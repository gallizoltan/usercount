#!/bin/bash
scritp_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $scritp_dir

echo -n "Starting at: " | tee -a publish.log
date +"%Y-%m-%d %H:%M:%S" | tee -a publish.log
(stdbuf -o L ./publish.py $@ 3>&1 1>&2 2>&3 | tee -a publish.err) 2>&1  | tee -a publish.log

tail -9998 publish.log > publish.log.temp
mv publish.log.temp publish.log
