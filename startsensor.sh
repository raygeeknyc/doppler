#!/bin/bash
logger "$0"
echo "`date` $0"
sudo python set_tilt.py
echo "starting sensor"
if [[ "$1" == "debug" ]]; then
  echo "debugging"
  python multisensor.py
else
  python multisensor.py >/dev/null 2>&1
fi
