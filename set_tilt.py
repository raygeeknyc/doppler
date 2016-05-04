#!/usr/bin/env python
import freenect
import time
import sys
 
ctx = freenect.init()
print "Number of kinects: %d\n" % freenect.num_devices(ctx)
dev = []
for devIdx in range(0, freenect.num_devices(ctx)):
    print "opening device %d" % devIdx
    dev.append(freenect.open_device(ctx, devIdx))
    if not dev:
        freenect.error_open_device()
 
if len(sys.argv) == 2:
	tilt = int(sys.argv[1])
	print "Setting tilt to %d" % tilt
	for sensor in dev:
	    print "Setting TILT: ", tilt
	    freenect.set_tilt_degs(sensor, tilt)
else:
	print "Setting custom tilts"
	print "[0] --> -20"
	freenect.set_tilt_degs(dev[0], -20)
	print "[1] --> -20"
	freenect.set_tilt_degs(dev[1], -20)
	print "[2] --> -30"
	freenect.set_tilt_degs(dev[2], -30)
