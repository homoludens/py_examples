import urllib2,sys
html = urllib2.urlopen('http://reddit.com').read()
from BeautifulSoup import BeautifulSoup
soup = BeautifulSoup(html)
votes = soup.findAll("div","score unvoted")
for vote in votes:
    print vote.string

#soup.findAll("div","score unvoted")[0].string

