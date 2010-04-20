# Echo client program
import socket
import sys

HOST = 'localhost'    # The remote host
PORT = 50004             # The same port as used by the server
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((HOST, PORT))
data =""
#for arg in sys.argv[1:]:
    #print arg
    #data = data + arg + " "

while True:
  data = sys.stdin.readline()
  if not data:break 
  s.send(data)
  data = ""
  stdout_value = s.recv(1024)
  print stdout_value
#s.send(data)

s.close()
print 'Received', repr(data)

