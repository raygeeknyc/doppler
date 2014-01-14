#!/bin/bash
export DISPLAY=":0.0"
/usr/bin/xset -dpms
killall -9 python
while true;do
	python renderer.py
done
