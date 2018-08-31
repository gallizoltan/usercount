#!/usr/bin/python3

from subprocess import call
from mastodon import Mastodon
import csv
import os
import json
import time
import sys
import requests       # For doing the web stuff, dummy!

###############################################################################
# INITIALISATION
###############################################################################

no_upload = False
if '--no-upload' in sys.argv:
    no_upload = True

no_update = False
if '--no-update' in sys.argv:
    no_update = True

# config.txt, mastostats.csv, generate.gnuplot, etc. are in the same folder as this file
os.chdir(os.path.dirname(os.path.abspath(__file__)))

mastostats_csv = "mastostats.csv"

# Check mastostats_csv exists, if not, create it
if not os.path.isfile(mastostats_csv):
    print("%s does not exist, creating it..." % mastostats_csv)
    # Create CSV header row
    with open(mastostats_csv, "w") as myfile:
        myfile.write("timestamp,usercount,instancecount,tootscount\n")
    myfile.close()

def get_config(file_path):
    if os.path.isfile(file_path):
        with open( file_path ) as f:
            return json.load(f)
    print("File %s not found, exiting."%file_path)
    sys.exit(1)

def get_mastodon(config_filepath):
    config = get_config(config_filepath)
    mastodon = Mastodon(
        client_id     = config["client_id"],
        client_secret = config["client_secret"],
        access_token  = config["access_token"],
        api_base_url  = 'https://' + config["mastodon_hostname"] # E.g., mastodon.social
    )
    return mastodon

###############################################################################
# GET THE DATA
###############################################################################

ts = int(time.time())
user_count = 0
toots_count = 0
instance_count = 0

snapshot_file="snapshot.json"
if os.path.isfile(snapshot_file):
	with open( snapshot_file ) as f:
		snapshot = json.load(f)
	for name in snapshot["data"]:
		s = snapshot["data"][name]
		user_count += s['user_count']
		toots_count += s['status_count']
		if int(snapshot["ts"]) <= int(s["ts"]) + 60*60:
			instance_count += 1

print("Number of users: %s " % user_count)
print("Number of instances: %s " % instance_count)
print("Number of toots: %s " % toots_count)

###############################################################################
# LOG THE DATA
###############################################################################

# Append to CSV file
if no_update:
    print("--no-update specified, so skip %s update" % mastostats_csv)
else:
    with open(mastostats_csv, "a") as myfile:
        myfile.write(str(ts) + "," + str(user_count) + "," + str(instance_count) + "," + str(toots_count) + "\n")

###############################################################################
# WORK OUT THE TOOT TEXT
###############################################################################

# Load CSV file
with open(mastostats_csv) as f:
    usercount_dict = [{k: int(v) for k, v in row.items()}
        for row in csv.DictReader(f, skipinitialspace=True)]

# Returns the timestamp,usercount pair which is closest to the specified timestamp
def find_closest_timestamp( input_dict, seek_timestamp ):
    a = []
    for item in input_dict:
        a.append( item['timestamp'] )
    return input_dict[ min(range(len(a)), key=lambda i: abs(a[i]-seek_timestamp)) ]

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

if no_upload:
    print("--no-upload specified, so not uploading anything")
    sys.exit(0)

# Upload chart
file_to_upload = 'graph.png'
mastodon = get_mastodon(config_filepath = "config.txt")

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
