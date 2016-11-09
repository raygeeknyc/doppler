#!/bin/bash
logger "$0"
echo "`date` $0"
echo "starting sensor"
if [[ "$1" == "debug" ]]; then
  echo "debugging"
  sudo python multisensor.py
else
  sudo python multisensor.py >/dev/null 2>&1
fi
