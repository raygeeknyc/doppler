#!/bin/sh
sudo rmmod gspca_kinect
sudo modprobe gspca_kinect
sudo python set_tilt.py -22
if [[ "${1}" -eq "single" ]];then
  sudo python singlesensor.py
else
  sudo python multisensor.py
fi
