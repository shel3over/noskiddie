#!/usr/bin/env python2
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
import stat
import re
import logging
import logging.config
import GeoIP


def actionManager():
    # i'm a thread i loop forever :)
    while True:
        ip, line = actionQueue.get()
        actionQueue.task_done()
        actionIptable(ip)
        # sending mail alert :)
        if config.get('smtp', 'enabled') != 'true':
            continue
        msg = MIMEText(line)
        msg['Subject'] = 'KIDS ALERT : %s %s ' % (geo.country_name_by_addr(ip), ip)
        msg['From'] = config.get('smtp', 'from')
        msg['To'] = config.get('smtp', 'to')
        server = smtplib.SMTP(
            config.get('smtp', 'server'),
            config.get('smtp', 'port'),
        )
        server.login(config.get('smtp', 'user'), config.get('smtp', 'pass'))
        server.sendmail(msg['From'], ['To'], msg.as_string())
        server.quit()


def logWatcher():
    # check the log file type/permition
    try:
        logStat = os.stat(config.get('global', 'logpath'))
    except OSError as err:
        log.fatal("%s: %s" % (err.strerror, err.filename))
        os._exit(1)

    if not logStat.st_mode & stat.S_IFREG:
        log.fatal("%s is not a regular file" % config.get('global', 'logpath'))
        os._exit(1)

    if logStat.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
        log.fatal("%s chmod should be 744 at least" %
                  config.get('global', 'logpath'))
        os._exit(1)

    # load the blaklist file
    blacklist = []
    for item in open('blacklist').readlines():
        blacklist.append(item.strip())

    f = subprocess.Popen(
        ['tail', '-F', config.get('global', 'logpath')],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    lastIp = ''
    # i'm a thread i loop forever :)
    while True:
        line = f.stdout.readline().lower()
        ip = line.split(' ')[0]
        if ip == lastIp:
            continue

        # we don't care if the ip is valid ,just a white list of chars
        if not re.match(r'^([0-9A-Fa-f\:\.])+$', ip):
            log.warn("ip : %s not valid" % ip)
            lastIp = ip
            continue
        for bad in blacklist:
            if bad in line:
                log.debug('bad word detected : %s in %s' % (bad, line))
                log.info('bad word detected : %s from %s' % (bad, ip))
                lastIp = ip
                actionQueue.put((ip, line))
                break


def actionCloudflare(ip):
    url = 'https://www.cloudflare.com/api.html?a=ban&key=%s&u=%s&tkn=%s' % (
        ip,
        config.get('cloudflare', 'user'),
        config.get('cloudflare', 'token'))
    urllib.open(url).read()


def actionIptable(ip):
    if os.getuid() != 0:
        log.warn("you don't have  permission to run iptables")
        return False
    if ':' in ip:
        iptables = 'ip6tables'
    else:
        iptables = 'iptables'
    os.popen('/usr/bin/env %s -A INPUT -s %s -j DROP' % (iptables, ip))
    return True

# load the config
config = ConfigParser.ConfigParser()
config.read('config.conf')

# logging
logging.config.dictConfig({
    'version': 1,
    'root': {
        'level': config.get('logging', 'level'),
        'handlers': ['console', 'file'],
    },
    'formatters': {
        'verbose': {
            'format':
            '%(levelname)s %(asctime)s %(module)s'
            '%(process)d %(thread)d %(message)s'
        },
        'normal': {
            'format': config.get('logging', 'format', True)
        },
    },
    'handlers': {
        'console': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose'
        },
        'file': {
            #'level': config.get('logging','level'),
            'class': 'logging.handlers.TimedRotatingFileHandler',
            'filename': config.get('logging', 'file'),
            'when': config.get('logging', 'when'),
            'interval': config.getint('logging', 'interval'),
            'backupCount': config.getint('logging', 'backupcount'),
            'formatter': 'normal',
        }
    },
})

log = logging.getLogger(__name__)

# load the GeoIP database
geo = GeoIP.new(GeoIP.GEOIP_MEMORY_CACHE)

actionQueue = Queue.Queue()
# start the threads
thread.start_new_thread(actionManager, ())
thread.start_new_thread(logWatcher, ())
# do not do anything :3
while True:
    sleep(1000)
