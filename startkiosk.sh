#!/bin/sh
cd `dirname $0`
sudo rm nohup.out
sudo nice nohup python led_renderer.py &
sleep 2
sudo nohup ./startsensor.sh debug &
