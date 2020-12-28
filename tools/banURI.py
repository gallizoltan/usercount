#!/usr/bin/python3

import os, sys, json
def get_json(filename, default_value = None):
	if os.path.isfile(filename):
		with open( filename ) as f:
			return json.load(f)
	return default_value

def main():
	target = sys.argv[1]
	print("Banning %s"%target)
	list_file = "list.json"
	names = get_json(list_file, default_value = [])

	for n, i in enumerate(names):
		if i == target:
			names[n] = target + "--"

	with open(list_file, 'w') as outfile:
		json.dump(names, outfile, indent=4, sort_keys=True)

	snapshot_file = "snapshot.json"
	snapshot = get_json(snapshot_file, default_value = {})

	if target in snapshot["data"]:
		del snapshot["data"][target]
		with open(snapshot_file, 'w') as outfile:
			json.dump(snapshot, outfile, indent=4, sort_keys=True)

if __name__ == "__main__":
	main()

