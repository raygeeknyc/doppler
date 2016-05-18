#!/bin/bash
logger "$0"
sudo rmmod gspca_kinect
sudo modprobe gspca_kinect
sudo python set_tilt.py
sudo nohup python multisensor.py
