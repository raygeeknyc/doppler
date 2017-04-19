#!/bin/bash
SUBNET="192.168.0"
for node in 101 102 103 104 105 106 107 108
do
	echo ${SUBNET}.${node}
	scp *.{py,sh} ubuntu@${SUBNET}.${node}:doppler/ &
done
jobs
