#!/bin/bash
if [[ "$1" == "debug" ]]; then
  echo "debugging"
  python singlesensor.py
else
  python singlesensor.py >/dev/null 2>&1
fi
