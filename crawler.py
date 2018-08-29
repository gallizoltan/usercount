#!/usr/bin/python3

import json
import os
import requests
from multiprocessing import Process
import multiprocessing
import time
import copy

file_path = "instances.json"
instances = {}
if os.path.isfile(file_path):
	with open( file_path ) as f:
		instances = json.load(f)

global_timeout = 30

def exception_wrapper(procnum, name, return_dict):
	rv = {}
	rv['status_count'] = 0
	rv['user_count'] = 0
	rv['active'] = 0
	try:
		page = requests.get("https://" + name + "/api/v1/instance", timeout=global_timeout)
		instance = json.loads(page.content.decode('utf-8'))
		toots = int(instance['stats']['status_count'])
		users = int(instance['stats']['user_count'])
		#print("%s %s: users: %s toots: %s"%(procnum, name, str(users), str(toots)))
		rv['status_count'] = toots
		rv['user_count'] = users
		rv['active'] = 1
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

processes = []
manager = multiprocessing.Manager()
return_dict = manager.dict()
for j in range(len(instances)):
	i = instances[j]
	if "name" in i:
		processes.append(Process(target=exception_wrapper, args=(j, i["name"], return_dict)))
	if (j+1) % 800 == 0:
		start_proc(processes)
		end_proc(processes)
		processes = []

start_proc(processes)
end_proc(processes)

return_dict = copy.deepcopy(return_dict)

user_count = 0
toots_count = 0
instance_count = 0
for i in return_dict:
	rv = return_dict[i]
	user_count += rv['user_count']
	toots_count += rv['status_count']
	instance_count += rv['active']

stats = {}
stats_file = "stats.json"
if os.path.isfile(stats_file):
		with open( stats_file ) as f:
			stats = json.load(f)

current_ts = str(int(time.time()))
stats[current_ts] = {}
stats[current_ts]["toots_count"] = toots_count
stats[current_ts]["user_count"] = user_count
stats[current_ts]["instance_count"] = instance_count
print("toots_count %s user_count %s instance_count %s"%(toots_count, user_count, instance_count))
print(stats)

with open(stats_file, 'w') as outfile:
	json.dump(stats, outfile, indent=4, sort_keys=True)

