#!/bin/bash
scritp_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $scritp_dir

echo -n "Starting at: " | tee -a usercount.log
date +"%Y-%m-%d %H:%M:%S" | tee -a usercount.log
(stdbuf -o L ./usercount.py $@ 3>&1 1>&2 2>&3 | tee -a usercount.err) 2>&1  | tee -a usercount.log
tail -9998 usercount.log > usercount.log.temp
mv usercount.log.temp usercount.log

BACKUP=`grep backup_folder config.txt | cut -f2 -d":" | tr -d '\" '`
if [ "$BACKUP" != "" ]
then
	TS=`date +"%d"`
	cp mastostats.csv "$BACKUP""$TS"mastostats.csv
	cp snapshot.json "$BACKUP""$TS"snapshot.json
	cp list.json "$BACKUP""$TS"list.json
fi
