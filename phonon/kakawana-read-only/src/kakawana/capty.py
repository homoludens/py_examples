# -*- coding: utf-8 -*-

"""This tries to do more or less the same thing as CutyCapt, but as a
python module.

This is a derived work from CutyCapt: http://cutycapt.sourceforge.net/

////////////////////////////////////////////////////////////////////
//
// CutyCapt - A Qt WebKit Web Page Rendering Capture Utility
//
// Copyright (C) 2003-2010 Bjoern Hoehrmann <bjoern@hoehrmann.de>
//
// This program is free software; you can redistribute it and/or
// modify it under the terms of the GNU General Public License
// as published by the Free Software Foundation; either version 2
// of the License, or (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// $Id$
//
////////////////////////////////////////////////////////////////////

"""

import sys
from PyQt4 import QtCore, QtGui, QtWebKit


class Capturer(object):
    """A class to capture webpages as images"""

    def __init__(self, url=None, filename=None):
        self.url = url
        self.filename = filename
        self.done = False
        self.wb = QtWebKit.QWebPage()
        self.wb.mainFrame().setScrollBarPolicy(
            QtCore.Qt.Horizontal, QtCore.Qt.ScrollBarAlwaysOff)
        self.wb.mainFrame().setScrollBarPolicy(
            QtCore.Qt.Vertical, QtCore.Qt.ScrollBarAlwaysOff)

        self.wb.loadFinished.connect(self.loadFinishedSlot)
        self.wb.mainFrame().initialLayoutCompleted.connect(
            self.initialLayoutSlot)

    def loadFinishedSlot(self):
        self.saw_document_complete = True
        if self.saw_initial_layout and self.saw_document_complete:
            self.doCapture()

    def initialLayoutSlot(self):
        self.saw_initial_layout = True
        if self.saw_initial_layout and self.saw_document_complete:
            self.doCapture()

    def capture(self, url=None, filename=None):
        """Captures url as an image to the file specified"""
        if url is not None:
            self.url = url
        if filename is not None:
            self.filename = filename

        if url is None or filename is None:
            return
        self.saw_initial_layout = False
        self.saw_document_complete = False
        self.done = False
        
        self.wb.mainFrame().load(QtCore.QUrl(self.url))

    def doCapture(self):
        self.wb.setViewportSize(self.wb.mainFrame().contentsSize())
        img = QtGui.QImage(self.wb.viewportSize(), QtGui.QImage.Format_ARGB32)
        painter = QtGui.QPainter(img)
        self.wb.mainFrame().render(painter)
        painter.end()
        img.save(self.filename)
        self.done=True
        print "Captured"

if __name__ == "__main__":
    """Run a simple capture"""
    app = QtGui.QApplication(sys.argv)
    c = Capturer(sys.argv[1], sys.argv[2])
    c.capture()
    app.exec_()
