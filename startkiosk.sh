#!/bin/sh
cd `dirname $0`
sudo nice python led_renderer.py &
sudo nohup ./startsensor.sh
