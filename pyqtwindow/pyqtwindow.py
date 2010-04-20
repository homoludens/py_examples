#!/usr/bin/python
# Code Example: Display a <strong class="highlight">window</strong> in <strong class="highlight">PyQt4</strong>
# Python 2.6 with PyQt 4

import sys
from PyQt4 import QtGui
from PyQt4 import QtCore

import time
from pythonwifi.iwlibs import Wireless
import shlex, subprocess

class MainFrame(QtGui.QMainWindow):

    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.setWindowTitle("PyQtCal") # title
        self.resize(280, 600) # size
        self.setMinimumSize(200, 200) # minimum size
        self.move(-281, 100) # position window frame at top left
	self.setMouseTracking(1)


        self.cal = QtGui.QCalendarWidget(self)
        self.cal.setGridVisible(False)
        self.cal.move(20, 20)
	self.cal.setGeometry(10, 10, 260, 160)

	self.mySlider = QtGui.QSlider(QtCore.Qt.Horizontal, self)
	self.mySlider.move(20, 200)
	self.mySlider.resize(240,50)
	self.mySlider.setRange(0,99)
	self.mySlider.setValue(50)

	self.button1 = QtGui.QPushButton("1",self)
	self.button2 = QtGui.QPushButton("2",self)
	self.button3 = QtGui.QPushButton("3",self)
	self.button4 = QtGui.QPushButton("4",self)

	self.button1.move(20, 250)
	self.button2.move(80, 250)
	self.button3.move(140, 250)
	self.button4.move(200, 250)

	self.button1.resize(50, 30)
	self.button2.resize(50, 30)
	self.button3.resize(50, 30)
	self.button4.resize(50, 30)

	self.signalLevel = QtGui.QProgressBar( self)
	self.signalLevel.move(20, 300)
	self.signalLevel.resize(240,30)
	self.signalLevel.setRange(0,99)
	self.signalLevel.setValue(0)

	self.getSignalLevel()
	#wifi = Wireless('wlan0') 
	#essid = wifi.getEssid()
	#signal = "xx"
	#try:
	  #signal = wifi.getQualityAvg().signallevel
	  #self.signalLevel.setValue(signal)
	#except:
	  #pass
	#self.signalLevel.setFormat(str(essid)+"  "+str(signal))
	
	QtCore.QObject.connect(self.mySlider, QtCore.SIGNAL("valueChanged(int)"), self.__update_master_volume)	
	QtCore.QObject.connect(self.button1, QtCore.SIGNAL('clicked()'), self.__change_to_workspace_1)
	QtCore.QObject.connect(self.button2, QtCore.SIGNAL('clicked()'), self.__change_to_workspace_2)
	QtCore.QObject.connect(self.button3, QtCore.SIGNAL('clicked()'), self.__change_to_workspace_3)
	QtCore.QObject.connect(self.button4, QtCore.SIGNAL('clicked()'), self.__change_to_workspace_4)

    def enterEvent(self, e):
	#print "In"
	#pushButton.move(0 , 100)
	self.getSignalLevel()
	self.get_master_volume()
	for i in range(1,11):
	    self.move(-280 + i*28, 100)
 
    def leaveEvent(self, e):
	#print "Out"
	#pushButton.move(-281, 100)
	for i in range(1,11):
	    self.move(0 - i*28, 100)

    #def mouseMoveEvent(self, event): 
	#print "on Hover", event.pos().x(), event.pos().y() 

    def getSignalLevel(self):
	wifi = Wireless('wlan1') 
	essid = wifi.getEssid()
	signal = "xx"
	try:
	  signal = wifi.getQualityAvg().signallevel
	  self.signalLevel.setValue(signal)
	except:
	  pass
	self.signalLevel.setFormat(str(essid)+"  "+str(signal))
	return True

    #
    #  Get PCM volume
    #
    def get_master_volume(self):
        proc = subprocess.Popen('/usr/bin/amixer sget PCM', shell=True, stdout=subprocess.PIPE)
        amixer_stdout = proc.communicate()[0].split('\n')[5]
        proc.wait()

        find_start = amixer_stdout.find('[') + 1
        find_end = amixer_stdout.find('%]', find_start)
	#print amixer_stdout[find_start:find_end]
	self.mySlider.setValue(int(amixer_stdout[find_start:find_end]))
        #return float(amixer_stdout[find_start:find_end])
	return True

    #
    #  Set PCM volume
    #
    def __update_master_volume(self, widget):
        val = self.mySlider.value()
        proc = subprocess.Popen('/usr/bin/amixer sset PCM ' + str(val) + '%', shell=True, stdout=subprocess.PIPE)
        proc.wait()

    def copy_to_all(self):
        proc = subprocess.Popen('/usr/bin/xsendkeys Alt_L+v', shell=True, stdout=subprocess.PIPE)
        proc.wait()

   
    def __change_to_workspace_1(self):
        proc = subprocess.Popen('/usr/bin/xsendkeys Alt_L+1', shell=True, stdout=subprocess.PIPE)
        proc.wait()

    def __change_to_workspace_2(self):
        proc = subprocess.Popen('/usr/bin/xsendkeys Alt_L+2', shell=True, stdout=subprocess.PIPE)
        proc.wait()

    def __change_to_workspace_3(self):
        proc = subprocess.Popen('/usr/bin/xsendkeys Alt_L+3', shell=True, stdout=subprocess.PIPE)
        proc.wait()

    def __change_to_workspace_4(self):
        proc = subprocess.Popen('/usr/bin/xsendkeys Alt_L+4', shell=True, stdout=subprocess.PIPE)
        proc.wait()


    def _actionHovered(self, action):
	print 'hover'
	tip = action.toolTip()
	QtGui.QToolTip.showText(QtGui.QCursor.pos(), tip)




if __name__ == "__main__":
    app = QtGui.QApplication(sys.argv)
    
    frame = MainFrame()
    frame.get_master_volume()
    frame.show()
    #frame.copy_to_all()
    #for i in range(1,11):
      #frame.move(-300 + i*30, 100)
    exit_code = app.exec_()
    sys.exit(exit_code)