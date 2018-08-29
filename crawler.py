#!/usr/bin/python3

import json
import os
import requests

file_path = "instances.json"
instances = {}
if os.path.isfile(file_path):
	with open( file_path ) as f:
		instances = json.load(f)

toots_count = 0
user_count = 0
instance_count = 0
for j in range(len(instances)):
	i = instances[j]
	try:
		page = requests.get("https://" + i["name"] + "/api/v1/instance", timeout=1)
		instance = json.loads(page.content.decode('utf-8'))
		#print(instance)
		toots = int(instance['stats']['status_count'])
		users = int(instance['stats']['user_count'])
		print("%s of %s %s: users: %s toots: %s"%(str(j), str(len(instances)), i["name"], str(users), str(toots)))
		toots_count += toots
		user_count += users
		instance_count += 1
	except Exception as e:
		print("%s of %s"%(str(j), str(len(instances))))
		#print(e)
		pass

stats = {}
stats["toots_count"] = toots_count
stats["user_count"] = user_count
stats["instance_count"] = instance_count
print("toots_count %s user_count %s instance_count %s"%(toots_count, user_count, instance_count))
print(stats)

stats_file = "stats2.json"
with open(stats_file, 'w') as outfile:
	json.dump(stats, outfile, indent=4, sort_keys=True)



