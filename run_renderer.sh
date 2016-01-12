#!/bin/bash
if [[ -z "${DISPLAY}" ]];then
  export DISPLAY=":0.0"
fi
/usr/bin/xset -dpms
killall -9 python
while true;do
	python renderer.py
done
