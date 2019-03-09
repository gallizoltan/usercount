#!/bin/bash
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $SCRIPT_DIR

FILENAME=$(basename "$0" | cut -f 1 -d '.')
echo "Starting at: "$(date +"%Y-%m-%d %H:%M:%S") | tee -a $FILENAME.log
(stdbuf -o L ./$FILENAME.py $@ 3>&1 1>&2 2>&3 | tee -a $FILENAME.err) 2>&1  | tee -a $FILENAME.log

tail -9998 $FILENAME.log > $FILENAME.log.temp
mv $FILENAME.log.temp $FILENAME.log
