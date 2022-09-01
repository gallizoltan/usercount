#!/usr/bin/python3
import os, sys, json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import common


def main():
	target = sys.argv[1]
	print("Adding %s"%target)
	list_file = "list.json"
	names = common.get_json(list_file, default_value = [])
	names.append(target)
	names = sorted(names)
	common.save_json(list_file, names)


if __name__ == "__main__":
	main()

