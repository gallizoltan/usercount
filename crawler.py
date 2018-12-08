#!/usr/bin/python3

import json
import os
import requests
import multiprocessing
import time
import fcntl, sys
import datetime
import atexit

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
				if any(s.startswith(beauty) and s.endswith("--") for s in names):
					continue
				new_names.append(beauty)
	except:
		pass
	new_names = sorted(list(set(new_names).union(set(names))))
	return(new_names)

def print_ts(msg):
	print(datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " " + msg)

def setup_request_params(execcount):
	msg = "+ Crawler execution count: " + str(execcount)
	global http_prefix
	if execcount % 2 == 0:
		http_prefix = "https://"
		msg += ", using https"
	else:
		http_prefix = "http://"
		msg += ", using http"

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
	print_ts(msg)

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

def close_msg(start_ts):
	timediff = int(time.time()) - start_ts
	s = timediff % 60
	timediff = timediff / 60
	m = timediff % 60
	h = timediff / 60
	print_ts("+ Crawler finished in %02d:%02d"%(m, s))

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
	except multiprocessing.context.TimeoutError as e:
		print()
		print_ts("No more time left!!!" + str(e))
	return results

def IsInData(name, data):
	if isinstance(data, dict):
		for d in data:
			if d == name:
				return True
	if isinstance(data, list):
		for d in data:
			if d != None and 'uri' in d and d['uri'] == name:
				return True
	return False

def update_snapshot(snapshot, results, news):
	current_ts = int(time.time())
	snapshot["ts"] = current_ts
	if "data" not in snapshot:
		snapshot["data"] = {}

	user_count = 0
	toots_count = 0
	instance_count = 0
	data = snapshot["data"]
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
				print_ts("Name: %s uri: %s cannot be automerged to list, name and uri differs"%(name, uri))
				continue
			if rv['user_count'] >= 500:
				print_ts("Name: %s uri: %s cannot be automerged to list, too many users: %d"%(name, uri, rv['user_count']))
				continue
			if IsInData(name, data):
				print_ts("Name: %s uri: %s cannot be automerged to list, name is already in the snapshot"%(name, uri))
				continue
			print_ts("%s is automerged to list with %d users"%(name, rv['user_count']))
			new_names.append(name)
		if name == uri or not IsInData(uri, results):
			user_count += rv['user_count']
			toots_count += rv['status_count']
			instance_count += 1
		if name != uri and IsInData(uri, data):
			if IsInData(name, data):
				print_ts("Instance %s is in the snapshot with its name and uri %s, users %s!!!"%(name, uri, str(rv['user_count'])))
			else:
				print_ts("Instance %s is in the snapshot with its uri %s, users %s"%(name, uri, str(rv['user_count'])))
			name = uri
		data[name] = {}
		data[name]['user_count'] = rv['user_count']
		data[name]['status_count'] = rv['status_count']
		data[name]['ts'] = current_ts

	print_ts("+ Toots: %s, users: %s, instances: %s"%(toots_count, user_count, instance_count))

	snapshot_file = "snapshot.json"
	with open(snapshot_file, 'w') as outfile:
		json.dump(snapshot, outfile, indent=4, sort_keys=True)
	return(new_names)

def get_json(filename, default_value = None):
	if os.path.isfile(filename):
		with open( filename ) as f:
			return json.load(f)
	return default_value

def main():
	start_ts = int(time.time())

	setup_environment()

	list_file = "list.json"
	names = get_json(list_file, default_value = [])

	if '--generate' in sys.argv:
		extended_names = extend_list(names)
		json.dump(extended_names, sys.stdout, indent=4, sort_keys=True)
		exit(0)

	if len(sys.argv) > 1:
		print("Invalid argument, exiting.")
		exit(0)

	snapshot_file = "snapshot.json"
	snapshot = get_json(snapshot_file, default_value = {})

	execcount = snapshot.get("execcount", 0) + 1
	snapshot["execcount"] = execcount

	setup_request_params(execcount)

	extended_names = names if execcount % 5 != 1 else extend_list(names)

	config = get_json("config.txt", default_value = {})
	results = download_all(extended_names, time_left = config.get("timeout", 720) + start_ts - int(time.time()), processes = config.get("processes", 25))
	news = set(extended_names).difference(set(names))
	new_names = update_snapshot(snapshot, results, news)
	if len(new_names) > 0:
		extended_names = sorted(list(set(new_names).union(set(names))))
		with open(list_file, 'w') as outfile:
			json.dump(extended_names, outfile, indent=4, sort_keys=True)
	close_msg(start_ts)

if __name__ == "__main__":
	main()
