#!/bin/sh
logger "$0"
cd `dirname $0`
./set_modules.sh
python set_tilt.py
logger "killing startsensor.sh"
sudo killall -9 startsensor.sh
rm nohup.out
nice nohup python led_renderer.py $1 &
sleep 2
nohup ./startsensor.sh $1 &
