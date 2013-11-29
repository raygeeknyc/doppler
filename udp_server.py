import socket
CLIENT_UDP_IPS = ["127.0.0.1", "192.168.0.100"]
CLIENT_UDP_PORTS = [5005,5006]
MESSAGE = "Hello, client at %d"

print "UDP target IP addresses:", CLIENT_UDP_IPS
print "UDP target ports:", CLIENT_UDP_PORTS
print "message:", MESSAGE

sock = socket.socket(socket.AF_INET, # Internet
socket.SOCK_DGRAM) # UDP
for host in CLIENT_UDP_IPS:
	for client in CLIENT_UDP_PORTS:
		sock.sendto(MESSAGE % client, (host, client))
