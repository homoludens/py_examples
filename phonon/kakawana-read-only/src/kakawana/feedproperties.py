# -*- coding: utf-8 -*-

import os
from PyQt4 import QtCore, QtGui, uic

class Feed_Properties(QtGui.QWidget):
    def __init__(self, parent = None):

        QtGui.QWidget.__init__(self, parent = parent)
        
        uifile = os.path.join(
            os.path.abspath(
                os.path.dirname(__file__)),'feedproperties.ui')
        uic.loadUi(uifile, self)

