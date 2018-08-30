#!/usr/bin/python3

import json
import os
import requests
import multiprocessing
import time
import copy
import sys

generate_list = False
if '--generate' in sys.argv:
    generate_list = True

test_mode = False

if generate_list:
	instances = {}
	page = requests.get('https://instances.social/instances.json')
	instances = json.loads(page.content.decode('utf-8'))

	l = []
	for i in instances:
		if "name" in i:
			beauty = i["name"].strip("/")
			beauty = beauty[beauty.rfind("@")+1:] if beauty.rfind("@") > -1 else beauty
			l.append(beauty)
	l = sorted(list(set(l)))
	json.dump(l, sys.stdout, indent=4, sort_keys=True)
	exit(0)

global_timeout = 30
if test_mode:
	global_timeout = 2

snapshot = {}
snapshot_file = "snapshot.json"
if os.path.isfile(snapshot_file):
		with open( snapshot_file ) as f:
			snapshot = json.load(f)

execcount = 0
if "execcount" in snapshot:
	execcount = snapshot["execcount"] + 1
snapshot["execcount"] = execcount

msg = "execcount: " + str(execcount)
if execcount % 2 == 0:
	http_prefix = "https://"
	msg += " using https"
else:
	http_prefix = "http://"
	msg += " using http"

if execcount % 4 < 2:
	proxies = {}
	msg += " using clearnet"
else:
	msg += " using darknet"
	proxies = {
		'http': 'socks5h://127.0.0.1:9050',
		'https': 'socks5h://127.0.0.1:9050'
	}
print(msg)

def exception_wrapper(procnum, name, return_dict):
	rv = {}
	rv['status_count'] = 0
	rv['user_count'] = 0
	rv['active'] = 0
	rv['uri'] = name
	try:
		page = requests.get(http_prefix + name + "/api/v1/instance", proxies=proxies, timeout=global_timeout)
		instance = json.loads(page.content.decode('utf-8'))
		toots = int(instance['stats']['status_count'])
		users = int(instance['stats']['user_count'])
		#print("%s %s: users: %s toots: %s"%(procnum, name, str(users), str(toots)))
		rv['status_count'] = toots
		rv['user_count'] = users
		rv['active'] = 1
		rv['uri'] = instance['uri']
	except:
		pass
	return_dict[procnum] = rv

def start_proc(jobs):
	print("starting processes: " + str(len(jobs)))
	for j in jobs:
		j.start()

def end_proc(jobs):
	if len(jobs) > 0:
		time.sleep(global_timeout + 1)
		print("ending processes: " + str(len(jobs)))
		for j in jobs:
			try:
				j.terminate()
				j.join()
			except Exception as e:
				print(e)

file_path = "list.json"
instances = {}
if os.path.isfile(file_path):
	with open( file_path ) as f:
		instances = json.load(f)

processes = []
manager = multiprocessing.Manager()
return_dict = manager.dict()
for i in range(len(instances)):
	name = instances[i]
	processes.append(multiprocessing.Process(target=exception_wrapper, args=(i, name, return_dict)))
	if (i+1) % 800 == 0:
		start_proc(processes)
		end_proc(processes)
		processes = []
		if test_mode:
			break

start_proc(processes)
end_proc(processes)

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
		name = instances[i]
		data[name] = {}
		data[name]['user_count'] = rv['user_count']
		data[name]['status_count'] = rv['status_count']
		data[name]['ts'] = current_ts

print("toots_count %s user_count %s instance_count %s"%(toots_count, user_count, instance_count))

# cleanup
#remove_list = []
#for d in data:
#	if int(data[d]["ts"]) == 0 and int(data[d]["status_count"]) == 0 and int(data[d]["user_count"]) == 0:
#		remove_list.append(d)
#for d in remove_list:
#	del data[d]

with open(snapshot_file, 'w') as outfile:
	json.dump(snapshot, outfile, indent=4, sort_keys=True)
	
print("crawler finished")
