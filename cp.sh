#!/bin/bash
SUBNET="192.168.0"
for node in 108 107 106 105 104 103 102 101
do
	echo ${SUBNET}.${node}
	ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no ubuntu@${SUBNET}.${node} "rm -fR doppler;mkdir doppler" < /dev/null
done
