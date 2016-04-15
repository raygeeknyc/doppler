#!/bin/sh
sudo rmmod gspca_kinect
sudo modprobe gspca_kinect
sudo python set_tilt.py -22
#sudo python multisensor.py
sudo python singlesensor.py
