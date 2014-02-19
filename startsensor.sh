#!/bin/sh
sudo rmmod gspca_kinect
sudo modprobe gspca_kinect
python set_tilt.py -28
python sensor.py
