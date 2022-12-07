#!/usr/bin/python3

import os
import sys
from subprocess import call
from mastodon import Mastodon
import time
import common


def get_mastodon(config_file):
    config = common.get_json(config_file)
    if config is None:
        print("File %s not found, exiting." % config_file, file=sys.stderr)
        sys.exit(1)
    mastodon = Mastodon(
        client_id     = config["client_id"],
        client_secret = config["client_secret"],
        access_token  = config["access_token"],
        api_base_url  = 'https://' + config["mastodon_hostname"]  # E.g., mastodon.social
    )
    return mastodon


def find_closest_timestamp(input_array, seek_timestamp):
    closest = input_array[-1]
    for item in reversed(input_array):
        if abs(int(closest[0])-seek_timestamp) >= abs(int(item[0])-seek_timestamp):
            closest = item
        else:
            return closest
    return closest


def main():
    # config.txt, mastostats.csv, generate.gnuplot, etc. are in the same folder as this file
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    masto_array = common.get_mastostats()
    del masto_array[0]

    ts = int(time.time())
    current_val = find_closest_timestamp(masto_array, ts)
    user_count = int(current_val[1])

    print("Number of users: %s " % user_count)
    print("Number of toots: %s " % current_val[3])
    print("Number of instances: %s " % current_val[2])

    toot_text = format(user_count, ",d") + " accounts \n"
    one_hour = 60 * 60
    hours = [1, 24, 168]
    prefix = ["Hourly", "Daily", "Weekly"]
    suffix = ["hour", "day", "week"]

    # Calculate difference in times
    for i in range(3):
        if len(masto_array) <= hours[i]:
            continue
        old_ts = ts - hours[i] * one_hour
        old_val = find_closest_timestamp(masto_array, old_ts)
        change = user_count - int(old_val[1])
        print("%s change %s" % (prefix[i], change))
        if change > 0:
            toot_text += "+" + format(change, ",d") + " in the last " + suffix[i] + "\n"

    # Generate chart
    call(["gnuplot", "generate.gnuplot"])

    # Upload chart
    file_to_upload = 'graph.png'
    mastodon = get_mastodon(config_file="config.txt")

    for i in range(3):
        try:
            media_dict = None
            print("Uploading %s..." % file_to_upload)
            media_dict = mastodon.media_post(file_to_upload)
            print("Uploaded file, returned:")
            print(str(media_dict))
            print("Tooting...")
            print(toot_text, end='')
            mastodon.status_post(toot_text, in_reply_to_id=None, media_ids=[media_dict])
            print("Successfully tooted!")
            sys.exit(0)
        except Exception as e:
            print("Exception while uploading: " + str(e), file=sys.stderr)
            time.sleep(3)
    sys.exit(1)


if __name__ == "__main__":
    main()
