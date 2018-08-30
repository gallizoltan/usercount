#!/usr/bin/python3

import json
import os
import requests
import multiprocessing
import time
import copy
import sys

snapshot = {}
snapshot_file = "snapshot.json"
if os.path.isfile(snapshot_file):
		with open( snapshot_file ) as f:
			snapshot = json.load(f)

old_snap = {}
snapshot_file = "old_snap.json"
if os.path.isfile(snapshot_file):
		with open( snapshot_file ) as f:
			old_snap = json.load(f)

merged = {}
merged["ts"] = snapshot["ts"]
merged["execcount"] = snapshot["execcount"]
merged["data"] = {}

for s in old_snap:
	merged["data"][s] = old_snap[s]
	merged["data"][s]["ts"] = 0

for s in snapshot["data"]:
	merged["data"][s] = snapshot["data"][s]

json.dump(merged, sys.stdout, indent=4, sort_keys=True)
