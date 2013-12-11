#!/usr/bin/env python
# arg = kinect device index, from 0
# arg = threshold above which we consider a sensor spots depth to be changed
import copy
import freenect
import numpy as np
import sys

if len(sys.argv) != 3:
	print >> sys.stderr, "usage %s kinect-device-index threshold" % sys.argv[0]
	sys.exit(255)

CELL_SCALING_FACTOR = 10
threshold = sys.argv[2]
old_depth, timestamp = freenect.sync_get_depth(sys.argv[1]])
height = len(old_depth)
width = len(old_depth[0])
print 'Kinect device %d, Depth map %d X %d\n' % (sys.argv[1], height, width)
cell_map = [[0]*(width/CELL_SCALING_FACTOR)]*(height/CELL_SCALING_FACTOR)
print 'Cell map %d X %d\n' % (len(cell_map), len(cell_map[0]))
min_depth = None
max_depth = None
while 1:
    depth, timestamp = freenect.sync_get_depth(sys.argv[1])
    min_depth = min(depth)
    max_depth = max(depth)
    delta = []
    shifts = 0
    for row in range(0, len(depth)):
      delta.append([])
      for col in range(0, len(depth[row])):
        delta[row].append(int(old_depth[row][col]) - int(depth[row][col]))
        if abs(delta[row][col]) >= threshold:
	  cell_map[int(row/CELL_SCALING_FACTOR)][int(col/CELL_SCALING_FACTOR)] += 1
          shifts += 1
    print "%d shifts >= %d" % (shifts, threshold)
    print "min:max depth %d : %d"\n" % (min_depth, max_depth)
    print "\nMap of %d X %d pixel aggregate shifts\n\n"
    for cell_row in range(0, len(cell_map):
      for cell_col in range(0, len(cell_map[0])):
        if cell_map[cell_row][cell_col] == 0:
          print ' '
        elif cell_map[cell_row][cell_col] > 9:
          print '+'
        else
          print cell_map[cell_row][cell_col]
      print '\n'
    old_depth = copy.deepcopy(depth)
