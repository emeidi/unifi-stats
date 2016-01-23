#!/usr/bin/python
# -*- coding: utf-8 -*-

import sys
import os.path
import argparse
import yaml
import codecs
import paramiko
import json

# Configuration
verbose=False

configPath = './config.yaml'

debugPath="./debug.txt"
debugFile = codecs.open(debugPath,'w','utf-8')

def d(msg):
	debugFile.write(msg + "\n")
	
	if verbose == False:
		return
	
	print msg

def UniFiMcaDump(ip,username,password,usePubKeyAuth):
	try:
		ssh = paramiko.SSHClient()
		ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		
		if not usePubKeyAuth:
			d('Connecting to ' + ip + ' with username=' + username + ' and password=' + "*" * len(password))
			ssh.connect(ip, username=username, password=password)
		else:
			ssh.connect(ip)
		
		d("Connected to " + ip)
	#except paramiko.AuthenticationException:
	except:
		d("Authentication failed when connecting to " + ip)
		sys.exit(1)

	stdin, stdout, stderr = ssh.exec_command("mca-dump")
	
	json = stdout.read()

	d('Closing connection to ' + ip)
	ssh.close()

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
	
	return data

def printCacti(data):
	elements = []
	
	for (key, val) in data.items():
		string = str(key) + ':' + str(val)
		elements.append(string)
	
	print ' '.join(elements)

# Parse command line arguments
# ======================================================================
parser = argparse.ArgumentParser(description='Query UniFi access point(s) for usage statistics')

parser.add_argument('--ip', metavar='STRING', help='The IP address of a single access point to query. If none is submitted', required=False)
parser.add_argument('--interface', metavar='STRING', help='Which radio interface to select (e.g. ath4). If none is selected, data for all interfaces is returned.', required=False)
parser.add_argument('--output', metavar='[clients|throughput|errors|rssi]', choices=['clients','throughput','errors','rssi'], help='What specific data to output', required=True)
parser.add_argument('--output-format', metavar='[cacti]', choices=['cacti'], help='The output format for results. Currently only cacti is supported', required=False)
parser.add_argument('--verbose', help='Print debug information', action="store_true", required=False)

args = parser.parse_args()

# Logic to handle command line arguments
# ======================================================================
if args.verbose:
	d('Enabling command line verbosity as requested by command line')
	verbose = True

if args.ip:
	ipOnly = args.ip
	d('Enabling querying only the access point with IP ' + ipOnly)
else:
	ipOnly = ''

# Read Config
# ======================================================================
if not os.path.isfile(configPath):
	d('Config file "' + configPath + '" not found. Aborting.')
	sys.exit(1)

with open('config.yaml', 'r') as stream:
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

reqs = ['ip','usePubKeyAuth','username','password']
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
	usePubKeyAuth = ap['usePubKeyAuth']
	
	if len(ipOnly) > 0:
		d('Query single access point enabled by command line switch. Checking if this is the one.')
		
		if ipOnly != ip:
			d('This access point\'s IP "' + ip + '" doesn\'t match the requested access point\'s IP "' + ipOnly + '". Skipping.')
			continue
	
	d('Connecting to access point "' + apName + '" with IP "' + ip + '"')
	jsonRaw = UniFiMcaDump(ip,username,password,usePubKeyAuth)
	#print jsonRaw
	
	json = json.loads(jsonRaw)
	
	data = parseDump(json)
	#print data
	
	printCacti(data)
	
d('Preliminary end')
sys.exit(0)