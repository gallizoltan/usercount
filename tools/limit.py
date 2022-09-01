#!/usr/bin/python3
import os
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import common


def main():
    target = sys.argv[1]
    limit = sys.argv[2]
    print(f"Modifying change limit for {target} to {limit} per crawler run")
    filename = "config.txt"
    config = common.get_json("config.txt", default_value={})
    config["allowed_change." + target] = int(limit)
    common.save_json(filename, config)


if __name__ == "__main__":
    main()
