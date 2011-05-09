# -*- coding: utf-8 -*-

import os
from PyQt4 import QtCore, QtGui, uic

class Google_Import(QtGui.QDialog):
    def __init__(self, parent):

        QtGui.QDialog.__init__(self, parent = None)
        
        uifile = os.path.join(
            os.path.abspath(
                os.path.dirname(__file__)),'google_import.ui')
        uic.loadUi(uifile, self)

