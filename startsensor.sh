#!/bin/bash
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
sudo python multisensor.py
