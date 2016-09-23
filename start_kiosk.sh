#!/bin/sh
logger "$0"
cd `dirname $0`
./set_modules.sh
python set_tilt.py -1
logger "killing startsensor.sh"
sudo killall -9 startsensor.sh
sudo rm nohup.out
nice nohup sudo python led_renderer.py $1 &
sleep 2
nohup ./startsensor.sh $1 &
