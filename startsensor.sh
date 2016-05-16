#!/bin/bash
sudo rmmod gspca_kinect
sudo modprobe gspca_kinect
sudo python set_tilt.py
sudo python multisensor.py
