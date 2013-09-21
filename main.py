#!/usr/bin/env python
"""
auth @shel3over

""" 
import Queue
import thread
from time import sleep
from email.mime.text import MIMEText
import subprocess
import smtplib
import os
import urllib
import ConfigParser

config = ConfigParser.ConfigParser()
config.read('config.conf')


def actionManager():
	#i'm a thread i loop forever :)
	while True: 
		ip,line=actionQueue.get()
		actionQueue.task_done()
		actionIptable(ip)
		#sending mail alert :)
		msg=MIMEText(line)
		msg['Subject'] = 'KIDS ALERT : ', ip
		msg['From'] = config.get('smtp','from')
		msg['To'] = config.get('smtp','to')
		server =  smtplib.SMTP(config.get('smtp','server'),config.get('smtp','port'))
		server.login(config.get('smtp','user'),config.get('smtp','pass'))
		server.sendmail(fromaddr,toaddrs, msg.as_string())
		server.quit()

def logWatcher():
	#load the blaklist file 
	blacklist=[]
	for item in open('blacklist').readlines():
		blacklist.append(item.strip())

	f = subprocess.Popen(['tail','-F',config.get('global','logpath')],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	lastIp=''
	#i'm a thread i loop forever :)
	while True:
		line = f.stdout.readline().lower()
		ip = line.split(' ')[0]
		if ip == lastIp:
			continue
		for bad in blacklist:
			if bad in line:
				print 'baaaaaaaaaad',bad#just for debug
				print line
				lastIp=ip
				actionQueue.put((ip,line))
				break

def actionCloudflare(ip):
	urllib.open('https://www.cloudflare.com/api.html?a=ban&key=%s&u=%s&tkn=%s'%(ip,config.get('cloudflare','user'),config.get('cloudflare','token'))).read()

def actionIptable(ip):
	if ':' in ip:
		iptables='ip6tables'
	else:
		iptables='iptables'
		
	os.popen('/usr/bin/env %s -A INPUT -s %s -j DROP'%(iptables,ip))
	return True
  
actionQueue=Queue.Queue()

#start the threads
thread.start_new_thread(actionManager,())
thread.start_new_thread(logWatcher,())
#do not do anything :3 

while True:
	sleep(1000)
