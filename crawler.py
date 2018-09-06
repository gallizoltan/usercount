#!/usr/bin/python3

import json
import os
import requests
import multiprocessing
import time
import copy
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

os.chdir(os.path.dirname(os.path.abspath(__file__)))

pid = os.getppid()
cmd = open('/proc/%d/cmdline' %pid).read()
filename, file_extension = os.path.splitext(os.path.basename(__file__))
if os.path.basename(__file__) in cmd:
	# most likely started from crontab
	sys.stdout = open(filename + '.log', 'a')
	sys.stderr = sys.stdout

pid_file = filename + '.pid'
fp = open(pid_file, 'w')
try:
	fcntl.lockf(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
except IOError:
	print("Another instance is running, exiting.", file=sys.stderr)
	sys.exit(1)

atexit.register(os.remove, pid_file)

file_path = "list.json"
names = []
if os.path.isfile(file_path):
	with open( file_path ) as f:
		names = json.load(f)

if '--generate' in sys.argv:
	instances = {}
	page = requests.get('https://instances.social/instances.json')
	instances = json.loads(page.content.decode('utf-8'))
	new_names = []
	for i in instances:
		if "name" in i:
			beauty = i["name"].strip("/")
			beauty = beauty[beauty.rfind("@")+1:] if beauty.rfind("@") > -1 else beauty
			if beauty.endswith('.'):
				beauty = beauty[:-1]
			blacklisted = [s for s in names if s.endswith("--") and s.startswith(beauty)]
			if len(blacklisted) > 0:
				beauty = blacklisted[0]
			new_names.append(beauty)
	new_names = sorted(list(set(new_names).union(set(names))))
	json.dump(new_names, sys.stdout, indent=4, sort_keys=True)
	exit(0)

if len(sys.argv) > 1:
	print("Invalid argument, exiting.")
	exit(0)

start_ts = int(time.time())

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

def mp_worker(name):
	try:
		page = requests.get(http_prefix + name + "/api/v1/instance", proxies=proxies, timeout=30)
		instance = json.loads(page.content.decode('utf-8'))
		toots = int(instance['stats']['status_count'])
		users = int(instance['stats']['user_count'])
		#print("%s %s: users: %s toots: %s"%(procnum, name, str(users), str(toots)))
		rv = {}
		rv['status_count'] = toots
		rv['user_count'] = users
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
	msg = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S') + " crawler finished in "
	msg += "%02d:%02d"%(m, s)
	print(msg)

args = []
for i in range(len(names)):
	if not names[i].endswith('--'):
		args.append(names[i])

pool = multiprocessing.Pool(80)
pool_result = pool.imap_unordered(mp_worker, args)
timeout_it = timeout_iterator(pool_result, 570)

results = []
try:
	last_print_ts = 0
	for i, rv in enumerate(timeout_it, 1):
		results.append(rv)
		current_ts = int(time.time())
		if current_ts > last_print_ts + 1:
			last_print_ts = current_ts
			print('\r%d of %d done'%(i, len(args)), end='', flush=True)
	print('\r', end='')
except multiprocessing.context.TimeoutError as e:
	print()
	print("No more time left!!!" + str(e))

current_ts = int(time.time())
snapshot["ts"] = current_ts
if "data" not in snapshot:
	snapshot["data"] = {}

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

user_count = 0
toots_count = 0
instance_count = 0
data = snapshot["data"]
for rv in results:
	if rv == None:
		continue
	name = rv['name']
	uri = rv['uri']
	if uri.startswith("http://"):
		uri = uri[7:]
	if uri.startswith("https://"):
		uri = uri[8:]
	if name == uri or not IsInData(uri, results):
		user_count += rv['user_count']
		toots_count += rv['status_count']
		instance_count += 1
	if name != uri and IsInData(uri, data):
		if IsInData(name, data):
			print("!!! Instance %s is in the snapshot with its name and uri %s, users %s"%(name, uri, str(rv['user_count'])), file=sys.stderr)
		else:
			print("Instance %s is in the snapshot with its uri %s, users %s"%(name, uri, str(rv['user_count'])))
		name = uri
	data[name] = {}
	data[name]['user_count'] = rv['user_count']
	data[name]['status_count'] = rv['status_count']
	data[name]['ts'] = current_ts

print("Toots: %s, users: %s, instances: %s"%(toots_count, user_count, instance_count))

with open(snapshot_file, 'w') as outfile:
	json.dump(snapshot, outfile, indent=4, sort_keys=True)

close_msg(start_ts)
