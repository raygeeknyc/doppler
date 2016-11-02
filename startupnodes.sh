#!/bin/bash
logger "$0"
SUBNET="192.168.0"
for node in 101 102 103 104 105 106 107 108
do
	echo ${SUBNET}.${node}
	ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ubuntu@${SUBNET}.${node} "cd doppler;killall -9 run_renderer.sh;killall -9 python;nohup ./run_renderer.sh"  < /dev/null > ./node_${node}.out 2>&1  &
done
