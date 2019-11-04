import sys

from PyQt5.QtGui import QGuiApplication
from PyQt5.QtQml import QQmlApplicationEngine, qmlRegisterType
from PyQt5.QtCore import QVariant, QObject, pyqtSignal, pyqtSlot, pyqtProperty, pyqtRemoveInputHook
from PyQt5 import QtBluetooth as QtBt


# app = QGuiApplication(sys.argv)

devicesUpdated         = pyqtSignal()
servicesUpdated        = pyqtSignal()


def getDevices(self):
    print('devices')
    return 'de devices'

def getServices(self):
    print('services')
    return 'de services'


devicesList = pyqtProperty(QVariant, getDevices, notify=devicesUpdated)
servicesList = pyqtProperty(QVariant, getServices, notify=servicesUpdated)

self ='iets'
d=devicesList.fget(self)
print(d)
d=servicesList.fget(self)
print(d)
