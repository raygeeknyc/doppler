#!/bin/bash
logger "$0"
SUBNET="192.168.0"
for node in 107
do
	echo ${SUBNET}.${node}
	ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ubuntu@${SUBNET}.${node} "cd doppler;killall -9 run_renderer.sh;killall -9 python;nohup ./run_renderer.sh"  < /dev/null &
done
