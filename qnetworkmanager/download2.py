import urllib, sys


def dlProgress(count, blockSize, totalSize):
	percent = int(count*blockSize*100/totalSize)
	sys.stdout.write("%2d%%" % percent)
	sys.stdout.write("\b\b\b")
	sys.stdout.flush()

rem_file = sys.argv[1]
loc_file = sys.argv[2]
sys.stdout.write(rem_file + "...") 
u = urllib.urlretrieve(rem_file, reporthook = dlProgress)
#print u
#print u[0]
urllib.urlretrieve(rem_file, loc_file, reporthook=dlProgress)

