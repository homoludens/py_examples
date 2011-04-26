import urllib2,sys
from BeautifulSoup import BeautifulSoup

file = open('osm_fr_links', 'r')
friend_list = file.read()
soup = BeautifulSoup(friend_list)
friend_urls = soup.findAll("a")

out = []

for friend_url in friend_urls:
  html = urllib2.urlopen(friend_url['href']+'/edits').read()
  soup = BeautifulSoup(html)
  #print soup
  try:
    e = soup.findAll("table")[0].findAll("a")  
  except:
    e = []
  print e
  edits = len(e)
  out.append((friend_url['href'], edits))
  print (friend_url['href'], edits)
  
print out