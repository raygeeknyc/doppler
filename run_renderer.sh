#!/bin/bash
if [[ -z "${DISPLAY}" ]];then
  export DISPLAY=":0.0"
fi
/usr/bin/xset -dpms
# This kill should only be run on standalone, dedicated renderer nodes
# killall -9 python
#while true;do
python renderer.py debug
#done
