#!/usr/bin/python3
import os, sys, json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import common


def main():
	target = sys.argv[1]
	print("Banning %s"%target)
	list_file = "list.json"
	names = common.get_json(list_file, default_value = [])

	if target in names:
		for n, i in enumerate(names):
			if i == target:
				names[n] = target + "--"
	else:
		names.append(target + "--")
		names = sorted(names)

	with open(list_file, 'w') as outfile:
		json.dump(names, outfile, indent=4, sort_keys=True)

	snapshot_file = "snapshot.json"
	snapshot = common.get_json(snapshot_file, default_value = {})

	if target in snapshot["data"]:
		del snapshot["data"][target]
		common.save_json(snapshot_file, snapshot)

if __name__ == "__main__":
	main()

