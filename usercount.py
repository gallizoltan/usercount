#!/usr/bin/python

from __future__ import print_function
from subprocess import call
from mastodon import Mastodon
import csv
import os
import json
import time, datetime
import sys
import requests       # For doing the web stuff, dummy!

###############################################################################
# INITIALISATION
###############################################################################

no_upload = False
# Run without uploading, if specified
if '--no-upload' in sys.argv:
    no_upload = True

no_update = False
# Run without uploading, if specified
if '--no-update' in sys.argv:
    no_update = True

# config.txt, mastostats.csv, generate.gnuplot, etc. are in the same folder as this file
os.chdir(os.path.dirname(os.path.abspath(__file__)))

# Check mastostats.csv exists, if not, create it
if not os.path.isfile("mastostats.csv"):    
        print("mastostats.csv does not exist, creating it...")

        # Create CSV header row
        with open("mastostats.csv", "w") as myfile:
            myfile.write("timestamp,usercount,instancecount,tootscount\n")
        myfile.close()

# Returns the parameter from the specified file
def get_parameter( parameter, file_path ):
    # Check if config file exists
    if not os.path.isfile(file_path):    
        print("File %s not found, exiting."%file_path)
        sys.exit(1)

    # Find parameter in file
    with open( file_path ) as f:
        for line in f:
            if line.startswith( parameter ):
                return line.replace(parameter + ":", "").strip()

    # Cannot find parameter, exit
    print(file_path + "  Missing parameter %s "%parameter)
    sys.exit(1)

def get_mastodon(config_filepath):
    # Load configuration from config file
    mastodon_hostname = get_parameter("mastodon_hostname", config_filepath) # E.g., mastodon.social
    uc_client_id      = get_parameter("uc_client_id",      config_filepath)
    uc_client_secret  = get_parameter("uc_client_secret",  config_filepath)
    uc_access_token   = get_parameter("uc_access_token",   config_filepath)

    # Initialise Mastodon API
    mastodon = Mastodon(
        client_id = uc_client_id,
        client_secret = uc_client_secret,
        access_token = uc_access_token,
        api_base_url = 'https://' + mastodon_hostname,
    )
    return mastodon

###############################################################################
# GET THE DATA
###############################################################################

# Get current timestamp
ts = int(time.time())

page = requests.get('https://instances.social/instances.json')

instances = json.loads(page.content.decode('utf-8'))

def get_value(d, n):
    if n not in d: return 0
    if d[n] == None: return 0
    return int(d[n])

user_count = 0
instance_count = 0
toots_count = 0
for instance in instances:
    user_count += get_value(instance, "users")
    toots_count += get_value(instance, "statuses")
    if instance["up"] == True:
        instance_count += 1

print("Number of users: %s " % user_count)
print("Number of instances: %s " % instance_count)
print("Number of toots: %s " % toots_count)

###############################################################################
# LOG THE DATA
###############################################################################

# Append to CSV file
if no_update:
    print("--no-update specified, so skip mastostats.csv update")
else:
    with open("mastostats.csv", "a") as myfile:
        myfile.write(str(ts) + "," + str(user_count) + "," + str(instance_count) + "," + str(toots_count) + "\n")

###############################################################################
# WORK OUT THE TOOT TEXT
###############################################################################

# Load CSV file
with open('mastostats.csv') as f:
    usercount_dict = [{k: int(v) for k, v in row.items()}
        for row in csv.DictReader(f, skipinitialspace=True)]

# Returns the timestamp,usercount pair which is closest to the specified timestamp
def find_closest_timestamp( input_dict, seek_timestamp ):
    a = []
    for item in input_dict:
        a.append( item['timestamp'] )
    return input_dict[ min(range(len(a)), key=lambda i: abs(a[i]-seek_timestamp)) ]

def print_instance_info(msg):
    print(msg + " at: " + datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'), file=sys.stderr)
    print("Instance info:", file=sys.stderr)
    for instance in instances:
        if not "users" in instance: continue
        if instance["users"] == None: continue
        print(instance["name"].encode('utf-8') + ": " + str(instance["users"]), file=sys.stderr)

# Calculate difference in times
hourly_change_string = ""
daily_change_string  = ""
weekly_change_string = ""

one_hour = 60 * 60
one_day  = one_hour * 24
one_week = one_hour * 168

# Hourly change
if len(usercount_dict) > 2:
    one_hour_ago_ts = ts - one_hour
    one_hour_ago_val = find_closest_timestamp( usercount_dict, one_hour_ago_ts )
    hourly_change = user_count - one_hour_ago_val['usercount']
    print("Hourly change %s"%hourly_change)
    if hourly_change > 0:
        hourly_change_string = "+" + format(hourly_change, ",d") + " in the last hour\n"
        if hourly_change > user_count / 100:
            print_instance_info("User count suspiciously increased")
    if hourly_change < 0:
        print_instance_info("User count decreased")

# Daily change
if len(usercount_dict) > 24:
    one_day_ago_ts = ts - one_day
    one_day_ago_val = find_closest_timestamp( usercount_dict, one_day_ago_ts )
    daily_change = user_count - one_day_ago_val['usercount']
    print("Daily change %s"%daily_change)
    if daily_change > 0:
        daily_change_string = "+" + format(daily_change, ",d") + " in the last day\n"

# Weekly change
if len(usercount_dict) > 168:
    one_week_ago_ts = ts - one_week
    one_week_ago_val = find_closest_timestamp( usercount_dict, one_week_ago_ts )
    weekly_change = user_count - one_week_ago_val['usercount']
    print("Weekly change %s"%weekly_change)
    if weekly_change > 0:
        weekly_change_string = "+" + format(weekly_change, ",d") + " in the last week\n"


###############################################################################
# CREATE AND UPLOAD THE CHART
###############################################################################

# Generate chart
FNULL = open(os.devnull, 'w')
call(["gnuplot", "generate.gnuplot"], stdout=FNULL, stderr=FNULL)


if no_upload:
    print("--no-upload specified, so not uploading anything")
    sys.exit(0)

mastodon = get_mastodon(config_filepath = "config.txt")
# Upload chart
file_to_upload = 'graph.png'

media_dict = None
try:
    print("Uploading %s..."%file_to_upload)
    media_dict = mastodon.media_post(file_to_upload)

    print("Uploaded file, returned:")
    print(str(media_dict))
except Exception as e:
    print("Exception while uploading: " + str(e), file=sys.stderr)

###############################################################################
# T  O  O  T !
###############################################################################

toot_text = format(user_count, ",d") + " accounts \n"
toot_text += hourly_change_string
toot_text += daily_change_string
toot_text += weekly_change_string

print("Tooting...")
print(toot_text, end='')

mastodon.status_post(toot_text, in_reply_to_id=None, media_ids=[media_dict] )

print("Successfully tooted!")
