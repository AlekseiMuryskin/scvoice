#!/usr/bin/env python

############################################################################
#    Copyright (C) by GFZ Potsdam                                          #
#                                                                          #
#    You can redistribute and/or modify this program under the             #
#    terms of the SeisComP Public License.                                 #
#                                                                          #
#    This program is distributed in the hope that it will be useful,       #
#    but WITHOUT ANY WARRANTY; without even the implied warranty of        #
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         #
#    SeisComP Public License for more details.                             #
############################################################################

import os
import sys
import subprocess
import traceback
import seiscomp.client
import seiscomp.seismology
import seiscomp.system


class VoiceAlert(seiscomp.client.Application):

    def __init__(self, argc, argv):
        seiscomp.client.Application.__init__(self, argc, argv)

        self.setMessagingEnabled(True)
        self.setDatabaseEnabled(True, True)
        self.setLoadRegionsEnabled(True)
        self.setMessagingUsername("")
        #self.setPrimaryMessagingGroup(
        #    seiscomp.communication.Protocol.LISTENER_GROUP)
        self.addMessagingSubscription("EVENT")
        self.addMessagingSubscription("LOCATION")
        self.addMessagingSubscription("MAGNITUDE")

        self.setAutoApplyNotifierEnabled(True)
        self.setInterpretNotifierEnabled(True)

        self.setLoadCitiesEnabled(True)
        self.setLoadRegionsEnabled(True)

        self._ampType = "snr"
        self._citiesMaxDist = 20
        self._citiesMinPopulation = 50000

        self._eventDescriptionPattern = None
        self._ampScript = None
        self._alertScript = None
        self._eventScript = None

        self._ampProc = None
        self._alertProc = None
        self._eventProc = None

        self._newWhenFirstSeen = False
        self._prevMessage = {}
        self._agencyIDs = []

    def createCommandLineDescription(self):
        self.commandline().addOption("Generic", "first-new",
                                     "calls an event a new event when it is seen the first time")
        self.commandline().addGroup("Alert")
        self.commandline().addStringOption("Alert", "amp-type",
                                           "specify the amplitude type to listen to", self._ampType)
        self.commandline().addStringOption("Alert", "amp-script",
                                           "specify the script to be called when a stationamplitude arrived, network-, stationcode and amplitude are passed as parameters $1, $2 and $3")
        self.commandline().addStringOption("Alert", "alert-script",
                                           "specify the script to be called when a preliminary origin arrived, latitude and longitude are passed as parameters $1 and $2")
        self.commandline().addStringOption("Alert", "event-script",
                                           "specify the script to be called when an event has been declared; the message string, a flag (1=new event, 0=update event), the EventID, the arrival count and the magnitude (optional when set) are passed as parameter $1, $2, $3, $4 and $5")
        self.commandline().addGroup("Cities")
        self.commandline().addStringOption("Cities", "max-dist",
                                           "maximum distance for using the distance from a city to the earthquake")
        self.commandline().addStringOption("Cities", "min-population",
                                           "minimum population for a city to become a point of interest")
        self.commandline().addGroup("Debug")
        self.commandline().addStringOption("Debug", "eventid,E", "specify Event ID")
        return True

    def init(self):
        if not seiscomp.client.Application.init(self):
            return False

        try:
            self._newWhenFirstSeen = self.configGetBool("firstNew")
        except:
            pass

        try:
            agencyIDs = self.configGetStrings("agencyIDs")
            for item in agencyIDs:
                item = item.strip()
                if item not in self._agencyIDs:
                    self._agencyIDs.append(item)
        except:
            pass

        try:
            if self.commandline().hasOption("first-new"):
                self._newWhenFirstSeen = True
        except:
            pass

        try:
            self._eventDescriptionPattern = self.configGetString("poi.message")
        except:
            pass

        try:
            self._citiesMaxDist = self.configGetDouble("poi.maxDist")
        except:
            pass

        try:
            self._citiesMaxDist = self.commandline().optionDouble("max-dist")
        except:
            pass

        try:
            self._citiesMinPopulation = self.configGetInt("poi.minPopulation")
        except:
            pass

        try:
            self._citiesMinPopulation = self.commandline().optionInt("min-population")
        except:
            pass

        try:
            self._ampType = self.commandline().optionString("amp-type")
        except:
            pass

        try:
            self._ampScript = self.commandline().optionString("amp-script")
        except:
            try:
                self._ampScript = self.configGetString("scripts.amplitude")
            except:
                seiscomp.logging.warning("No amplitude script defined")

        if self._ampScript:
            self._ampScript = seiscomp.system.Environment.Instance().absolutePath(self._ampScript)

        try:
            self._alertScript = self.commandline().optionString("alert-script")
        except:
            try:
                self._alertScript = self.configGetString("scripts.alert")
            except:
                seiscomp.logging.warning("No alert script defined")

        if self._alertScript:
            self._alertScript = seiscomp.system.Environment.Instance(
            ).absolutePath(self._alertScript)

        try:
            self._eventScript = self.commandline().optionString("event-script")
        except:
            try:
                self._eventScript = self.configGetString("scripts.event")
                seiscomp.logging.info(
                    "Using event script: %s" % self._eventScript)
            except:
                seiscomp.logging.warning("No event script defined")

        if self._eventScript:
            self._eventScript = seiscomp.system.Environment.Instance(
            ).absolutePath(self._eventScript)

        seiscomp.logging.info("Creating ringbuffer for 100 objects")
        if not self.query():
            seiscomp.logging.warning(
                "No valid database interface to read from")
        self._cache = seiscomp.datamodel.PublicObjectRingBuffer(
            self.query(), 100)

        if self._ampScript and self.connection():
            self.connection().subscribe("AMPLITUDE")

        if self._newWhenFirstSeen:
            seiscomp.logging.info(
                "A new event is declared when I see it the first time")

        if not self._agencyIDs:
            seiscomp.logging.info("agencyIDs: []")
        else:
            seiscomp.logging.info("agencyIDs: %s" %
                                   (" ".join(self._agencyIDs)))

        return True

    def run(self):
        try:
            try:
                eventID = self.commandline().optionString("eventid")
                event = self._cache.get(seiscomp.datamodel.Event, eventID)
                if event:
                    self.notifyEvent(event)
            except:
                pass

            return seiscomp.client.Application.run(self)
        except:
            info = traceback.format_exception(*sys.exc_info())
            for i in info:
                sys.stderr.write(i)
            return False

    def QuotedStr(s):
		return '"'+s+'"'
    
    def runAmpScript(self, net, sta, amp):
        if not self._ampScript:
            return

        if self._ampProc is not None:
            if self._ampProc.poll() is None:
                seiscomp.logging.warning(
                    "AmplitudeScript still in progress -> skipping message")
                return
        try:
            self._ampProc = subprocess.Popen(
                [self._ampScript, net, sta, "%.2f" % amp])
            seiscomp.logging.info(
                "Started amplitude script with pid %d" % self._ampProc.pid)
        except:
            seiscomp.logging.error(
                "Failed to start amplitude script '%s'" % self._ampScript)

    def runAlert(self, lat, lon):
        if not self._alertScript:
            return

        if self._alertProc is not None:
            if self._alertProc.poll() is None:
                seiscomp.logging.warning(
                    "AlertScript still in progress -> skipping message")
                return
        try:
            self._alertProc = subprocess.Popen(
                [self._alertScript, "%.1f" % lat, "%.1f" % lon])
            seiscomp.logging.info(
                "Started alert script with pid %d" % self._alertProc.pid)
        except:
            seiscomp.logging.error(
                "Failed to start alert script '%s'" % self._alertScript)

    def handleMessage(self, msg):
        try:
            dm = seiscomp.core.DataMessage.Cast(msg)
            if dm:
                for att in dm:
                    org = seiscomp.datamodel.Origin.Cast(att)
                    if org:
                        try:
                            if org.evaluationStatus() == seiscomp.datamodel.PRELIMINARY:
                                self.runAlert(org.latitude().value(),
                                              org.longitude().value())
                        except:
                            pass

            #ao = seiscomp3.DataModel.ArtificialOriginMessage.Cast(msg)
            # if ao:
            #  org = ao.origin()
            #  if org:
            #    self.runAlert(org.latitude().value(), org.longitude().value())
            #  return

            seiscomp.client.Application.handleMessage(self, msg)
        except:
            info = traceback.format_exception(*sys.exc_info())
            for i in info:
                sys.stderr.write(i)

    def addObject(self, parentID, object):
        try:
            obj = seiscomp.datamodel.Amplitude.Cast(object)
            if obj:
                if obj.type() == self._ampType:
                    seiscomp.logging.debug("got new %s amplitude '%s'" % (
                        self._ampType, obj.publicID()))
                    self.notifyAmplitude(obj)

            obj = seiscomp.datamodel.Origin.Cast(object)
            if obj:
                self._cache.feed(obj)
                seiscomp.logging.debug("got new origin '%s'" % obj.publicID())

                try:
                    if obj.evaluationStatus() == seiscomp.datamodel.PRELIMINARY:
                        self.runAlert(obj.latitude().value(),
                                      obj.longitude().value())
                except:
                    pass

                return

            obj = seiscomp.datamodel.Magnitude.Cast(object)
            if obj:
                self._cache.feed(obj)
                seiscomp.logging.debug(
                    "got new magnitude '%s'" % obj.publicID())
                return

            obj = seiscomp.datamodel.Event.Cast(object)
            if obj:
                org = self._cache.get(
                    seiscomp.datamodel.Origin, obj.preferredOriginID())
                agencyID = org.creationInfo().agencyID()
                seiscomp.logging.debug("got new event '%s'" % obj.publicID())
                if not self._agencyIDs or agencyID in self._agencyIDs:
                    self.notifyEvent(obj, True)
        except:
            info = traceback.format_exception(*sys.exc_info())
            for i in info:
                sys.stderr.write(i)

    def updateObject(self, parentID, object):
        try:
            obj = seiscomp.datamodel.Event.Cast(object)
            if obj:
                org = self._cache.get(
                    seiscomp.datamodel.Origin, obj.preferredOriginID())
                agencyID = org.creationInfo().agencyID()
                seiscomp.logging.debug("update event '%s'" % obj.publicID())
                if not self._agencyIDs or agencyID in self._agencyIDs:
                    self.notifyEvent(obj, False)
        except:
            info = traceback.format_exception(*sys.exc_info())
            for i in info:
                sys.stderr.write(i)

    def notifyAmplitude(self, amp):
        self.runAmpScript(amp.waveformID().networkCode(
        ), amp.waveformID().stationCode(), amp.amplitude().value())

    def notifyEvent(self, evt, newEvent=True, dtmax=360000):
        try:
            org = self._cache.get(
                seiscomp.datamodel.Origin, evt.preferredOriginID())
            if not org:
                seiscomp.logging.warning(
                    "unable to get origin %s, ignoring event message" % evt.preferredOriginID())
                return

            preliminary = False
            try:
                if org.evaluationStatus() == seiscomp.datamodel.PRELIMINARY:
                    preliminary = True
            except:
                pass

            if preliminary == False:
                nmag = self._cache.get(
                    seiscomp.datamodel.Magnitude, evt.preferredMagnitudeID())
                if nmag:
                    mag = nmag.magnitude().value()
                    mag = "magnitude %.1f" % mag
                else:
                    if len(evt.preferredMagnitudeID()) > 0:
                        seiscomp.logging.warning(
                            "unable to get magnitude %s, ignoring event message" % evt.preferredMagnitudeID())
                    else:
                        seiscomp.logging.warning(
                            "no preferred magnitude yet, ignoring event message")
                    return

            # keep track of old events
            if self._newWhenFirstSeen:
                if evt.publicID() in self._prevMessage:
                    newEvent = False
                else:
                    newEvent = True

            dsc = seiscomp.seismology.Regions.getRegionName(
                org.latitude().value(), org.longitude().value())
            
            #new code
            city, dist, azi = self.nearestCity(org.latitude().value(), org.longitude(
                    ).value(), self._citiesMaxDist, self._citiesMinPopulation)
            dsc = self._eventDescriptionPattern
            region = seiscomp.seismology.Regions.getRegionName(
                            org.latitude().value(), org.longitude().value())
            distStr = str(int(seiscomp.math.deg2km(dist)))
            dsc = dsc.replace("@region@", region).replace(
                            "@dist@", distStr).replace("@poi@", city.name())
            ####
            if self._eventDescriptionPattern:
                try:
                    city, dist, azi = self.nearestCity(org.latitude().value(), org.longitude(
                    ).value(), self._citiesMaxDist, self._citiesMinPopulation)
                    if city:
                        dsc = self._eventDescriptionPattern
                        region = seiscomp.seismology.Regions.getRegionName(
                            org.latitude().value(), org.longitude().value())
                        distStr = str(int(seiscomp.math.deg2km(dist)))
                        dsc = dsc.replace("@region@", region).replace(
                            "@dist@", distStr).replace("@poi@", city.name())
                except:
                    pass

            seiscomp.logging.debug("desc: %s" % dsc)

            dep = org.depth().value()
            now = seiscomp.core.Time.GMT()
            otm = org.time().value()

            dt = (now - otm).seconds()

    #   if dt > dtmax:
    #       return

            if dt > 3600:
                dt = "%d hours %d minutes ago" % (dt/3600, (dt % 3600)/60)
            elif dt > 120:
                dt = "%d minutes ago" % (dt/60)
            else:
                dt = "%d seconds ago" % dt

            if preliminary == True:
                message = "earthquake, preliminary, %%s, %s" % dsc
            else:
                message = "earthquake, %%s, %s, %s, depth %d kilometers" % (dsc, mag, int(dep+0.5))
            # at this point the message lacks the "ago" part
            
            message = message % dt
            
            print message
            
            
            try:
                isNew = 0
                nPh = 0
                M = "-"
                if newEvent:
                    isNew = 1

                #print '1'
                org = self._cache.get(
                    seiscomp.datamodel.Origin, evt.preferredOriginID())
                if org:
                    try:
                        nPh = org.quality().associatedPhaseCount()
                    except:
                        pass

                #print '2'
                nmag = self._cache.get(
                    seiscomp.datamodel.Magnitude, evt.preferredMagnitudeID())
                if nmag:
                    M = "%.1f" % nmag.magnitude().value()

                #print '3'
                T0 = '"'+str(org.time().value())+'"'
                #print '4'
                lat = "%.4f" % org.latitude().value()
                lon = "%.4f" % org.longitude().value()
                depth = "%.1f" % org.depth().value()
                pID = str(evt.publicID())
                s_out = pID+'\t'+T0+'\t'+lat+'\t'+lon+'\t'+depth+'\t'+M
                #print s_out+'\n'
                fevents.write(s_out+"\n")
                fevents.flush()
                
                s_out = '"'+message+'" '+str(isNew)+' '+s_out.replace('\t', ' ')
                print 'Starting INFO script with parameters: '+s_out
                os.system('python ~/processing/EvtMsg.py '+s_out)
                os.system('python ~/processing/EvtMsgTelegram.py '+s_out)
                #self._eventProc = subprocess.Popen(
                #    [self._eventScript, message, "%d" % param2, evt.publicID(), "%d" % param3, param4])
                #self._eventProc = subprocess.Popen([self._eventScript, s_out])
                #seiscomp3.Logging.info(
                    #"Started event script with pid %d" % self._eventProc.pid)
                
            except:
                seiscomp.logging.error("Failed to start event script")
        except:
            info = traceback.format_exception(*sys.exc_info())
            for i in info:
                sys.stderr.write(i)


app = VoiceAlert(len(sys.argv), sys.argv)
print 'Script started!'
seiscomp.logging.error("scvoice2 script started")
#print 'Alert script = '+str(self._eventScript)
fname = './events_scvoice.txt'
if os.path.exists(fname):
	fevents = open(fname, 'a')
else:
	fevents = open(fname, 'w')

fevents.write("scvoice2 script started\n")
fevents.flush()

sys.exit(app())
