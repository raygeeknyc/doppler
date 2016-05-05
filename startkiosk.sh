#!/bin/sh
cd `basename $0`
sudo nohup nice python led_renderer.py 2>&1 > /tmp/renderer.log &
nohup sudo python singlesensor.py 2>&1 > /tmp/sensor.log &
