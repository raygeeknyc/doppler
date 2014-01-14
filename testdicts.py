import time

l = []
for x in range(300):
        r = []
        for y in range(100):
                r.append(x+y)
        l.append(r)

d = {}
for x in range(300):
        r = {}
        for y in range(100):
                r[y] = (x+y)
        d[x] = r

print "list[%d][%d]" % (len(l), len(l[0]))
for iter in range(5):  
        start = time.time()
        for x in range(300):
                for y in range(100):
                        a = l[x][y]
        print "list took %f" % (time.time() - start)

        start = time.time()
        for x in range(300):
                for y in range(100):
                        a = d[x][y]
        print "dict took %f" % (time.time() - start)
