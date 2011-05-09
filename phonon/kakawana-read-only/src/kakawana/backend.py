# -*- coding: utf-8 -*-

"""A simple backend for kakawana, using Elixir"""
VERSION="0.0.1"

import os
import re
import time
from elixir import *
import kakawana.feedparser as feedparser
import pickle, base64
import datetime, time
# Import Qt modules
from PyQt4 import QtCore, QtGui, QtWebKit
import icons_rc
import tenjin
escape = tenjin.helpers.escape

feedparser.USER_AGENT = 'Kakawana/%s +http://kakawana.googlecode.com/'%VERSION

if 'KW_DBDIR' in os.environ:
    dbdir=os.environ['KW_DBDIR']
else:
    dbdir=os.path.join(os.path.expanduser("~"),".kakawana")
dbfile=os.path.join(dbdir,"kakawana.sqlite")

from htmlentitydefs import name2codepoint as n2cp
def h2t(value):
    "Return the given HTML with all tags stripped."
    return decode_htmlentities(re.sub(r'<[^>]*?>', '', value))

def substitute_entity(match):
  ent = match.group(2)
  if match.group(1) == "#":
    return unichr(int(ent))
  else:
    cp = n2cp.get(ent)
    if cp:
      return unichr(cp)
    else:
      return match.group()

def decode_htmlentities(string):
  entity_re = re.compile("&(#?)(\d{1,5}|\w{1,8});")
  return entity_re.subn(substitute_entity, string)[0]

# It's good policy to have your app use a hidden folder in 
# the user's home to store its files. That way, you can 
# always find them, and the user knows where everything is.


# Sanitize parsed feeds so they can be pickled, see
# http://bugs.python.org/issue1757062

import BeautifulSoup

def sanitize(d):
    if isinstance(d, BeautifulSoup.NavigableString):
        return unicode(d)
    elif isinstance (d, list):
        return [sanitize(i) for i in d]
    elif hasattr(d,'keys'):
        for k in d.keys():
            d[k]=sanitize(d[k])
    return d
            

class Feed(Entity):
    """
    A comic book feed
    """
    
    # By inheriting Entity, we are using Elixir to make this 
    # class persistent, Feed objects can easily be stored in
    # our database, and you can search for them, change them, 
    # delete them, etc.        
    
    using_options(tablename='feeds')
    # This specifies the table name we will use in the database, 
    # I think it's nicer than the automatic names Elixir uses.
    name = Field(Unicode,required=True)
    '''The name of the feed'''
    url = Field(Unicode,required=False)
    '''The URL of the comic's website'''
    xmlurl = Field(Unicode,required=True, primary_key=True)
    '''The URL for the RSS/Atom feed'''
    data = Field(Unicode,required=False)
    '''everything in the feed'''
    posts = OneToMany("Post", order_by = "-date")
    '''Posts in the feed'''
    etag = Field(Text, default='')
    '''etag of last check'''
    check_date = Field(DateTime, required=False, default=datetime.datetime(1970,1,1))
    '''timestamp of last check'''
    last_status = Field(Integer, required=False, default=0)
    '''last status of the feed'''
    last_good_check = Field(DateTime, required=False, default=datetime.datetime(1970,1,1))
    '''last good check (status 2xx or 3xx)'''
    bad_check_count = Field(Integer, default=0)
    '''How many bad checks in a row'''
    mode = Field(Integer, default=1)
    '''Mode to use to display the feed'''
    oldest_fresh = Field(DateTime, required=False, default=datetime.datetime(1970,1,1))
    '''Date of the oldest fresh item. You can't expire newer than this because
    they just get re-fetched'''
    
    def __repr__(self):
        return "Feed: %s <%s>"%(self.name, self.url)


    def expire(self):
        '''Removes all posts in the feed that:

        * Are not starred
        * Are not newer than self.oldest_fresh
        * Are older than 2 weeks

        And keeps at least 20 posts, if they are available.
        '''
        postList = Post.query.filter(Post.date < self.oldest_fresh).\
            filter_by(feed = self, star = False).order_by(Post.date).all()
        if len(postList) > 20:
            for p in postList[20:]:
                p.delete()
        saveData()

    @classmethod
    def createFromFPData(cls, url, feed):
        '''
        Create a feed in the DB from feedparser data.

        feed is fedparser.parse(url)
        '''
        from pprint import pprint
        
        link = url
        if 'link' in feed['feed']:
            link = feed['feed']['link']
        elif 'links' in feed['feed'] and feed['feed']['links']:
            link = feed['feed']['links'][0].href

        title = u'No Title'
        if 'title' in feed['feed']:
            title = feed['feed']['title']

        # Add it to the DB
        f = Feed.update_or_create(dict (
            name = unicode(title),
            url = unicode(link),
            xmlurl = unicode(url),
            data = unicode(base64.b64encode(pickle.dumps(sanitize(feed['feed']))))),
            surrogate = False)
        saveData()
        return f


    def addPosts(self, feed=None):
        '''Takes an optional already parsed feed'''
        self.check_date = datetime.datetime.now()
        saveData()
        if feed == None:
            feed=feedparser.parse(self.xmlurl,
                etag = self.etag,
                modified = self.check_date.timetuple())
        elif feed == {}:
            # This was probably a feedparser bug that made the
            # fetcher crash, so don't try to do much, but
            # mark as updated anyway
            saveData()
            return

        # Fill in missing things
        if not self.url:
            if 'link' in feed['feed']:
                self.url = feed['feed']['link']
            elif 'links' in feed['feed'] and feed['feed']['links']:
                self.url = feed['feed']['links'][0].href
        # Keep data fresh
        self.data = unicode(base64.b64encode(pickle.dumps(sanitize(feed['feed']))))

        if 'status' in feed:

            self.last_status = feed.status
            if str(feed.status)[0]=='4':
                # Error
                self.bad_check_count+=1
            else: #good check
                self.last_good_check=datetime.datetime.now()
            
            if feed.status == 304: # No change
                print "Got 304 on feed update"
                saveData()
                return
            elif feed.status == 301: # Permanent redirect
                print "Got 301 on feed update => %s"%feed.href
                self.xmlUrl=feed.href
            elif feed.status == 410: # Feed deleted. FIXME: tell the user and stop trying!
                print "Got 410 on feed update"
                saveData()
                return
            elif feed.status == 404: # Feed gone. FIXME: tell the user and stop trying!
                print "Got 404 on feed update"
                saveData()
                return
        if 'etag' in feed:
            self.etag = feed['etag']

        self.oldest_fresh=datetime.datetime.now()
        for post in feed['entries']:
            p=Post.get_or_create(post)
            self.posts.append(p)
            if p.date < self.oldest_fresh:
                self.oldest_fresh = p.date
        saveData()

class Post(Entity):
    '''Everything in the feed'''
    
    using_options(tablename='posts')
    title = Field(Unicode, required=True)
    url = Field(Unicode, required=True)
    read = Field(Boolean, default=False)
    star = Field(Boolean, default=False)
    data=Field(Unicode,required=True)
    _id=Field(Unicode,required=True, primary_key=True)
    feed=ManyToOne("Feed")
    date=Field(DateTime, required=True)
    content = Field(Unicode, required=False)

    @classmethod
    def get_or_create(cls, post):
        """Takes a entry as generated by feedparser and returns
        an existing or a new Post object"""
        #from pudb import set_trace; set_trace()

        post_date = time.localtime()
        try:
            post_date = post.published_parsed
        except AttributeError:
            try:
                post_date = post.updated_parsed
            except AttributeError:
                pass
        if not post_date: # Sometimes it comes back None
            post_date = time.localtime()
        data = base64.b64encode(pickle.dumps({}))
        try:
            data = base64.b64encode(pickle.dumps(sanitize(post)))
        except:
            print 'Error pickling post data', post.id

        if 'id' in post:
            _id = post.id
        else:
            _id = post.link

        post_date = datetime.datetime(*post_date[:6])
        p=Post.update_or_create( dict(
            title = post.title,
            url = post.link,
            _id = _id,
            date = post_date,
            content = Post.getContent(post),
            data = data),
            surrogate = False,
            )
        return p

    def createItem(self, fitem):
        text = h2t(self.title) or unicode(self.date)
        pitem=QtGui.QTreeWidgetItem(fitem,['',text,unicode(self.date)])
        pitem.setToolTip(0,text)
        pitem.setToolTip(1,text)
        if self.read:
            pitem.setForeground(1, QtGui.QBrush(QtGui.QColor("lightgray")))
        else:
            pitem.setForeground(1, QtGui.QBrush(QtGui.QColor("black")))
        if self.star:
            pitem.setIcon(0,QtGui.QIcon(':/icons/star.svg'))
        else:
            pitem.setIcon(0,QtGui.QIcon(':/icons/star2.svg'))
        pitem._id=self._id
        return pitem

    @classmethod
    def getContent(cls, data):
        '''find the post contents in a feeedparser entry'''
        content = ''
        if 'content' in data:
            content = '<hr>'.join([c.value for c in data['content']])
        elif 'summary' in data:
            content = data['summary']
        elif 'value' in data:
            content = data['value']
        else:
            print "Can't find content in this entry"
            print data

        # Rudimentary NON-html detection
        if not '<' in content:
            content=escape(content).replace('\n\n', '<p>')
        return content
        
    def __repr__(self):
        return "Post: %s"%self.title

class KeyValue(Entity):
    """Useful for storing random stuff on a key/value store like
    if it were a dictionary"""
    key = Field(Unicode,required=True, primary_key=True)
    value = Field(Unicode,required=True)
    timestamp = Field(DateTime, required = True)

class Tag(Entity):
    """
    A tag we can apply to a feed or post.
    """
    # Again, they go in the database, so they are an Entity.
    
    using_options(tablename='tags')
    name = Field(Unicode,required=True)
    feeds = ManyToMany("Feed")
    posts = ManyToMany("Post")
    
    def __repr__(self):
        return "Tag: "+self.name

# Using a database involves a few chores. I put them 
# in the initDB function. Just remember to call it before 
# trying to use Tags, Posts, etc.!

def initDB():
    # Make sure ~/.kakawana exists
    if not os.path.isdir(dbdir):
        os.mkdir(dbdir)
    # Set up the Elixir internal thingamajigs
    metadata.bind = "sqlite:///%s"%dbfile
    setup_all()
    # And if the database doesn't exist: create it.
    if not os.path.exists(dbfile):
        create_all()
        
    # This is so Elixir 0.5.x and 0.6.x work
    # Yes, it's kinda ugly, but needed for Debian 
    # and Ubuntu and other distros.
    
    global saveData
    import elixir
    if elixir.__version__ < "0.6":
        saveData=session.flush
    else:
        saveData=session.commit
        
