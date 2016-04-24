#!/bin/bash
SUBNET="192.168.1"
for node in 101 105 102 106 103 107 104 108
do
	echo ${SUBNET}.${node}
	ssh root@${SUBNET}.${node} "cd doppler;killall -9 run_renderer.sh;killall -9 python;./run_renderer.sh &"
done
