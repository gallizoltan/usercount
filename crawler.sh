#!/bin/bash
scritp_dir="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd $scritp_dir

export TZ=Europe/Budapest

python3 -m compileall -l . > /dev/null
cp __pycache__/common.cpython*.pyc common.pyc
cp __pycache__/crawler.cpython*.pyc crawler.pyc

EXECCOUNT=$(grep -oP "execcount[^\-0-9]*\K[\-0-9]*" snapshot.json)
echo $(date +"%Y-%m-%d %H:%M:%S")" + Crawler Quadruple started with execcount $EXECCOUNT" | tee -a crawler.log
if [ $(($EXECCOUNT % 4)) -ne 0 ]; then
    EXECCOUNT2=$(($EXECCOUNT+4-$(($EXECCOUNT%4))))
    sed -i "s/\"execcount\": $EXECCOUNT,/\"execcount\": $EXECCOUNT2,/g" snapshot.json
fi

STARTTS=$(date +'%s')
killall crawler.py 2>/dev/null
for i in $(seq 1 4);
do
    stdbuf -o L python3 crawler.pyc $@ 2>&1 | tee -a crawler.log
done

LOGLINES=$(grep loglines "config.txt" | cut -f2 -d":" | cut -f2 -d"\"")
[ -z "$LOGLINES" ] && LOGLINES="9998"
tail -n $LOGLINES crawler.log > crawler.log.temp
mv crawler.log.temp crawler.log
tac crawler.log | grep --text -v "+" | grep -v "No time for crawl" | grep -v "[Nn]o more time left" | grep -v Shrinking | rev | cut -d$'\r' -f 1 | rev | egrep -v '[0-9]+ of [0-9]+ done' | uniq -f 2 | tac > crawler.err

RUNNING_TIME=$(($(date '+%s') - $STARTTS))
echo $(date +"%Y-%m-%d %H:%M:%S")" + Crawler Quadruple finished in "$(date -d @$RUNNING_TIME +"%M:%S") | tee -a crawler.log
