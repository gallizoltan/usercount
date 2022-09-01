import json
import csv
import os


def get_json(filename, default_value=None):
    if os.path.isfile(filename):
        with open(filename) as f:
            return json.load(f)
    return default_value


def save_json(filename, values):
    with open(filename, 'w') as outfile:
        json.dump(values, outfile, indent=4, sort_keys=True)


def get_mastostats():
    mastostats_csv = "mastostats.csv"
    masto_array = [['timestamp', 'usercount', 'instancecount', 'tootscount']]
    if os.path.isfile(mastostats_csv):
        with open(mastostats_csv, 'r') as csvfile:
            reader = csv.reader(csvfile)
            masto_array = [row for row in reader]
        csvfile.close()
    return masto_array
