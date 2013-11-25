#!/bin/bash
SUBNET="192.168.1"
for node in 101 102 103 104 105 106 107 108
do
	echo ${SUBNET}.${node}
	ssh root@${SUBNET}.${node} "cd doppler;export DISPLAY=':0.0';killall -9 python;nohup python renderer.py &"
done
