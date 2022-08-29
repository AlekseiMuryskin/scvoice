#!/usr/bin/env python

import sys, os
import configparser
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from time import sleep
import telebot


def NewOrOldEQ(EventID):
    ListID=[]
    with open('res.txt') as f:
        text=f.readlines()
    for i in text:
        s=i.split('\t')
        ListID.append(s[2])
    ListID=set(ListID)
    if EventID in ListID:
        return False
    else:
        return True

class MsgConfig():

    def __init__(self):
        self.minlat=0
        self.maxlat=0
        self.minlon=0
        self.maxlon=0
        self.email=''
        self.emaillst=[]

    def readcfg(self,fileini):
        config=configparser.ConfigParser()
        config.read(fileini)
        self.minlat=float(config.get('Main','MinLat'))
        self.maxlat=float(config.get('Main','MaxLat'))
        self.minlon=float(config.get('Main','MinLon'))
        self.maxlon=float(config.get('Main','MaxLon'))
        self.email=config.get('Main','Email')
        Email=self.email
        self.emaillst=Email.split(',')

    def IsOurArea(self,lat,lon):
        if (lat>=self.minlat) and (lat<=self.maxlat) and (lon>=self.minlon) and (lon<=self.maxlon):
            return True
        else:
            return False

    def otchet(self):
        print("=============Input parameters================")
        print("Min. latitude: %s" % self.minlat)
        print("Max. latitude: %s" % self.maxlat)
        print("Min. longitude: %s" % self.minlon)
        print("Max. longitude: %s" % self.maxlon)
        print("Number of email: %s" % len(self.emaillst))
        print("Email list: %s" % self.email)
        print("============================================")



# $1-InfoText $2-IsNewEQ $3-PublicID $4-DateTime $5-Lat $6-Lon $7-Depth $8-M

InfoText=sys.argv[1]
IsNewEQ=sys.argv[2]
EventID=sys.argv[3].replace('gfz','mi')
DataTime=sys.argv[4]
Lat=sys.argv[5]
Lon=sys.argv[6]
Depth=sys.argv[7]
M=sys.argv[8]

pth='config_bot.ini'
MyConfig=MsgConfig()
MyConfig.readcfg(pth)
MyConfig.otchet()

token='5676724609:AAHN6vxfLkIF87AsGgenvXzS0kgVZxkY3BI'
bot=telebot.TeleBot(token)
bot.config['api_key']=token
channel_id='-1001600125905'

if MyConfig.IsOurArea(float(Lat),float(Lon)):
    text = 'Subject: New Earthquake information (ID:'+EventID+')\r\n'
    text += '\r\n'+ InfoText + '\r\n'
    text += DataTime + '\t'+ Lat + '\t' + Lon + '\t' + Depth + '\t' + M + '\r\n'
    if NewOrOldEQ(EventID):
        #msg['Subject'] = 'Subject: New Earthquake information (ID:'+EventID+')\r\n'
        bot.send_message(CHANNEL_NAME,text)
    else:
        #msg['Subject'] ='Subject: Earthquake information update (ID:'+EventID+')\r\n'
        pass

    try:
        with open('res.txt','a') as f:
            f.write('{}\t{}\t{}\t{}\t{}\t{}\n'.format(DataTime,IsNewEQ,EventID,Lat,Lon,M))
    except:
        with open('res.txt','w') as f:
            f.write('{}\t{}\t{}\t{}\t{}\t{}\n'.format(DataTime,IsNewEQ,EventID,Lat,Lon,M))
    """
    msg['From'] = 'uralseis@gmail.com'
    msg['To'] = MyConfig.email

    for email in MyConfig.emaillst:
        mailserver = smtplib.SMTP('smtp.gmail.com',587)
        mailserver.ehlo()
        mailserver.starttls()
        mailserver.login('uralseis@gmail.com', 'labpts555')
        mailserver.sendmail(msg['From'],email,msg.as_string())
        mailserver.quit()
        print("Message sent for %s" % email)
        
    """
    
