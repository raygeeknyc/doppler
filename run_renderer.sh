#!/bin/bash
export DISPLAY=":0.0"
killall -9 python
while true;do
	python renderer.py
done
