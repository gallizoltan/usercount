#!/usr/bin/python3
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import pytz
from datetime import datetime
import common

def ban_instance(target):
    tz = pytz.timezone('Europe/Budapest')
    print(datetime.now(tz).strftime('%Y-%m-%d %H:%M:%S') + " + Banning " + target)
    list_file = "list.json"
    names = common.get_json(list_file, default_value=[])

    if target in names:
        for n, i in enumerate(names):
            if i == target:
                names[n] = target + "--"
    else:
        names.append(target + "--")
        names = sorted(names)

    common.save_json(list_file, names)

    snapshot_file = "snapshot.json"
    snapshot = common.get_json(snapshot_file, default_value={})

    if target in snapshot["data"]:
        del snapshot["data"][target]
        common.save_json(snapshot_file, snapshot)


def main():
    ban_instance(sys.argv[1])


if __name__ == "__main__":
    main()
