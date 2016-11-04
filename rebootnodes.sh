#!/bin/bash
logger "$0"
SUBNET="192.168.0"
for node in 101 102 103 104 105 106 107 108
do
	echo ${SUBNET}.${node}
	ssh -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no root@${SUBNET}.${node} "reboot" < /dev/null &
done
