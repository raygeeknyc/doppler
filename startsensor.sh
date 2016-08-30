#!/bin/bash
# run as root
sudo rmmod gspca_kinect
sudo rmmod gspca_main
sudo modprobe gspca_main
sudo modprobe gspca_kinect
if [[ "$1" == "debug" ]]; then
  echo "debugging"
  python singlesensor.py
else
  python singlesensor.py >/dev/null 2>&1
fi
