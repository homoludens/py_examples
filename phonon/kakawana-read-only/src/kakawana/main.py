# -*- coding: utf-8 -*-

"""The user interface for our app"""

import os, sys, hashlib, re, cgi
from pprint import pprint

# Import Qt modules
from PyQt4 import QtCore, QtGui, QtWebKit, uic

# Import our backend
import backend

import kakawana.feedfinder as feedfinder
import kakawana.feedparser as feedparser
import pickle
import datetime
import time
import base64
import codecs
import keyring
from multiprocessing import Process, Queue
from audioplayer import AudioPlayer
from videoplayer import VideoPlayer
import libgreader as gr
from reader_client import GoogleReaderClient
import json


VERSION="0.0.1"

# Templating stuff
import tenjin
# The obvious import doesn't work for complicated reasons ;-)
to_str=tenjin.helpers.to_str
escape=tenjin.helpers.escape
templateEngine=tenjin.Engine()
tmplDir=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'templates')
# To convert UTC times (returned by feedparser) to local times
def utc2local(dt):
  return dt-datetime.timedelta(seconds=time.timezone)
def renderTemplate(tname, **context):
  context['to_str']=to_str
  context['escape']=escape
  context['utc2local']=utc2local
  codecs.open('x.html', 'w', 'utf-8').write(templateEngine.render(os.path.join(tmplDir,tname), context))
  return templateEngine.render(os.path.join(tmplDir,tname), context)
# End oftemplating stuff

fetcher_in = Queue()
fetcher_out = Queue()

# Background feed fetcher
def fetcher():
    while True:
        print 'Fetching'
        try:
            commands = []
            while True:
                cmd = fetcher_in.get(5)
                if cmd not in commands:
                    commands.insert(0,cmd)
                if fetcher_in.empty():
                   break
            while len(commands):
                cmd = commands.pop()
                if cmd[0] == 'update':
                    print 'Updating:', cmd[1],'...',
                    f=feedparser.parse(cmd[1],
                        etag = cmd[2],
                        modified = cmd[3].timetuple())
                    if 'bozo_exception' in f:
                        f['bozo_exception'] = None
                    fetcher_out.put(['updated',cmd[1],backend.sanitize(f)])
                    print 'Done'
                elif cmd[0] == 'add':
                    print 'Adding:', cmd[1],'...'
                    f=feedparser.parse(cmd[1])
                    if 'bozo_exception' in f:
                        f['bozo_exception'] = None
                    fetcher_out.put(['added',cmd[1],backend.sanitize(f)])
                    print 'Done'
                
        except Exception as e:
            print 'exception in fetcher:', e
            fetcher_out.put(['updated',cmd[1],{}])

class TrayIcon(QtGui.QSystemTrayIcon):
    "Notification area icon"

    def __init__(self, main):
        QtGui.QSystemTrayIcon.__init__ (self,
            QtGui.QIcon(":/icons/urssus.svg"))
        self.main = main

# Create a class for our main window
class Main(QtGui.QMainWindow):
    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        # Load settings
        self.settings=QtCore.QSettings("ralsina", "Kakawana")
        self.restoreGeometry(self.settings.value("geometry").toByteArray())
        self.restoreState(self.settings.value("state").toByteArray())

        self.mode = 0
        self.showAllFeeds = False
        self.showAllPosts = False
        self.keepGoogleSynced = True
        
        self.enclosures = []
        self.feed_properties = None
        # This is always the same
        uifile = os.path.join(
            os.path.abspath(
                os.path.dirname(__file__)),'main.ui')
        uic.loadUi(uifile, self)
        self.ui = self
        #QtWebKit.QWebSettings.globalSettings().\
            #setAttribute(QtWebKit.QWebSettings.PluginsEnabled, True)

        # Tray Icon
        self.tray=TrayIcon(self)
        self.tray.show()
        self.tray.activated.connect(self.trayActivated)

        # Fix column widths in feed list
        header=self.ui.feeds.header()
        header.setResizeMode(0, QtGui.QHeaderView.Fixed)
        header.resizeSection(0, 24)
        self.feeds.setSortingEnabled(True)
        self.feeds.sortItems(2, QtCore.Qt.DescendingOrder)
        header.hideSection(2)

        self.enclosureLayout = QtGui.QVBoxLayout(self.enclosureContainer)
        self.enclosureContainer.setLayout(self.enclosureLayout)
        self.enclosureContainer.hide()

        # Smart 'Space' that jumps to next post if needed
        self.addAction(self.ui.actionSpace)
        self.addAction(self.ui.actionNext)
        self.addAction(self.ui.actionPrevious)
        self.addAction(self.ui.actionStar)
        self.addAction(self.ui.actionFind)
        self.ui.searchWidget.hide()
        self.ui.actionFind.triggered.connect(self.ui.searchWidget.show)

        # Zoom actions
        self.ui.actionLarger.triggered.connect(lambda: self.ui.html.setZoomFactor(self.ui.html.zoomFactor()+.2))
        self.ui.actionSmaller.triggered.connect(lambda: self.ui.html.setZoomFactor(self.ui.html.zoomFactor()-.2))
        self.ui.actionNormal.triggered.connect(lambda: self.ui.html.setZoomFactor(1))

        self.ui.html.page().setLinkDelegationPolicy(QtWebKit.QWebPage.DelegateExternalLinks)
        self.ui.html.page().linkClicked.connect(self.linkClicked)
        self.ui.html.page().linkHovered.connect(self.showTempStatus)
        self.progressBar=QtGui.QProgressBar()
        self.progressBar.setMaximum(100)
        self.progressBar.setMaximumWidth(150)
        self.statusbar.addPermanentWidget(self.progressBar, False)
        self.ui.html.page().loadProgress.connect(self.progressBar.setValue)
        self.ui.html.page().loadStarted.connect(self.progressBar.show)
        self.ui.html.page().loadFinished.connect(self.progressBar.hide)


        # Show about kakawana on startup
        self.on_actionAbout_Kakawana_activated()

        self.loadFeeds(-1)

        self.showStatusBar = True
        self.ui.actionShow_Status_Bar.setChecked(self.showStatusBar)

        self.fetcher = Process(target=fetcher)
        self.fetcher.daemon = True
        self.fetcher.start()

        self.update_timer = QtCore.QTimer()
        self.update_timer.timeout.connect(self.get_updates)
        self.update_timer.start(2000)

        self.scheduled_updates = QtCore.QTimer()
        self.scheduled_updates.timeout.connect(self.updateOneFeed)
        self.scheduled_updates.start(30000)

        self.googleList=[]

    def showTempStatus(self, msg, *args):
        self.statusbar.showMessage(msg, 5000)

    def on_actionShow_Status_Bar_toggled(self, checked):
        '''Show/Hide status bar'''
        self.ui.statusbar.setVisible(checked)
	self.showStatusBar = checked

    def on_actionSync_Read_Items_activated(self, b=None):
        '''Fetches the readingList from google and marks all known
        articles as read. Saves that list as self.googleList'''

        if b is not None: return
        progress = QtGui.QProgressDialog(self)
        progress.setLabelText(self.tr('Connecting to Google Reader'))
        progress.show()
        progress.setAutoClose(True)
        QtCore.QCoreApplication.processEvents()
        
        reader = self.getGoogleReader()
        userJson = reader.httpGet(reader.READING_LIST_URL, {'n':5000})
        allPosts = json.loads(userJson, strict=False)['items']
        userInfo = reader.getUserInfo()
        readtag = u'user/%s/state/com.google/read'%userInfo['userId']
        changedFeeds = set()
        progress.setLabelText(self.tr('Syncing'))
        progress.setMaximum(len(allPosts))
        for i,p in enumerate(allPosts):
            progress.setValue(i)
            if i%10 == 0:
                QtCore.QCoreApplication.processEvents()
            if progress.wasCanceled():
                break
            if readtag in p['categories']:
                # It's read
                p2 = backend.Post.get_by(url=p['alternate'][0]['href'])
                f1 = backend.Feed.get_by(xmlurl=p['origin']['streamId'][5:])
                if p2 and f1 and p2.feed == f1 and p2.read==False:
                    p2.read = True
                    print 'Marking post: ', p2._id
                    if f1 not in changedFeeds:
                        changedFeeds.add(f1)
                elif not p2:
                    print "Can't find post:", p['alternate']
        self.googleList = allPosts
        backend.saveData()
        progress.close()
        # Update all changed feeds in the UI
        # FIXME: this can be made smarter
        self.refreshFeeds()

    def trayActivated(self, reason):
        if reason == None: return
        if reason == self.tray.Trigger:
            if self.isVisible():
                self.hide()
            else:
                self.show()
                self.raise_()

    def on_actionMark_All_As_Read_triggered(self, b=None):
        '''Mark all visible posts in the current feed as read'''
        if b is not None: return
        print 'Marking feed as Read'
        item = self.ui.feeds.currentItem()
        fitem = item.parent()
        if not fitem:
            fitem = item
        if fitem._id in (-1,-2):
            return
        for i in range(fitem.childCount()):
            _id=fitem.child(i)._id
            if _id:
                post = backend.Post.get_by(_id=_id)
                post.read = True
        if not self.showAllPosts:
            fitem.takeChildren()
        backend.saveData()
        self.on_feeds_itemClicked(item=fitem, column=1)

    def linkClicked(self,url):
        if unicode(url.scheme()) == 'cmd':
            # These are fake URLs that trigger kakawana's actions
            cmd = unicode(url.host()).lower()
            print 'COMMAND:', cmd # This is the action name

            # Feed commands
            if cmd == 'mark-all-read':
                print 'Triggering mark-all-read'
                self.ui.on_actionMark_All_As_Read_triggered()
                
            elif cmd == 'refresh':
                self.updateCurrentFeed()

            elif cmd == 'unsubscribe':
                self.on_actionDelete_Feed_activated()
                
            # Post commands
            elif cmd == 'keep-unread':
                self.actionKeep_Unread.trigger()

            elif cmd == 'star':
                self.actionStar.setChecked(True)
            elif cmd == 'unstar':
                self.actionStar.setChecked(False)
                
        else:
            QtGui.QDesktopServices.openUrl(url)

    def updateStarredFeed(self):
        '''Updates the 'starred posts' feed'''
        fitem = self.findFeedItem(-2)
        fitem.takeChildren()
        posts =  backend.Post.query.filter(backend.Post.star==True)
        for post in posts:
            pitem = post.createItem(fitem)

    def updateRecentFeed(self):
        '''Updates the 'recent posts' feed'''
        fitem = self.findFeedItem(-1)
        fitem.takeChildren()
        posts =  backend.Post.query.filter(backend.Post.read==False).\
            order_by("date desc").limit(10).all()
        for post in posts:
            pitem = post.createItem(fitem)

    def updateCurrentFeed(self):
        '''Launches a forced update for the current feed.

        If it's a real feed, the update is queued.
        If it's a meta feed, the update is immediate.

        '''
        item = self.ui.feeds.currentItem()
        fitem = item.parent()
        if not fitem:
            fitem = item
        if fitem._id == -1: # Recent posts, do it now
            self.updateRecentFeed()
            
        elif fitem._id == -2: # Starred
            self.updateStarredFeed()
            
        else: # Plain feed, do it non-blocking
            feed = backend.Feed.get_by(xmlurl = fitem._id)
            if feed:
                print  "Manual update of: ",feed.xmlurl
                fetcher_in.put(['update', feed.xmlurl, feed.etag, feed.check_date])

    def updateOneFeed(self):
        """Launches an update for the feed that needs it most"""
        feeds = backend.Feed.query.order_by("check_date").limit(1).all()
        if feeds:
            feed = feeds[0]
            print feed.check_date
            # Only check if it has not been checked in at least 10 minutes
            if (datetime.datetime.now() - feed.check_date).seconds > 600:
                print  "Scheduled update of: ",feed.xmlurl
                fetcher_in.put(['update', feed.xmlurl, feed.etag, feed.check_date])
        
    def get_updates(self):
        try:
            cmd = fetcher_out.get(False) # Don't block
        except:
            return
        if cmd[0] == 'updated':
            xmlurl = cmd[1]
            feed = backend.Feed.get_by(xmlurl = xmlurl)
            if feed:
                feed.addPosts(cmd[2])
                self.updateFeed(xmlurl)
        elif cmd[0] == 'added':
            print 'Adding feed to DB'
            xmlurl = cmd[1]
            feed_data = cmd[2]
            f = backend.Feed.createFromFPData(xmlurl, feed_data)
            if self.keepGoogleSynced:
                # Add this feed to google reader
                # FIXME: what if the feed is already subscribed in google?
                
                reader = self.getGoogleReader2()
                if reader:
                    print 'Adding to google:', f.xmlurl, f.name
                    reader.subscribe_feed(f.xmlurl, f.name)
            f.addPosts(feed_data)
            self.updateFeed(f.xmlurl)

    def findPostItem(self, post):
        '''Given a post, returns the item where this post is displayed.
        This is the item at feed->post not one in recent or other places.
        Those are generated dynamically when the pseudofeed opens.
        '''
        fitem = self.findFeedItem(post.feed.xmlurl)
        for i in range(fitem.childCount()):
            if fitem.child(i)._id == post._id:
                return fitem.child(i)
        return None

    def findFeedItem(self, feed_id):
        for i in range(self.ui.feeds.topLevelItemCount()):
            fitem = self.ui.feeds.topLevelItem(i)
            if fitem._id == feed_id:
                return fitem
        return None

    def updateFeed(self, feed_id):
        # feed_id is a Feed.xmlurl, which is also item._id
        fitem = self.findFeedItem(feed_id)
        if fitem:
            feed = backend.Feed.get_by(xmlurl = feed_id)
            if fitem == self.feeds.currentItem():
                # It's the current item, needs to have its children displayed
                self.showFeedPosts(fitem, feed)

            else:
                # It's not the current item, just show the item count
                
                # This is the one to update
                unread_count = min(100,len(filter(lambda p: not p.read, feed.posts)))
                fitem.setText(1,backend.h2t('%s (%d)'%(feed.name,unread_count)))
                if unread_count:
                    fitem.setBackground(0, QtGui.QBrush(QtGui.QColor("lightgreen")))
                    fitem.setBackground(1, QtGui.QBrush(QtGui.QColor("lightgreen")))
                else:
                    fitem.setBackground(0, QtGui.QBrush(QtGui.QColor(200,200,200)))
                    fitem.setBackground(1, QtGui.QBrush(QtGui.QColor(200,200,200)))
                if (self.ui.feeds.currentItem() and (fitem in [self.ui.feeds.currentItem(),self.ui.feeds.currentItem().parent()]))  or \
                        self.showAllFeeds or \
                        unread_count:
                    fitem.setHidden(False)
                else:
                    fitem.setHidden(True)
        else:
            # This is actually a new feed, so reload
            # feed list
            self.refreshFeeds()

    def loadFeeds(self, expandedFeedId=None, currentItemId=None):
        '''Creates all items for feeds and posts.

        If expandedFeedId is set, that feed's item will be expanded.
        if currentItemId is set, that item will be current (FIXME)

        '''
        scrollTo = None
        feeds=backend.Feed.query.order_by('name').all()
        feeds.sort(cmp=lambda x,y: -cmp(x.name.lower(),y.name.lower()))
        self.ui.feeds.clear()
        self.feed_icon = QtGui.QIcon(':/icons/feed.svg')
        self.warning_icon = QtGui.QIcon(':/icons/warning.svg')
        self.error_icon = QtGui.QIcon(':/icons/error.svg')
        # Add "some recent"
        fitem = QtGui.QTreeWidgetItem(['',"Recent",'BB'])
        fitem.setBackground(0, QtGui.QBrush(QtGui.QColor("lightgreen")))
        fitem.setIcon(0,self.feed_icon)
        fitem.setBackground(1, QtGui.QBrush(QtGui.QColor("lightgreen")))
        fitem._id = -1
        self.ui.feeds.addTopLevelItem(fitem)
        if expandedFeedId == -1:
            fitem.setExpanded(True)
            scrollTo = fitem
            
        #for post in posts:
            #pitem = post.createItem(fitem)

        #posts = backend.Post.query.filter(backend.Post.star==True)
        fitem = QtGui.QTreeWidgetItem(['',"Starred",'BA'])
        fitem.setBackground(0, QtGui.QBrush(QtGui.QColor("lightgreen")))
        fitem.setIcon(0, self.feed_icon)
        fitem.setBackground(1, QtGui.QBrush(QtGui.QColor("lightgreen")))
        fitem._id = -2
        self.ui.feeds.addTopLevelItem(fitem)
        if expandedFeedId == -2:
            fitem.setExpanded(True)
            
        #for post in posts:
            #pitem=post.createItem(fitem)

        i=0
        # FIXME: this does a lot of unnecesary work
        for feed in feeds:
            i+=1
            if  i%5==0:
                QtCore.QCoreApplication.instance().processEvents()
            unread_count = min(100,backend.Post.query.filter_by(feed=feed, read=False).count())
            tt=backend.h2t(feed.name)
            tt2='A%09d'%(i)
            fitem=QtGui.QTreeWidgetItem(['','%s (%d)'%(tt,unread_count),tt2])
            if feed.bad_check_count > 5:
                fitem.setIcon(0,self.error_icon)
            elif feed.last_status == 301:
                fitem.setIcon(0,self.warning_icon)
            else:
                fitem.setIcon(0,self.feed_icon)
            if unread_count:
                fitem.setBackground(0, QtGui.QBrush(QtGui.QColor("lightgreen")))
                fitem.setBackground(1, QtGui.QBrush(QtGui.QColor("lightgreen")))
            else:
                fitem.setBackground(0, QtGui.QBrush(QtGui.QColor(200,200,200)))
                fitem.setBackground(1, QtGui.QBrush(QtGui.QColor(200,200,200)))
                
            fitem._id = feed.xmlurl
            self.ui.feeds.addTopLevelItem(fitem)
            if expandedFeedId == feed.xmlurl:
                fitem.setExpanded(True)
                scrollTo = fitem
            if fitem._id == expandedFeedId or \
                    self.showAllFeeds or unread_count:
                fitem.setHidden(False)
            else:
                fitem.setHidden(True)
                
        if scrollTo:
            self.ui.feeds.scrollToItem(scrollTo)

    def on_feeds_itemClicked(self, item=None, column=1):
        if item is None: return
        fitem = item.parent()
        if fitem: # Post
            p=backend.Post.get_by(_id=item._id)
            data = pickle.loads(base64.b64decode(p.data))

            # We display differently depending on current mode
            # The modes are:
            # ["Feed Decides", "Site", "Feed", "Fast Site", "Fast Feed"]
            
            # Use feed mode as feed decides for a while
            if self.mode == 0:
                self.mode = 2
            if self.mode == 0:
                # Feed decides
                self.ui.html.load(QtCore.QUrl(p.url))
            elif self.mode == 1:
                # Site mode
                self.ui.html.load(QtCore.QUrl(p.url))
            elif self.mode == 2:
                # Feed mode

                #content = ''
                #if 'content' in data:
                    #content = '<hr>'.join([c.value for c in data['content']])
                #elif 'summary' in data:
                    #content = data['summary']
                #elif 'value' in data:
                    #content = data['value']
                #else:
                    #print "Can't find content in this entry"
                    #print data

                ## Rudimentary NON-html detection
                #if not '<' in content:
                    #content=escape(content).replace('\n\n', '<p>')
                
                self.ui.html.setHtml(renderTemplate('post.tmpl',
                    post = p,
                    data = data,
                    content = p.content,
                    cssdir = tmplDir,
                    escapedposturl=cgi.escape(p.url),
                    escapedposttitle=cgi.escape(p.title),
                    ))
            elif self.mode == 3:
                # Fast site mode
                fname = os.path.join(backend.dbdir, 'cache',
                    '%s.jpg'%hashlib.md5(p._id).hexdigest())
                if os.path.exists(fname):
                    self.ui.html.setHtml('''<img src="file://%s" style="max-width:100%%;">'''%fname)
                else:
                    self.ui.html.load(QtCore.QUrl(p.url))
            elif self.mode == 4:
                # Fast Feed mode
                pass

            # Enclosures
            for enclosure in self.enclosures:
                enclosure.hide()
                enclosure.deleteLater()
            self.enclosures=[]
            resize = False
            for e in data.get('enclosures',[]):
                # FIXME: add generic 'download' enclosure widget
                cls = None
                if hasattr(e,'type'):
                    if e.type.startswith('audio'):
                        cls = AudioPlayer
                    elif e.type.startswith('video') or \
                        e.href.split('.')[-1] in ['ogv','m4v','avi','mp4']:
                        cls = VideoPlayer
                        resize = True
                    if cls:
                        player = cls(e.href,
                            self.enclosureContainer)
                        player.show()
                        self.enclosures.append(player)
                        self.enclosureLayout.addWidget(player)
            if self.enclosures:
                self.enclosureContainer.show()
                if resize:
                    self.enclosureContainer.setGeometry(0,0,self.width(), 200)
            else:
                self.enclosureContainer.hide()
            
            p.read=True
            if column == 0:
                print 'Star clicked setting to:', not p.star
                p.star = not p.star
                if p.star:
                    item.setIcon(0,QtGui.QIcon(':/icons/star.svg'))
                else:
                    item.setIcon(0,QtGui.QIcon(':/icons/star2.svg'))
            
            backend.saveData()
            
            item.setForeground(1, QtGui.QBrush(QtGui.QColor("lightgray")))
            if fitem._id != p.feed.xmlurl: # Also mark as read in the post's feed
                item = self.findPostItem(p)
            if item:
                item.setForeground(1, QtGui.QBrush(QtGui.QColor("lightgray")))
                if p.star:
                    item.setIcon(0,QtGui.QIcon(':/icons/star.svg'))
                else:
                    item.setIcon(0,QtGui.QIcon(':/icons/star2.svg'))

            # Update unread count
            self.updateFeed(p.feed.xmlurl)
        else: # Feed
            self.enclosureContainer.hide()
            self.updateCurrentFeed()
            feed=backend.Feed.get_by(xmlurl=item._id)
            if feed:
                # Timeline data structure
                tdata={}
                #tdata['events']=[{
                #    'start': p.date.strftime(r"%b %d %Y %H:%M:00 GMT"),
                #    'title': p.title,
                #    'link': p.url,
                #    } for p in feed.posts]
                data = pickle.loads(base64.b64decode(feed.data))
                if 'status' in data:
                    status = data['status']
                else:
                    status = 'Unknown'
                self.ui.html.setHtml(renderTemplate('feed.tmpl',
                    timelinedata = json.dumps(tdata),
                    feed = feed,
                    cssdir = tmplDir,
                    status = status,
                    ))
            else:
                self.ui.html.setHtml("")

            if not item.isExpanded():
                self.ui.feeds.collapseAll()
                item.takeChildren()
                item.setExpanded(True)
            self.showFeedPosts(item, feed)

    def showFeedPosts(self, item, feed):
        '''Given a feed and an item, it shows the feed's posts as
        children of the item, and updates what the feed item shows'''
        if feed:
            unread_count = min(len(filter(lambda p: not p.read, feed.posts)), 100)
            item.setText(1,backend.h2t('%s (%d)'%(feed.name,unread_count)))

            items = {}
            for i in range(item.childCount()):
                items[item.child(i)._id]=item
            if self.showAllPosts:
                postList = feed.posts[:100]
            else:
                postList = backend.Post.query.filter_by(feed = feed, read=False).order_by(-backend.Post.date).limit(100).all()
            for i,post in enumerate(postList):
                if i%10==0:
                    QtCore.QCoreApplication.instance().processEvents()
                if post.read == False or self.showAllPosts:
                    # Should be visible

                    if post._id not in items:
                        # But it's not there
                        pitem=post.createItem(item)
                        
        elif item._id==-1:
            self.updateRecentFeed()
        elif item._id==-2:
            self.updateStarredFeed()


    def on_actionNew_Feed_triggered(self, b=None):
        '''Ask for site or feed URL and add it to backend'''
        
        # FIXME: this is silly slow and blocking.
        
        if b is not None: return
        url,r=QtGui.QInputDialog.getText(self, 
            "Kakawana - New feed", 
            "Enter the URL for the site")
        if not r:
            return
        url=unicode(url)
        feeds=[]
        feedurls=feedfinder.feeds(url)
        if not feedurls:
            # Didn't find any feeds
            QtGui.QMessageBox.critical(self, self.tr("Kakawana - Error"),
                self.tr("Couldn't find any feeds at that URL."))
            return
        for furl in feedurls:
            f=feedparser.parse(furl)
            feeds.append(f)
        if len(feeds) > 1:
            items = [ u'%d - %s'%(i,feed['feed']['title']) for i,feed in enumerate(feeds) ]
            ll=QtCore.QStringList()
            for i in items:
                ll.append(QtCore.QString(i))
            item, ok = QtGui.QInputDialog.getItem(self,
                u"Kakawana - New feed",
                u"What feed do you prefer for this site?",
                ll,
                editable = False)
            if not ok:
                return
            # Finally, this is the feed URL
            feed = feeds[items.index(unicode(item))]
            furl = feedurls[items.index(unicode(item))]
        else:
            feed = feeds[0]
            furl = feedurls[0]
        f = backend.Feed.createFromFPData(furl, feed)
        
        f.addPosts(feed=feed)
        self.loadFeeds(f.xmlurl)
        if self.keepGoogleSynced:
            # Add this feed to google reader
            reader = self.getGoogleReader2()
            if reader:
                print 'Adding to google:', f.xmlurl, f.name
                reader.subscribe_feed(f.xmlurl, f.name)

    def modeChange(self, mode=None):
        #if not isinstance(mode, int):
            #return
        self.mode = mode
        print "Switching to mode:", mode
        self.on_feeds_itemClicked(self.ui.feeds.currentItem())

    def on_actionUpdate_Feed_activated(self, b=None):
        if b is not None: return
        self.updateCurrentFeed()

    def refreshFeeds(self):
        '''Like a loadFeeds, but always keeps the current one open'''
        # FIXME: this is very inefficient
        item = self.ui.feeds.currentItem()
        _id = None
        _pid = None
        if item:
            fitem = item.parent()
            _pid = item._id
            if not fitem:
                fitem = item
            _id = fitem._id
        self.loadFeeds(_id, currentItemId = _pid)

    def on_actionEdit_Feed_activated(self, b=None):
        if b is not None: return

        item = self.ui.feeds.currentItem()
        _id = None
        if item:
            fitem = item.parent()
            if not fitem:
                fitem = item
            _id = fitem._id

        feed = backend.Feed.get_by(xmlurl=_id)
        if not feed: # No feed selected
            return

        if not self.feed_properties:
            from feedproperties import Feed_Properties
            self.feed_properties = Feed_Properties()
        self.ui.vsplitter.addWidget(self.feed_properties)

        # get feed and load data into the widget
        self.feed_properties.name.setText(backend.h2t(feed.name))
        self.feed_properties.url.setText(feed.url or '')
        self.feed_properties.xmlurl.setText(feed.xmlurl)
        
        self.feed_properties.show()

    def on_actionConfigure_Google_Account_activated(self, b=None):
        if b is not None: return
        from google_import import Google_Import
        d = Google_Import(parent = self)
        username = keyring.get_password('kakawana', 'google_username') or ''
        password = keyring.get_password('kakawana', 'google_password') or ''

        d.username.setText(username)
        d.password.setText(password)
        if username or password:
            d.remember.setChecked(True)
        r = d.exec_()
        if r == QtGui.QDialog.Rejected:
            return None
        username = unicode(d.username.text())
        password = unicode(d.password.text())
        if d.remember.isChecked():
            # Save in appropiate keyring
            keyring.set_password('kakawana','google_username',username)
            keyring.set_password('kakawana','google_password',password)
        return username, password

    def getGoogleReader(self):
        reader = None
        if self.keepGoogleSynced:
            username = keyring.get_password('kakawana', 'google_username') or ''
            password = keyring.get_password('kakawana', 'google_password') or ''
            if not username or not password:
                # Show config dialog
                username, password = on_actionConfigure_Google_Account_activated()
            if username and password:
                auth = gr.ClientAuth(username, password)
                reader = gr.GoogleReader(auth)
        return reader

    def getGoogleReader2(self):
        reader = None
        if self.keepGoogleSynced:
            username = keyring.get_password('kakawana', 'google_username') or ''
            password = keyring.get_password('kakawana', 'google_password') or ''
            if not username or not password:
                # Show config dialog
                username, password = on_actionConfigure_Google_Account_activated()
            if username and password:
                reader = GoogleReaderClient(username, password)
        return reader

    def on_actionImport_Google_Reader_activated(self, b=None):
        if b is not None: return
        reader = self.getGoogleReader()
        if not reader: return
        reader.buildSubscriptionList()
        feeds = reader.getFeeds()
        for f in feeds:
            f1 = backend.Feed.update_or_create(dict(name = f.title.decode('utf-8'), xmlurl = f.url),
                surrogate=False)
        backend.saveData()
        self.refreshFeeds()

    def on_actionSync_Google_Feeds_activated(self, b=None):
        if b is not None: return

        print 'Syncing google feed subscriptions'
        
        reader = self.getGoogleReader()
        if not reader: return
        
        reader.buildSubscriptionList()
        g_feeds = reader.getFeeds()
        # Check what feeds exist in google and not here:
        new_in_google=[]
        print g_feeds
        for f in g_feeds:
            print f.url, type(backend.Feed.get_by(xmlurl = f.url))
            if not backend.Feed.get_by(xmlurl = f.url):
                new_in_google.append(f.url)
                # Add it to the DB via fetcher
                fetcher_in.put(['add',f.url])
        print 'New in Google: %d feeds'%len(new_in_google)

        # Check what feeds exist here and not in google:
        g_feed_dict={}
        for f in g_feeds:
            g_feed_dict[f.url] = f
        new_here = []
        for f in backend.Feed.query.all():
            if f.xmlurl not in g_feed_dict:
                new_here.append([f.xmlurl, f.name])
        print 'New here: %d feeds'%len(new_here)
        # FIXME: don't aways do this
        reader = self.getGoogleReader2()
        if reader:
            for xmlurl, name in new_here:
                print 'Adding to gogle:', xmlurl, name
                reader.subscribe_feed(xmlurl, name)

        # Check what feeds have been deleted here since last sync:

    def on_actionShow_All_Posts_toggled(self, b=None):
        print 'SAP:', b
        self.showAllPosts = b
        item = self.ui.feeds.currentItem()
        fitem = item.parent()
        if not fitem:
            fitem = item
        if fitem._id in (-1,-2):
            return        
        self.on_feeds_itemClicked(item=fitem, column=1)

    def on_actionShow_All_Feeds_toggled(self, b=None):
        print 'SAF:', b 
        self.showAllFeeds = b
        self.refreshFeeds()

    def on_actionSpace_activated(self, b=None):
        '''Scroll down the current post, or jump to the next one'''
        if b is not None: return
        frame = self.html.page().mainFrame()
        if frame.scrollBarMaximum(QtCore.Qt.Vertical) == \
            frame.scrollPosition().y():
                self.on_actionNext_activated()
        else:
            frame.scroll(0,self.html.height())
            
    def on_actionNext_activated(self, b=None):
        '''Jump to the beginning of the next post'''
        if b is not None: return
        item = self.ui.feeds.currentItem()
        if not item:
            item = self.ui.feeds.topLevelItem(0)
        if item:
            item = self.ui.feeds.itemBelow(item)
            self.ui.feeds.setCurrentItem(item)
            self.on_feeds_itemClicked(item)
            
    def on_actionPrevious_activated(self, b=None):
        '''Jump to the beginning of the previous post'''
        if b is not None: return
        item = self.ui.feeds.currentItem()
        if not item:
            item = self.ui.feeds.topLevelItem(0)
        if item:
            item = self.ui.feeds.itemAbove(item)
            self.ui.feeds.setCurrentItem(item)
            self.on_feeds_itemClicked(item)
            
    def on_actionKeep_Unread_activated(self, b=None):
        '''Mark the current post as unread'''
        # FIXME this **can** be called without the item being current
        # if the user calls it from the page link, so it should take an ID
        # as optional argument
        if b is not None: return
        item = self.ui.feeds.currentItem()
        if not item.parent(): return # Not a post
        post = backend.Post.get_by(_id = item._id)
        if not post: return
        post.read = False
        backend.saveData()
        self.refreshFeeds()

    def on_actionStar_toggled(self, b=None):
        '''Mark the current post as unread'''
        # FIXME this **can** be called without the item being current
        # if the user calls it from the page link, so it should take an ID
        # as optional argument
        if b is None: return
        item = self.ui.feeds.currentItem()
        if not item.parent(): return # Not a post
        post = backend.Post.get_by(_id = item._id)
        if not post: return
        post.star = b
        backend.saveData()
        self.refreshFeeds()


    def on_actionDelete_Feed_activated(self, b=None):
        '''Unsubscribe from current feed'''
        if b is not None: return
        item = self.ui.feeds.currentItem()
        if item:
            fitem = item.parent()
            if not fitem:
                fitem = item
            feed = backend.Feed.get_by(xmlurl = fitem._id)
            if not feed: return

            # Got the current feed, now, must delete it
            feed.delete()
            # Delete all feedless posts
            for p in backend.Post.query.filter_by(feed=None).all():
                p.delete()
            backend.saveData()

            # May need to delete feed from google
            if self.keepGoogleSynced:
                try:
                    # Add this feed to google reader
                    reader = self.getGoogleReader2()
                    if reader:
                        print 'Unsubscribing at google: ', fitem._id
                        reader.unsubscribe_feed(fitem._id)
                except Exception, e:
                    # I'm not going to worry if this fails
                    print e
            self.loadFeeds()

    def on_actionKeep_Google_Synced_toggled(self, b):
        self.keepGoogleSynced = b

    def expirePosts(self):
        print 'Expiring posts'
        print 'Before:', backend.Post.query.count()
        feedcount = backend.Feed.query.count()
        progress = QtGui.QProgressDialog(self)
        progress.setLabelText(self.tr('Deleting old posts'))
        progress.show()
        progress.setAutoClose(True)
        QtCore.QCoreApplication.processEvents()

        progress.setMaximum(feedcount)
        flag = True
        for i,f in enumerate(backend.Feed.query):
            print 'Expiring: ', f.xmlurl
            progress.setValue(i)
            QtCore.QCoreApplication.processEvents()
            if progress.wasCanceled():
                flag = False
                break
            f.expire()
        print 'After:', backend.Post.query.count()
        if flag:
            self.settings.setValue('lastexpiration',QtCore.QDateTime.currentDateTime())
    
    def on_actionQuit_activated(self, b=None):
        if b is not None: return
        self.close()
        now = QtCore.QDateTime.currentDateTime()

        lastExpiration = self.settings.value("lastexpiration",
            QtCore.QVariant(now)).toDateTime()
        print 'Last expired:', lastExpiration
        if lastExpiration.daysTo(now) > 3:
            self.expirePosts()
        
        QtCore.QCoreApplication.instance().quit()

    def on_actionAbout_Kakawana_activated(self, b=None):
        if b is not None: return
        self.ui.html.setHtml (
            '''
<body style="font-family: sans-serif; margin: auto; width: 520px;">
<img src="file://%s/kakawana-about.jpg" width="520px" border="0"/>
<div style="position: absolute; top:15px; padding-left: 10px; color: #F4ECE3;font-size: 14px; width: 500px;">
<span style="font-size: 21px; font-weight: bold; color: #F4ECE3;">Kakawana: a better way to get your news.</span><hr>
(c) 2010: Roberto Alsina <a style="font-size: 14px; color: #F4F4a3; text-decoration: none;" href="mailto:ralsina@netmanagers.com.ar">&lt;ralsina@netmanagers.com.ar&gt;</a></br>
Website: <a style="font-size: 14px; color: #F4F4a3; text-decoration: none;" href="http://kakawana.googlecode.com">http://kakawana.googlecode.com</a><br>
<a style="font-size: 14px; color: #F4F4a3; text-decoration: none;" href="http://www.paypal.com/cgi-bin/webscr?cmd=_donations&amp;amp;business=Q6R5YDDPM2RL6&amp;amp;lc=AR&amp;amp;item_name=kakawana&amp;amp;item_number=kakawana&amp;amp;currency_code=USD&amp;amp;bn=PP%%2dDonationsBF%%3abtn_donate_LG%%2egif%%3aNonHosted">Donations</a><p>
Kakawana is free software:<a style="font-size: 14px; color: #F4F4a3; text-decoration: none;" href="http://code.google.com/p/kakawana/wiki/License"> learn more</a>
</div>
            '''%tmplDir )

    def closeEvent(self, event):
        self.settings.setValue('geometry', self.saveGeometry())
        self.settings.setValue('state', self.saveState())
        QtGui.QMainWindow.closeEvent(self, event)

def main():
    # Init the database before doing anything else
    backend.initDB()
    
    app = QtGui.QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window=Main()
    window.show()
    # It's exec_ because exec is a reserved word in Python
    sys.exit(app.exec_())
    

if __name__ == "__main__":
    main()
