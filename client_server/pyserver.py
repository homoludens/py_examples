#!/usr/bin/python
# Echo server program
import socket
import shlex, subprocess
import daemon

HOST = 'localhost'                 # Symbolic name meaning the local host
PORT = 50004              # Arbitrary non-privileged port

def main():
  while 1:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind((HOST, PORT))
    s.listen(1)
    conn, addr = s.accept()
    print 'Connected by', addr
    while 1:
	data = conn.recv(1024)
	if not data: break
	print "data: "+data
	proc = subprocess.Popen(data, shell=True, stdout=subprocess.PIPE,)
	proc.wait()
	stdout_value = proc.communicate()[0]
	conn.send(stdout_value)
    conn.close()

if __name__ == "__main__":
  #with daemon.DaemonContext():
    main()