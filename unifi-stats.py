#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os.path
import time
import argparse
import yaml
import codecs
import paramiko
import json
import random

# Configuration
verbose = False
maxCacheAgeInSeconds = 70
cacheUsed = False

scriptPath = os.path.dirname(os.path.abspath(__file__))

configPath = scriptPath + '/config.yaml'

debugPath = scriptPath + '/debug.txt'
debugFile = codecs.open(debugPath,'w','utf-8')

sshDefaultLogFilePath = '/tmp/unifi-stats.ssh.log'

def d(msg):
    debugFile.write(msg + "\n")

    if verbose == False:
        return

    print msg

def UniFiMcaDump(ip,username,password,privateKeyPath = ''):
    global cacheUsed

    cacheFile = '/tmp/unifi_' + ip + '.json'

    if os.path.isfile(cacheFile):
        d('Cache file ' + cacheFile + ' found.')

        then = int(os.path.getmtime(cacheFile))
        now = int(time.time())
        diff = now - then

        if diff < maxCacheAgeInSeconds:
            d('Cache file ' + cacheFile + ' is younger than ' + str(maxCacheAgeInSeconds) + ' seconds (' + str(diff) + ' seconds). Using cached data instead of querying access point.')
            cacheUsed = True

            json = open(cacheFile).read()
            return json
        else:
            d('Cache file ' + cacheFile + ' is older than ' + str(maxCacheAgeInSeconds) + ' seconds (' + str(diff) + ' seconds). Performing SSH connection.')

    try:
        ssh = paramiko.SSHClient()
        paramiko.util.log_to_file(sshLogFilePath)
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        if len(privateKeyPath) > 0:
            privateKeyPathOrig = privateKeyPath
            privateKeyPath = os.path.abspath(scriptPath + '/' + privateKeyPath)

            d('Using private key at "' + privateKeyPath + '" (non-absolutized path: "' + privateKeyPathOrig + '")')
            pkey = paramiko.RSAKey.from_private_key_file(privateKeyPath)
            ssh.connect(ip, username=username, pkey=pkey)
        else:
            d('Connecting to ' + ip + ' with username=' + username + ' and password=' + "*" * len(password))
            ssh.connect(ip, username=username, password=password)

        d("Connected to " + ip)
    #except paramiko.AuthenticationException:
    except:
        d("Authentication failed when connecting to " + ip)
        sys.exit(1)

    stdin, stdout, stderr = ssh.exec_command("mca-dump")

    json = stdout.read()

    d('Closing connection to ' + ip)
    ssh.close()

    f = open(cacheFile, 'w')
    f.write(json)
    f.close()

    return json

def parseDump(json):
    function = args.output
    function = 'parseDump' + function.title()

    d('Accessing function "' + function + '"')

    data = globals()[function](json)

    return data

def parseDumpClients(json):
    data = {}

    vaps = json['vap_table']
    for vap in vaps:
        interface = vap['name']
        d('Looking at radio interface "' + interface + '"')

        if args.interface:
            d('Only a specific radio interface is selected, checking')
            if args.interface != interface:
                continue

        if not vap['num_sta']:
            d('vap[num_sta] not set for interface ' + interface + '. Skipping.')
            continue

        data[interface] = vap['num_sta']

    data['all'] = sum(data.values())

    return data

def parseDumpBytes(json):
    data = {}

    vaps = json['vap_table']
    for vap in vaps:
        interface = vap['name']
        d('Looking at radio interface "' + interface + '"')

        if args.interface:
            d('Only a specific radio interface is selected, checking')
            if args.interface != interface:
                continue

        if not vap['rx_bytes']:
            d('vap[rx_bytes] not set for interface ' + interface + '. Skipping.')
            continue

        data[interface] = vap['rx_bytes']


    data['all'] = sum(data.values())

    return data

def parseDumpPackets(json):
    data = {}

    vaps = json['vap_table']
    for vap in vaps:
        interface = vap['name']
        d('Looking at radio interface "' + interface + '"')

        if args.interface:
            d('Only a specific radio interface is selected, checking')
            if args.interface != interface:
                continue

        if not vap['rx_packets']:
            d('vap[rx_bytes] not set for interface ' + interface + '. Skipping.')
            continue

        data[interface] = vap['rx_packets']

    data['all'] = sum(data.values())

    return data

def parseDumpErrors(json):
    data = {}

    vaps = json['vap_table']
    for vap in vaps:
        interface = vap['name']
        d('Looking at radio interface "' + interface + '"')

        if args.interface:
            d('Only a specific radio interface is selected, checking')
            if args.interface != interface:
                continue

        if not vap['rx_errors']:
            d('vap[rx_errors] not set for interface ' + interface + '. Skipping.')
            continue

        data[interface] = vap['rx_errors']

    data['all'] = sum(data.values())

    return data

def parseDumpRssi_Low(json):
    data = {}

    default = 9999

    vaps = json['vap_table']
    for vap in vaps:
        interface = vap['name']
        d('Looking at radio interface "' + interface + '"')

        if args.interface:
            d('Only a specific radio interface is selected, checking')
            if args.interface != interface:
                continue

        low = default
        clients = vap['sta_table']
        for client in clients:
            MAC = client['mac']
            d('Looking at client with MAC "' + MAC + '"')

            if not client['rssi']:
                d('client[rssi] not set for interface ' + interface + '. Skipping.')
                continue

            rssi = client['rssi']
            if rssi < low:
                d('RSSI ' + str(rssi) + ' is worse than ' + str(low) + '. Selecting this client as new low.')
                low = rssi
            else:
                d('RSSI ' + str(rssi) + ' is better than ' + str(low) + '. Skipping this client.')

        if low == default:
            low = 0

        data[interface] = low

    low = default
    for val in data.values():
        if val < 1:
            continue

        if val < low:
            low = val

    if low == default:
        low = 0

    data['all'] = low

    return data

def parseDumpRssi_High(json):
    data = {}

    default = 0

    vaps = json['vap_table']
    for vap in vaps:
        interface = vap['name']
        d('Looking at radio interface "' + interface + '"')

        if args.interface:
            d('Only a specific radio interface is selected, checking')
            if args.interface != interface:
                continue

        high = default
        clients = vap['sta_table']
        for client in clients:
            MAC = client['mac']
            d('Looking at client with MAC "' + MAC + '"')

            if not client['rssi']:
                d('client[rssi] not set for interface ' + interface + '. Skipping.')
                continue

            rssi = client['rssi']
            if rssi > high:
                d('RSSI ' + str(rssi) + ' is better than ' + str(high) + '. Selecting this client as new high.')
                high = rssi
            else:
                d('RSSI ' + str(rssi) + ' is worse than ' + str(high) + '. Skipping this client.')

        if high == default:
            high = 0

        data[interface] = high

    high = default
    for val in data.values():
        if val < 1:
            continue

        if val > high:
            high = val

    if high == default:
        high = 0

    data['all'] = high

    return data

def printCacti(data):
    elements = []

    for (key, val) in data.items():
        string = str(key) + ':' + str(val)
        elements.append(string)

    if cacheUsed:
        cacheUsedInt = 1
    else:
        cacheUsedInt = 0

    elements.append('CACHE:' + str(cacheUsedInt))

    out = ' '.join(elements)

    d('Output: ' + out)
    print out

# Parse command line arguments
# ======================================================================
parser = argparse.ArgumentParser(description='Query UniFi access point(s) for usage statistics')

parser.add_argument('--ip', metavar='STRING', help='The IP address of a single access point to query. If none is submitted', required=False)
parser.add_argument('--interface', metavar='STRING', help='Which radio interface to select (e.g. ath4). If none is selected, data for all interfaces is returned.', required=False)
parser.add_argument('--enablewait', help='Enable a randomly chosen wait period to prevent race conditions when using JSON cache', action="store_true", required=False)
parser.add_argument('--output', metavar='[clients|bytes|packets|errors|rssi_low|rssi_high]', choices=['clients','bytes','packets','errors','rssi_low','rssi_high'], help='What specific data to output', required=True)
parser.add_argument('--output-format', metavar='[cacti]', choices=['cacti'], help='The output format for results. Currently only cacti is supported', required=False)
parser.add_argument('--verbose', help='Print debug information', action="store_true", required=False)
parser.add_argument('--sshlog', metavar='STRING', help='Where to log Paramikos SSH module info to. If not provided defaults to "' + sshDefaultLogFilePath + '"', required=False)

args = parser.parse_args()

# Logic to handle command line arguments
# ======================================================================
if args.verbose:
    d('Enabling command line verbosity as requested by command line')
    verbose = True

if args.enablewait:
    d('Enabling random wait as requested by command line')
    enableWait = True
else:
    enableWait = False

if args.ip:
    ipOnly = args.ip
    d('Enabling querying only the access point with IP ' + ipOnly)
else:
    ipOnly = ''

if args.sshlog:
    sshLogFilePath = args.sshlog
else:
    sshLogFilePath = sshDefaultLogFilePath

# Read Config
# ======================================================================
if not os.path.isfile(configPath):
    d('Config file "' + configPath + '" not found. Aborting.')
    sys.exit(1)

with open(configPath, 'r') as stream:
    config = yaml.load(stream)

# General Config
# ======================================================================
if not config['General']:
    d('Config key "General" not set in "' + configPath + '". Aborting.')
    sys.exit(1)

if not config['AccessPoints']:
    d('Config key "AccessPoints" not set in "' + configPath + '". Aborting.')
    sys.exit(1)

# Iterate over access points
# ======================================================================
aps = config['AccessPoints']
#print(aps)
#sys.exit(1)

reqs = ['ip','username','password','privatekeypath']
for (apName, ap) in aps.items():
    skipAp = False
    #apName = str(apName)

    for req in reqs:
        d('Checking for "' + req + '" in "' + apName + '"')

        if not req in ap:
            d('ap[' + req + '] not set for access point "' + apName + '". Skipping.')
            skipAp = True
        else:
            d(req + ' is present in "' + apName + '"')

    if skipAp:
        d('Skipping this access point because of a missing configuration item.')
        continue

    ip = ap['ip']
    username = ap['username']
    password = ap['password']
    privatekeypath = ap['privatekeypath']

    if len(ipOnly) > 0:
        d('Query single access point enabled by command line switch. Checking if this is the one.')

        if ipOnly != ip:
            d('This access point\'s IP "' + ip + '" doesn\'t match the requested access point\'s IP "' + ipOnly + '". Skipping.')
            continue

    if enableWait:
        seconds = random.randint(1,15)
        d('Chose to sleep ' + str(seconds) + ' random seconds in hope of being able to reuse by then populated JSON cache')
        time.sleep(seconds)

    d('Connecting to access point "' + apName + '" with IP "' + ip + '"')
    jsonRaw = UniFiMcaDump(ip,username,password,privatekeypath)
    #print jsonRaw

    json = json.loads(jsonRaw)

    data = parseDump(json)
    #print data

    printCacti(data)

d('Script finished executing at ')
sys.exit(0)
