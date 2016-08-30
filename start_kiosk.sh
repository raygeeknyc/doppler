#!/bin/sh
logger "$0"
logger "killing startsensor.sh"
sudo killall -9 startsensor.sh
cd `dirname $0`
rm nohup.out
nice nohup python led_renderer.py $1 &
sleep 2
nohup ./startsensor.sh $1 &
