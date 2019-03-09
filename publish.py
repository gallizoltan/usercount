#!/usr/bin/python3

from subprocess import call
from mastodon import Mastodon
import json, csv
import os, sys
import time

# config.txt, mastostats.csv, generate.gnuplot, etc. are in the same folder as this file
os.chdir(os.path.dirname(os.path.abspath(__file__)))

def get_config(filename):
    if os.path.isfile(filename):
        with open( filename ) as f:
            return json.load(f)
    print("File %s not found, exiting."%filename, file=sys.stderr)
    sys.exit(1)

def get_mastodon(config_file):
    config = get_config(config_file)
    mastodon = Mastodon(
        client_id     = config["client_id"],
        client_secret = config["client_secret"],
        access_token  = config["access_token"],
        api_base_url  = 'https://' + config["mastodon_hostname"] # E.g., mastodon.social
    )
    return mastodon

# Load CSV file
mastostats_csv = "mastostats.csv"
with open(mastostats_csv) as f:
    usercount_dict = [{k: int(v) for k, v in row.items()}
        for row in csv.DictReader(f, skipinitialspace=True)]

# Returns the timestamp,usercount pair which is closest to the specified timestamp
def find_closest_timestamp( input_dict, seek_timestamp ):
    a = []
    for item in input_dict:
        a.append( item['timestamp'] )
    return input_dict[ min(range(len(a)), key=lambda i: abs(a[i]-seek_timestamp)) ]

ts = int(time.time())
current_val = find_closest_timestamp( usercount_dict, ts )
user_count = current_val['usercount']

print("Number of users: %s " % user_count)
print("Number of toots: %s " % current_val['tootscount'])
print("Number of instances: %s " % current_val['instancecount'])

toot_text = format(user_count, ",d") + " accounts \n"
one_hour = 60 * 60
hours = [1, 24, 168]
prefix = ["Hourly", "Daily", "Weekly"]
suffix = ["hour", "day", "week"]

# Calculate difference in times
for i in range(3):
    if len(usercount_dict) <= hours[i]: continue
    old_ts = ts - hours[i] * one_hour
    old_val = find_closest_timestamp( usercount_dict, old_ts )
    change = user_count - old_val['usercount']
    print("%s change %s" % (prefix[i], change))
    if change > 0:
        toot_text += "+" + format(change, ",d") + " in the last " + suffix[i] + "\n"

# Generate chart
FNULL = open(os.devnull, 'w')
call(["gnuplot", "generate.gnuplot"])

# Upload chart
file_to_upload = 'graph.png'
mastodon = get_mastodon(config_file = "config.txt")

media_dict = None
try:
    print("Uploading %s..."%file_to_upload)
    media_dict = mastodon.media_post(file_to_upload)

    print("Uploaded file, returned:")
    print(str(media_dict))
except Exception as e:
    print("Exception while uploading: " + str(e), file=sys.stderr)

print("Tooting...")
print(toot_text, end='')

mastodon.status_post(toot_text, in_reply_to_id=None, media_ids=[media_dict] )

print("Successfully tooted!")
