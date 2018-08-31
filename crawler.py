#!/usr/bin/python3

import json
import os
import requests
import multiprocessing
import time
import copy
import sys
import datetime

if '--generate' in sys.argv:
	instances = {}
	page = requests.get('https://instances.social/instances.json')
	instances = json.loads(page.content.decode('utf-8'))
	names = []
	for i in instances:
		if "name" in i:
			beauty = i["name"].strip("/")
			beauty = beauty[beauty.rfind("@")+1:] if beauty.rfind("@") > -1 else beauty
			names.append(beauty)
	names = sorted(list(set(names)))
	json.dump(names, sys.stdout, indent=4, sort_keys=True)
	exit(0)

start_ts = int(time.time())

global_timeout = 30

snapshot = {}
snapshot_file = "snapshot.json"
if os.path.isfile(snapshot_file):
		with open( snapshot_file ) as f:
			snapshot = json.load(f)

execcount = 0
if "execcount" in snapshot:
	execcount = snapshot["execcount"] + 1
snapshot["execcount"] = execcount

msg = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " execution count: " + str(execcount)
if execcount % 2 == 0:
	http_prefix = "https://"
	msg += ", using https"
else:
	http_prefix = "http://"
	msg += ", using http"

if execcount % 4 < 2:
	proxies = {}
	msg += " + clearnet"
else:
	msg += " + darknet"
	proxies = {
		'http': 'socks5h://127.0.0.1:9050',
		'https': 'socks5h://127.0.0.1:9050'
	}
print(msg)
print('Working', end='')

def mp_worker(procnum, name, return_dict):
	try:
		page = requests.get(http_prefix + name + "/api/v1/instance", proxies=proxies, timeout=global_timeout)
		instance = json.loads(page.content.decode('utf-8'))
		toots = int(instance['stats']['status_count'])
		users = int(instance['stats']['user_count'])
		#print("%s %s: users: %s toots: %s"%(procnum, name, str(users), str(toots)))
		rv = {}
		rv['status_count'] = toots
		rv['user_count'] = users
		rv['active'] = 1
		rv['uri'] = instance['uri']
		return_dict[procnum] = rv
	except:
		pass
	if procnum % 500 == 0:
		print('.', end='', flush=True)

file_path = "list.json"
names = {}
if os.path.isfile(file_path):
	with open( file_path ) as f:
		names = json.load(f)

args = []
manager = multiprocessing.Manager()
return_dict = manager.dict()
for i in range(len(names)):
	args.append((i, names[i], return_dict))

p = multiprocessing.Pool(500)
p.starmap(mp_worker, args)

print()

return_dict = copy.deepcopy(return_dict)

current_ts = int(time.time())
snapshot["ts"] = current_ts
if "data" not in snapshot:
	snapshot["data"] = {}

user_count = 0
toots_count = 0
instance_count = 0
data = snapshot["data"]
for i in return_dict:
	rv = return_dict[i]
	user_count += rv['user_count']
	toots_count += rv['status_count']
	if rv["active"] > 0:
		instance_count += 1
		name = names[i]
		data[name] = {}
		data[name]['user_count'] = rv['user_count']
		data[name]['status_count'] = rv['status_count']
		data[name]['ts'] = current_ts

print("Toots: %s, users: %s, instances: %s"%(toots_count, user_count, instance_count))

# cleanup
#remove_list = []
#for d in data:
#	if int(data[d]["ts"]) == 0 and int(data[d]["status_count"]) == 0 and int(data[d]["user_count"]) == 0:
#		remove_list.append(d)
#for d in remove_list:
#	del data[d]

with open(snapshot_file, 'w') as outfile:
	json.dump(snapshot, outfile, indent=4, sort_keys=True)

timediff = int(time.time()) - start_ts
s = timediff % 60
timediff = timediff / 60
m = timediff % 60
h = timediff / 60
msg = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " crawler finished in "
msg += "%02d:%02d"%(m, s)
print(msg)
