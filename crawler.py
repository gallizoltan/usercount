#!/usr/bin/python3

import sys
sys.dont_write_bytecode = True
import os
import json
import csv
import urllib.request
import time
import fcntl
from datetime import datetime
import pytz
import atexit
import urllib3
urllib3.disable_warnings(urllib3.exceptions.SecurityWarning)
try:
    import psutil
except Exception:
    print("Run: \'pip3 install psutil\' to see memory consumption")
import common
from tools import banURI
import threading
import concurrent.futures
import socket


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
        response = urllib.request.urlopen('https://instances.social/instances.json')
        instances = json.loads(response.read().decode('utf-8'))
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
    print(datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S') + " " + msg, flush=True)


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


def download_one_inner(name):
    response = urllib.request.urlopen(http_prefix + name + "/api/v1/instance")
    instance = json.loads(response.read().decode('utf-8'))
    rv = {}
    rv['status_count'] = int(instance['stats']['status_count'])
    rv['user_count'] = int(instance['stats']['user_count'])
    rv['uri'] = instance['uri']
    rv['name'] = name
    return rv


downloading = {}


def download_one(name):
    rv = None
    downloading[threading.get_ident()] = name
    try:
        rv = download_one_inner(name)
    except Exception:
        pass
    downloading[threading.get_ident()] = ""
    return rv


def name_picker(names, time_left):
    start_ts = int(time.time())
    counter = 0
    for name in names:
        if time_left + start_ts - int(time.time()) <= 0:
            break
        if names[name]["lock"].acquire(blocking=False):
            names[name]["ts"] = int(time.time())
            names[name]["result"] = download_one(name)
            counter += 1
    return counter


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
    if data == {}:
        return False
    if name not in data:
        return (hash(name) + snapshot.get("execcount", 0)) % 23 != 0
    current_ts = int(time.time())
    ts = int(data.get(name, {}).get("ts", current_ts))
    return current_ts - ts > 3600*24*7 and int((current_ts - ts) / 3600) % 49 != 0


futures = set()


def download_all(names, snapshot, time_left, processes):
    start_ts = int(time.time())
    args = {}
    for name in names:
        if name.endswith('--'):
            continue
        if filter_frequented(name, snapshot):
            continue
        args[name] = {}
        args[name]["lock"] = threading.Lock()

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=processes)
    for threadid in range(processes):
        futures.add(executor.submit(name_picker, args, time_left))

    results = []
    timeout = time_left + start_ts - int(time.time()) <= 0
    if timeout:
        print("No time for crawl!!!")
    while not timeout:
        instance_done = sum(args[a]["lock"].locked() for a in args)
        print('\r%d of %d done' % (instance_done, len(args)), end='', flush=True)
        max_ts = max(args[a].get("ts", 0) for a in args)
        future_done = sum(future.done() for future in futures)
        if len(futures) == future_done or max_ts + request_time + 5 < int(time.time()):
            print('\r', end='', flush=True)
            break
        timeout = time_left + start_ts - int(time.time()) <= 0
        if timeout:
            print(", but no more time left!!!")
            break
        time.sleep(5)
    for ids in downloading:
        if downloading[ids] != "":
            print_ts(f"! {downloading[ids]} gets stuck")
    for name in args:
        results.append(args[name].get("result"))
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
                print_ts(f"- Name: {name} uri: {uri} has too many users: {rv['user_count']}")
                continue
            if FindInData(name, sn_data) is not None:
                print_ts(f"! Name: {name} uri: {uri} cannot be automerged to list, name is already in the snapshot, users: {rv['user_count']}")
                continue
            if name == uri:
                print_ts(f"+ {name} is automerged to list with {rv['user_count']} users")
                new_names.append(name)
            else:
                name_content = download_one(name)
                uri_content = download_one(uri)
                if name_content is not None and uri_content is None:
                    print_ts(f"+ Name: {name} uri: {uri}  merge conflict resolved with using name, users: {rv['user_count']}")
                    new_names.append(name)
                    new_names.append(uri + "--")
                elif name_content is None and uri_content is not None:
                    print_ts(f"+ Name: {name} uri: {uri}  merge conflict resolved with using uri, users: {rv['user_count']}")
                    new_names.append(name + "--")
                    new_names.append(uri)
                else:
                    print_ts(f"! Name: {name} uri: {uri} cannot be automerged to list, name and uri differs, users: {rv['user_count']}")
                    continue
        uri_version = FindInData(uri, results)
        if name == uri or uri_version is None:
            # this is the preferred case
            user_count += rv['user_count']
            status_count += rv['status_count']
            instance_count += 1
        else:
            print_ts(f"! Instance {name} is in the results with its name and uri {uri}, users: {rv['user_count']} vs {uri_version['user_count']}")
            ban_names.append(name)
        if name != uri and FindInData(uri, sn_data) is not None:
            sn_version = FindInData(name, sn_data)
            if sn_version is None:
                print_ts(f"! Instance {name} is in the snapshot with its uri {uri}, users: {rv['user_count']}")
            else:
                print_ts(f"! Instance {name} is in the snapshot with its name and uri {uri}, users: {sn_version['user_count']} vs {rv['user_count']}!!!")
            name = uri
        old_user_count = sn_data.get(name, {}).get('user_count', 0)
        if old_user_count != 0 and rv['user_count'] > old_user_count + 500 and rv['user_count'] > old_user_count * 1.002:
            print_ts(f"- Unexpected growth for instance {name}: {old_user_count} -> {rv['user_count']} ~ {rv['user_count'] - old_user_count}")
            allowed_change = config.get("allowed_change." + name, max(100, int(old_user_count * 0.001)))
            sn_data[name]['user_count'] = min(rv['user_count'], sn_data[name]['user_count'] + allowed_change)
            sn_data[name]['status_count'] = rv['status_count']
            sn_data[name]['ts'] = current_ts
            continue
        if old_user_count > rv['user_count'] + 2:
            print_ts(f"- Shrinking usercount in instance {name}: {old_user_count} -> {rv['user_count']}")
            allowed_change = config.get("allowed_change." + name, max(20, int(old_user_count * 0.0002)))
            if old_user_count > rv['user_count'] + allowed_change:
                print_ts(f"- Unexpected shrinking for instance {name}: {old_user_count} -> {rv['user_count']} ~ {old_user_count - rv['user_count']}")
                sn_data[name]['user_count'] = max(rv['user_count'], sn_data[name]['user_count'] - allowed_change)
                sn_data[name]['status_count'] = rv['status_count']
                sn_data[name]['ts'] = current_ts
                continue
        sn_data[name] = {}
        sn_data[name]['user_count'] = rv['user_count']
        sn_data[name]['status_count'] = rv['status_count']
        sn_data[name]['ts'] = current_ts

    print_ts(f"+ Toots: {status_count}, users: {user_count}, instances: {instance_count}")

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
    socket.setdefaulttimeout(request_time)
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
    done = sum(future.done() for future in futures)
    if done < len(futures):
        print_ts(f"! {done} of {len(futures)} futures done, killing process")
        os.kill(os.getpid(), 9)
