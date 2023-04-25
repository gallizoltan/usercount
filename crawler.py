#!/usr/bin/python3

import sys
sys.dont_write_bytecode = True
import os
import json
import csv
import requests
import multiprocessing
import time
import fcntl
from datetime import datetime
import pytz
import atexit
import signal
try:
    import psutil
except Exception:
    print("Run: \'pip3 install psutil\' to see memory consumption")
import common
from tools import banURI


class TimeoutError(Exception):
    def __init__(self, value="Timed Out"):
        self.value = value

    def __str__(self):
        return repr(self.value)


def timeout(seconds_before_timeout):
    def decorate(f):
        def handler(signum, frame):
            raise TimeoutError()

        def new_f(*args, **kwargs):
            old = signal.signal(signal.SIGALRM, handler)
            old_time_left = signal.alarm(seconds_before_timeout)
            if 0 < old_time_left < seconds_before_timeout:  # never lengthen existing timer
                signal.alarm(old_time_left)
            start_time = time.time()
            try:
                result = f(*args, **kwargs)
            finally:
                if old_time_left > 0:  # deduct f's run time from the saved timer
                    old_time_left -= time.time() - start_time
                signal.signal(signal.SIGALRM, old)
                signal.alarm(old_time_left)
            return result
        new_f.__name__ = f.__name__
        return new_f
    return decorate


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
    filename, file_extension = os.path.splitext(os.path.basename(__file__))
    lock_file = filename + '.pid'
    global fp
    fp = open(lock_file, 'w')
    try:
        # LOCK_EX - exclusive lock
        # LOCK_NB - don't block when locking
        fcntl.flock(fp, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fp.truncate()
        fp.write(str(os.getpid()))
        fp.flush()
    except IOError:
        print("Another instance is running, exiting.", file=sys.stderr)
        sys.exit(1)
    atexit.register(os.remove, lock_file)


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
    except Exception:
        pass
    new_names = sorted(list(set(new_names).union(set(names))))
    return(new_names)


def print_ts(msg):
    tz = pytz.timezone('Europe/Budapest')
    print(datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S') + " " + msg)


def setup_request_params(execcount, config):
    clearnetOnly = config.get("clearnet", True)
    execstr = ""
    global http_prefix
    if execcount % 2 == 0 or clearnetOnly:
        http_prefix = "https://"
        execstr += "https"
    else:
        http_prefix = "http://"
        execstr += "http"
    global proxies
    if execcount % 4 < 2 or clearnetOnly:
        proxies = {}
        execstr += " + clearnet"
    else:
        proxies = {
            'http': 'socks5h://127.0.0.1:9050',
            'https': 'socks5h://127.0.0.1:9050'
        }
        execstr += " + darknet"
    msg = "+ Crawler execution count: " + str(execcount)
    msg += ", download via " + execstr
    return msg


@timeout(60)
def download_one(name):
    try:
        page = requests.get(http_prefix + name + "/api/v1/instance", proxies=proxies, timeout=request_time)
        instance = json.loads(page.content.decode('utf-8'))
        rv = {}
        rv['status_count'] = int(instance['stats']['status_count'])
        rv['user_count'] = int(instance['stats']['user_count'])
        rv['uri'] = instance['uri']
        rv['name'] = name
        return rv
    except Exception:
        pass


def close_msg(start_ts, execcount, stat_msg):
    timediff = int(time.time()) - start_ts
    s = timediff % 60
    timediff = timediff / 60
    m = timediff % 60
    msg = "+ Finished in %02d:%02d" % (m, s)
    msg += stat_msg
    print_ts(msg)


def filter_frequented(name, snapshot):
    data = snapshot.get("data", {})
    if name not in data:
        return (hash(name) + snapshot.get("execcount", 0)) % 23 != 0
    current_ts = int(time.time())
    ts = int(data.get(name, {}).get("ts", current_ts))
    return current_ts - ts > 3600*24*7 and int((current_ts - ts) / 3600) % 49 != 0


def download_all(names, snapshot, time_left, processes):
    args = []
    for name in names:
        if name.endswith('--'):
            continue
        if filter_frequented(name, snapshot):
            continue
        args.append(name)

    pool = multiprocessing.Pool(processes)
    pool_result = pool.imap_unordered(download_one, args)
    timeout_it = timeout_iterator(pool_result, time_left)

    results = []
    last_print_ts = 0
    try:
        for i, rv in enumerate(timeout_it, 1):
            results.append(rv)
            current_ts = int(time.time())
            if current_ts > last_print_ts + 5:
                last_print_ts = current_ts
                print('\r%d of %d done' % (i, len(args)), end='', flush=True)
        print('\r', end='')
    except multiprocessing.context.TimeoutError:
        if last_print_ts == 0:
            print("No time for crawl!!!")
        else:
            print(", but no more time left!!!")
    pool.close()
    return results, len(args)


def FindInData(name, data):
    if isinstance(data, dict):
        for d in data:
            if d == name:
                return data[name]
    if isinstance(data, list):
        for d in data:
            if d is not None and 'name' in d and d['name'] == name:
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
    ban_names = []
    config = common.get_json("config.txt", default_value={})
    for rv in results:
        if rv is None:
            continue
        name = rv['name']
        uri = rv['uri']
        if type(uri) is dict:
            uri = ""
        if uri.startswith("http://"):
            uri = uri[7:]
        if uri.startswith("https://"):
            uri = uri[8:]
        if name in news:
            if len(new_names) > 10:
                continue
            if rv['user_count'] < 10:
                continue
            if rv['user_count'] > 500:
                print_ts("Name: %s uri: %s has too many users: %d" % (name, uri, rv['user_count']))
                rv['user_count'] = 500
            if FindInData(name, sn_data) is not None:
                print_ts("Name: %s uri: %s cannot be automerged to list, name is already in the snapshot, users: %d" % (name, uri, rv['user_count']))
                continue
            if name == uri:
                print_ts("%s is automerged to list with %d users" % (name, rv['user_count']))
                new_names.append(name)
            else:
                name_content = download_one(name)
                uri_content = download_one(uri)
                if name_content is not None and uri_content is None:
                    print_ts("Name: %s uri: %s merge conflict resolved with using name, users: %d" % (name, uri, rv['user_count']))
                    new_names.append(name)
                    new_names.append(uri + "--")
                elif name_content is None and uri_content is not None:
                    print_ts("Name: %s uri: %s merge conflict resolved with using uri, users: %d" % (name, uri, rv['user_count']))
                    new_names.append(name + "--")
                    new_names.append(uri)
                else:
                    print_ts("Name: %s uri: %s cannot be automerged to list, name and uri differs, users: %d" % (name, uri, rv['user_count']))
                    continue
        uri_version = FindInData(uri, results)
        if name == uri or uri_version is None:
            # this is the preferred case
            user_count += rv['user_count']
            status_count += rv['status_count']
            instance_count += 1
        else:
            print_ts("Instance %s is in the results with its name and uri %s, users: %d vs %d" % (name, uri, rv['user_count'], uri_version['user_count']))
            ban_names.append(name)
        if name != uri and FindInData(uri, sn_data) is not None:
            sn_version = FindInData(name, sn_data)
            if sn_version is None:
                print_ts("Instance %s is in the snapshot with its uri %s, users: %d" % (name, uri, rv['user_count']))
            else:
                print_ts("Instance %s is in the snapshot with its name and uri %s, users: %d vs %d!!!" % (name, uri, sn_version['user_count'], rv['user_count']))
            name = uri
        old_user_count = sn_data.get(name, {}).get('user_count', 0)
        if old_user_count != 0 and rv['user_count'] > old_user_count + 500 and rv['user_count'] > old_user_count * 1.002:
            print_ts(f"Unexpected growth for instance {name}: {old_user_count} -> {rv['user_count']} ~ {rv['user_count'] - old_user_count}")
            allowed_change = config.get("allowed_change." + name, max(100, int(old_user_count * 0.001)))
            sn_data[name]['user_count'] = min(rv['user_count'], sn_data[name]['user_count'] + allowed_change)
            sn_data[name]['status_count'] = rv['status_count']
            sn_data[name]['ts'] = current_ts
            continue
        if old_user_count > rv['user_count'] + 2:
            print_ts("Shrinking usercount in instance %s: %d -> %d" % (name, old_user_count, rv['user_count']))
            allowed_change = config.get("allowed_change." + name, max(20, int(old_user_count * 0.0002)))
            if old_user_count > rv['user_count'] + allowed_change:
                print_ts(f"Unexpected shrinking for instance {name}: {old_user_count} -> {rv['user_count']} ~ {old_user_count - rv['user_count']}")
                sn_data[name]['user_count'] = max(rv['user_count'], sn_data[name]['user_count'] - allowed_change)
                sn_data[name]['status_count'] = rv['status_count']
                sn_data[name]['ts'] = current_ts
                continue
        sn_data[name] = {}
        sn_data[name]['user_count'] = rv['user_count']
        sn_data[name]['status_count'] = rv['status_count']
        sn_data[name]['ts'] = current_ts

    print_ts("+ Toots: %s, users: %s, instances: %s" % (status_count, user_count, instance_count))

    snapshot_file = "snapshot.json"
    with open(snapshot_file, 'w') as outfile:
        json.dump(snapshot, outfile, indent=4, sort_keys=True)
    return new_names, ban_names


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

    prev_hour = datetime.now().replace(microsecond=0, second=0, minute=0)
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
    names = common.get_json(list_file, default_value=[])

    if '--generate' in sys.argv:
        extended_names = extend_list(names)
        json.dump(extended_names, sys.stdout, indent=4, sort_keys=True)
        exit(0)

    if len(sys.argv) > 1:
        print("Invalid argument, exiting.")
        exit(0)

    snapshot_file = "snapshot.json"
    snapshot = common.get_json(snapshot_file, default_value={})

    execcount = snapshot.get("execcount", 0)
    snapshot["execcount"] = execcount + 1

    config = common.get_json("config.txt", default_value={})
    msg = setup_request_params(execcount, config)

    extended_names = extend_list(names)

    processes = config.get("processes", 25)
    msg += " using %d threads" % processes
    timeout = config.get("timeout", 720)
    global request_time
    request_time = config.get("request_time", 15)
    if isinstance(timeout, int):
        time_left = timeout + start_ts - int(time.time())
    else:
        time_left = max(0, 3450 - int(time.time()) % 3600)
    msg += ", timeout %d secs" % time_left
    print_ts(msg)
    results, checked_instances = download_all(extended_names, snapshot, time_left=time_left, processes=processes)
    stat_msg = f", {checked_instances}/{len(extended_names)} instance checked"
    news = set(extended_names).difference(set(names))
    new_names, ban_names = update_snapshot(snapshot, results, news)
    update_stats(snapshot)
    if len(new_names) > 0:
        extended_names = sorted(list(set(new_names).union(set(names))))
        with open(list_file, 'w') as outfile:
            json.dump(extended_names, outfile, indent=4, sort_keys=True)
    for name in ban_names:
        banURI.ban_instance(name)
    if 'psutil' in sys.modules:
        mem2 = psutil.virtual_memory()
        stat_msg += ", free memory: %.2fG -> %.2fG of %.2fG" % (mem1.free / 1024.0**3, mem2.free / 1024.0**3, mem2.total / 1024.0 ** 3)
    close_msg(start_ts, execcount, stat_msg)


if __name__ == "__main__":
    main()
