#!/bin/bash
scritp_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $scritp_dir

export TZ=Europe/Budapest

echo $(date +"%Y-%m-%d %H:%M:%S")" + Crawler Quadruple started" | tee -a crawler.log
STARTTS=$(date +'%s')
killall crawler.py 2>/dev/null
for i in $(seq 1 4);
do
	stdbuf -o L ./crawler.py $@ 2>&1 | tee -a crawler.log
done

LOGLINES=$(grep loglines "config.txt" | cut -f2 -d":" | cut -f2 -d"\"")
[ -z "$LOGLINES" ] && LOGLINES="9998"
tail -n $LOGLINES crawler.log > crawler.log.temp
mv crawler.log.temp crawler.log
tac crawler.log | grep -v "+" | grep -v "[Nn]o more time left" | grep -v " done$" | rev | cut -d$'\r' -f 1 | rev | uniq -f 2 | tac > crawler.err

RUNNING_TIME=$(($(date '+%s') - $STARTTS))
echo $(date +"%Y-%m-%d %H:%M:%S")" + Crawler Quadruple finised in "$(date -d @$RUNNING_TIME +"%M:%S") | tee -a crawler.log
