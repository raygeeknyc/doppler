#!/bin/bash
<<<<<<< HEAD
logger "$0"
echo "`date` $0"
sudo rmmod gspca_kinect
sudo rmmod gspca_main
sudo modprobe gspca_main
sudo modprobe gspca_kinect
sudo python set_tilt.py
sudo rmmod gspca_kinect
sudo rmmod gspca_main
sudo modprobe gspca_main
sudo modprobe gspca_kinect
echo "starting sensor"
sudo python multisensor.py
=======
if [[ "$1" == "debug" ]]; then
  echo "debugging"
  python singlesensor.py
else
  python singlesensor.py >/dev/null 2>&1
fi
>>>>>>> ef7f26851762e3ae41f544a6d425b06fb20b2fdc
