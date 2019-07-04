#!/usr/bin/python3

import os, sys
sys.dont_write_bytecode = True
import json, csv
import requests
import multiprocessing
import time
import fcntl
from datetime import datetime
import atexit
try:
	import psutil
except:
	print("Run: \'pip install psutil\' to see memory consumption")
import common

class timeout_iterator:
	def __init__(self, pool_it, total_timeout):
		self.pool_it = pool_it
		self.total_timeout = total_timeout
		self.start_ts = int(time.time())
	def __iter__(self):
		return self
	def __next__(self):
		remaining_time = self.total_timeout + self.start_ts - int(time.time())
		return self.pool_it.next(remaining_time)

def setup_environment():
	os.chdir(os.path.dirname(os.path.abspath(__file__)))

	pid = os.getppid()
	filename, file_extension = os.path.splitext(os.path.basename(__file__))
	pid_file = filename + '.pid'

	global fp
	fp = open(pid_file, 'w')
	try:
		fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
	except IOError:
		print("Another instance is running, exiting.", file=sys.stderr)
		sys.exit(1)
	atexit.register(os.remove, pid_file)

def extend_list(names):
	instances = {}
	new_names = []
	try:
		page = requests.get('https://instances.social/instances.json')
		instances = json.loads(page.content.decode('utf-8'))
		for i in instances:
			if "name" in i:
				beauty = i["name"].strip("/")
				beauty = beauty[beauty.rfind("@")+1:] if beauty.rfind("@") > -1 else beauty
				if beauty.endswith('.'):
					beauty = beauty[:-1]
				beauty = beauty.encode("idna").decode('utf-8')
				forbidden = beauty + "--"
				if any(s == forbidden for s in names):
					continue
				new_names.append(beauty)
	except:
		pass
	new_names = sorted(list(set(new_names).union(set(names))))
	return(new_names)

def print_ts(msg):
	print(datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " " + msg)

def setup_request_params(execcount):
	msg = "+ Crawler execution count: " + str(execcount)
	global http_prefix
	if execcount % 2 == 0:
		http_prefix = "https://"
		msg += ", download via https"
	else:
		http_prefix = "http://"
		msg += ", download via http"

	global proxies
	if execcount % 4 < 2:
		proxies = {}
		msg += " + clearnet"
	else:
		msg += " + darknet"
		proxies = {
			'http': 'socks5h://127.0.0.1:9050',
			'https': 'socks5h://127.0.0.1:9050'
		}
	return msg

def download_one(name):
	try:
		page = requests.get(http_prefix + name + "/api/v1/instance", proxies=proxies, timeout=30)
		instance = json.loads(page.content.decode('utf-8'))
		rv = {}
		rv['status_count'] = int(instance['stats']['status_count'])
		rv['user_count'] = int(instance['stats']['user_count'])
		rv['uri'] = instance['uri']
		rv['name'] = name
		return rv
	except:
		pass

def close_msg(start_ts, memory_msg):
	timediff = int(time.time()) - start_ts
	s = timediff % 60
	timediff = timediff / 60
	m = timediff % 60
	h = timediff / 60
	print_ts("+ Finished in %02d:%02d%s"%(m, s, memory_msg))

def download_all(names, time_left, processes):
	args = []
	for i in range(len(names)):
		if not names[i].endswith('--'):
			args.append(names[i])

	pool = multiprocessing.Pool(processes)
	pool_result = pool.imap_unordered(download_one, args)
	timeout_it = timeout_iterator(pool_result, time_left)

	results = []
	try:
		last_print_ts = 0
		for i, rv in enumerate(timeout_it, 1):
			results.append(rv)
			current_ts = int(time.time())
			if current_ts > last_print_ts + 5:
				last_print_ts = current_ts
				print('\r%d of %d done'%(i, len(args)), end='', flush=True)
		print('\r', end='')
	except multiprocessing.context.TimeoutError:
		print(", but no more time left!!!")
	return results

def FindInData(name, data):
	if isinstance(data, dict):
		for d in data:
			if d == name:
				return data[name]
	if isinstance(data, list):
		for d in data:
			if d != None and 'name' in d and d['name'] == name:
				return d
	return None

def update_snapshot(snapshot, results, news):
	current_ts = int(time.time())
	snapshot["ts"] = current_ts
	if "data" not in snapshot:
		snapshot["data"] = {}

	user_count = 0
	status_count = 0
	instance_count = 0
	sn_data = snapshot["data"]
	new_names = []
	for rv in results:
		if rv == None:
			continue
		name = rv['name']
		uri = rv['uri']
		if uri.startswith("http://"):
			uri = uri[7:]
		if uri.startswith("https://"):
			uri = uri[8:]
		if name in news:
			if name != uri:
				print_ts("Name: %s uri: %s cannot be automerged to list, name and uri differs, users: %d"%(name, uri, rv['user_count']))
				continue
			if rv['user_count'] >= 500:
				print_ts("Name: %s uri: %s cannot be automerged to list, too many users: %d"%(name, uri, rv['user_count']))
				continue
			if FindInData(name, sn_data) != None:
				print_ts("Name: %s uri: %s cannot be automerged to list, name is already in the snapshot, users: %d"%(name, uri, rv['user_count']))
				continue
			print_ts("%s is automerged to list with %d users"%(name, rv['user_count']))
			new_names.append(name)
		uri_version = FindInData(uri, results)
		if name == uri or uri_version == None:
			# this is the preferred case
			user_count += rv['user_count']
			status_count += rv['status_count']
			instance_count += 1
		else:
			print_ts("Instance %s is in the results with its name and uri %s, users: %d vs %d"%(name, uri, rv['user_count'], uri_version['user_count']))
		if name != uri and FindInData(uri, sn_data) != None:
			sn_version = FindInData(name, sn_data)
			if sn_version == None:
				print_ts("Instance %s is in the snapshot with its uri %s, users: %d"%(name, uri, rv['user_count']))
			else:
				print_ts("Instance %s is in the snapshot with its name and uri %s, users: %d vs %d!!!"%(name, uri, sn_version['user_count'], rv['user_count']))
			name = uri
		old_user_count = sn_data.get(name, {}).get('user_count', 0)
		if old_user_count != 0 and rv['user_count'] > old_user_count + 1000:
			print_ts("Unexpected growth for instance %s: %d -> %d"%(name, old_user_count, rv['user_count']))
			continue
		sn_data[name] = {}
		sn_data[name]['user_count'] = rv['user_count']
		sn_data[name]['status_count'] = rv['status_count']
		sn_data[name]['ts'] = current_ts

	print_ts("+ Toots: %s, users: %s, instances: %s"%(status_count, user_count, instance_count))

	snapshot_file = "snapshot.json"
	with open(snapshot_file, 'w') as outfile:
		json.dump(snapshot, outfile, indent=4, sort_keys=True)
	return(new_names)

def update_stats(snapshot):
	user_count = 0
	toots_count = 0
	instance_count = 0
	for name in snapshot["data"]:
		s = snapshot["data"][name]
		user_count += s['user_count']
		toots_count += s['status_count']
		if int(snapshot["ts"]) <= int(s["ts"]) + 60*60*3:
			instance_count += 1

	masto_array = common.get_mastostats()

	prev_hour = datetime.now().replace(microsecond=0,second=0,minute=0)
	next_hour_ts = int(datetime.timestamp(prev_hour))+3600
	while masto_array[-1][0] == str(next_hour_ts):
		del masto_array[-1]

	mastostats_csv = "mastostats.csv"
	with open(mastostats_csv, 'w') as csvfile:
		writer = csv.writer(csvfile, lineterminator='\n')
		for row in masto_array:
			writer.writerow(row)
		writer.writerow([next_hour_ts, user_count, instance_count, toots_count])
	csvfile.close()

def main():
	start_ts = int(time.time())

	if 'psutil' in sys.modules:
		mem1 = psutil.virtual_memory()
	setup_environment()

	list_file = "list.json"
	names = common.get_json(list_file, default_value = [])

	if '--generate' in sys.argv:
		extended_names = extend_list(names)
		json.dump(extended_names, sys.stdout, indent=4, sort_keys=True)
		exit(0)

	if len(sys.argv) > 1:
		print("Invalid argument, exiting.")
		exit(0)

	snapshot_file = "snapshot.json"
	snapshot = common.get_json(snapshot_file, default_value = {})

	execcount = snapshot.get("execcount", 0)
	snapshot["execcount"] = execcount + 1

	msg = setup_request_params(execcount)

	extended_names = names if execcount % 5 != 1 else extend_list(names)

	config = common.get_json("config.txt", default_value = {})
	processes = config.get("processes", 25)
	msg += " using %d threads"%processes
	timeout = config.get("timeout", 720)
	if isinstance(timeout, int):
		time_left = timeout + start_ts - int(time.time())
	else:
		time_left = max(0, 3540 - int(time.time()) % 3600)
	msg += ", timeout %d secs"%time_left
	print_ts(msg)
	results = download_all(extended_names, time_left = time_left, processes = processes)
	news = set(extended_names).difference(set(names))
	new_names = update_snapshot(snapshot, results, news)
	update_stats(snapshot)
	if len(new_names) > 0:
		extended_names = sorted(list(set(new_names).union(set(names))))
		with open(list_file, 'w') as outfile:
			json.dump(extended_names, outfile, indent=4, sort_keys=True)
	if 'psutil' in sys.modules:
		mem2 = psutil.virtual_memory()
		memory_msg = ", free memory: %.2fG -> %.2fG of %.2fG"%(mem1.free / 1024.0**3, mem2.free / 1024.0**3, mem2.total / 1024.0 ** 3)
	else:
		memory_msg = ""
	close_msg(start_ts, memory_msg)

if __name__ == "__main__":
	main()
