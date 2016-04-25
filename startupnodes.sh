#!/bin/bash
SUBNET="192.168.0"
for node in 108 107 106 105 104 103 102 101
do
	echo ${SUBNET}.${node}
	ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@${SUBNET}.${node} "cd doppler;killall -9 run_renderer.sh;killall -9 python;nohup ./run_renderer.sh &"
done
