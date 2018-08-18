#!/bin/bash
scritp_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $scritp_dir
echo -n "Starting at: " | tee -a usercount.log
date +"%Y-%m-%d %H:%M:%S" | tee -a usercount.log
(stdbuf -o L ./usercount.py $1 | tee -a usercount.log) 3>&1 1>&2 2>&3 | tee -a usercount.err
tail -9998 usercount.log > usercount.log.temp
mv usercount.log.temp usercount.log
