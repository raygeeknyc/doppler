import time
import collections

start = time.time()
for x in range(1,1000):
	l = []
	for y in range(1,05):
		l.append(x)
print "lists took %f" % (time.time()-start)
start = time.time()
for x in range(1,1000):
	l = collections.deque()
	for y in range(1,05):
		l.append(x)
print "deques took %f" % (time.time()-start)
start = time.time()
l = collections.deque()
for x in range(1,1000):
	for y in range(1,05):
		l.append(x)
	l.clear()
print "deque took %f" % (time.time()-start)
