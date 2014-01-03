import time

start = time.time()
for x in range(1000):
	for y in range(1000):
		s = "S"+","+str(x)+","+str(y)
print "concats took %f" % (time.time() - start)

start = time.time()
for x in range(1000):
	for y in range(1000):
		s = "S,%d,%d" % (x,y)
print "formats took %f" % (time.time() - start)
