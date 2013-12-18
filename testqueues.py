import time
import Queue

q = Queue.Queue()
l = []
start = time.time()
for x in range(1,100000):
	l.append(x)
print "list took %f" % (time.time()-start)
start = time.time()
for x in range(1,100000):
	q.put(x)
print "queue took %f" % (time.time()-start)
