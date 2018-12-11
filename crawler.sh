#!/bin/bash
scritp_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $scritp_dir

killall crawler.py
stdbuf -o L ./crawler.py $@ 2>&1 | tee -a crawler.log

LOGLINES=$(grep loglines "config.txt" | cut -f2 -d":" | cut -f2 -d"\"")
[ -z "$LOGLINES" ] && LOGLINES="9998"
tail -n $LOGLINES crawler.log > crawler.log.temp
mv crawler.log.temp crawler.log
tac crawler.log | grep -v "+" | grep -v "[Nn]o more time left" | grep -v " done$" | rev | cut -d$'\r' -f 1 | rev | uniq -f 2 | tac > crawler.err
