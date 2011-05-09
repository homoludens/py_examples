# -*- coding: utf-8 -*-

"""Using kakawana's backend, update all feeds, and fetch all
web pages as images into the cache"""

import os, sys, hashlib, time
from PyQt4 import QtCore, QtGui, QtWebKit

import backend
from capty import Capturer

def run():
    # FIXME: reimplement, this is a CPU hog
    capturer = Capturer()
    for feed in backend.Feed.query.all():
        feed.addPosts()
        for p in feed.posts:
            if not p.read:
                fname = os.path.join(cachedir,
                    '%s.jpg'%hashlib.md5(p._id).hexdigest())
                if not os.path.exists(fname):
                    print "Capture %s => %s"%(p.url, fname)
                    capturer.capture(p.url, fname)
                    while capturer.done == False:
                        QtCore.QCoreApplication.processEvents()
    QtCore.QCoreApplication.instance().quit()

if __name__ == "__main__":
    cachedir = os.path.join(backend.dbdir, 'cache')
    if not os.path.isdir(cachedir):
        os.mkdir(cachedir)
    app = QtGui.QApplication(sys.argv)
    backend.initDB()
    QtCore.QTimer.singleShot(0,run)
    app.exec_()
