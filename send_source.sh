#!/bin/bash
SUBNET="192.168.1"
for node in 101 102 103 104 105 106 107 108
do
	echo ${SUBNET}.${node}
	scp *.py root@${SUBNET}.${node}:doppler/
done
