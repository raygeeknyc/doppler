#!/bin/bash
# run as root
rmmod gspca_kinect
rmmod gspca_main
modprobe gspca_main
modprobe gspca_kinect
if [[ "$1" == "debug" ]]; then
  echo "debugging"
  python singlesensor.py
else
  python singlesensor.py >/dev/null 2>&1
fi
