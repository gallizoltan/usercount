#!/usr/bin/python3

import json
import os
import requests
import multiprocessing
import time
import copy
import sys


instances = {}
file_path = "instances.json"
if os.path.isfile(file_path):
	with open( file_path ) as f:
		instances = json.load(f)

file_path = "list.json"
names = {}
if os.path.isfile(file_path):
	with open( file_path ) as f:
		names = json.load(f)

def get_value(d, n):
    if n not in d: return 0
    if d[n] == None: return 0
    return int(d[n])

snap = {}
for name in names:
	for i in instances:
		beauty = i["name"].strip("/")
		beauty = beauty[beauty.rfind("@")+1:] if beauty.rfind("@") > -1 else beauty
		if beauty == name:
			if beauty not in snap:
				snap[beauty] = {}
			user_count = get_value(i, "users")
			if "user_count" in snap[beauty]:
				if snap[beauty]["user_count"] > user_count:
					user_count = snap[beauty]["user_count"]
			snap[beauty]["user_count"] = user_count
			status_count = get_value(i, "statuses")
			if "status_count" in snap[beauty]:
				if snap[beauty]["status_count"] > status_count:
					status_count = snap[beauty]["status_count"]
			snap[beauty]["status_count"] = status_count
			
json.dump(snap, sys.stdout, indent=4, sort_keys=True)

