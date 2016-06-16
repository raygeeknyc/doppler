#!/bin/bash
sudo rmmod gspca_kinect
sudo rmmod gspca_main
sudo modprobe gspca_main
sudo modprobe gspca_kinect
sudo python singlesensor.py
