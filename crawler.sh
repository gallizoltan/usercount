#!/bin/bash
scritp_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $scritp_dir

killall crawler.py
stdbuf -o L ./crawler.py $@ 2>&1 | tee -a crawler.log

tail -998 crawler.log > crawler.log.temp
mv crawler.log.temp crawler.log
