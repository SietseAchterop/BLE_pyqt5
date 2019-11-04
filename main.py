import sys

from PyQt5.QtGui import QGuiApplication
from PyQt5.QtQml import QQmlApplicationEngine, qmlRegisterType
from PyQt5.QtCore import QVariant, QObject, pyqtSignal, pyqtSlot, pyqtProperty, QMetaObject, Qt, QTimer
from PyQt5 import QtBluetooth as QtBt


class DeviceInfo(QObject):

    deviceChanged = pyqtSignal()

    def __init__(self, d=None):
        QObject.__init__(self)
        if d is not None:
            self.device = d

    def getAddress(self):
        return self.device.address().toString()

    def getName(self):
        return self.device.name()

    def getDevice(self):
        return self.device

    def setDevice(self, dev):
        self.device = QtBt.QBluetoothDeviceInfo(dev)
        self.deviceChanged.emit()

    deviceName = pyqtProperty(str, getName, notify=deviceChanged)
    deviceAddress = pyqtProperty(str, getAddress, notify=deviceChanged)


class ServiceInfo(QObject):

    serviceChanged = pyqtSignal()

    def __init__(self, s: QtBt.QLowEnergyService):
        QObject.__init__(self)
        if s is not None:
            self.services = s

    def service(self):
        return self.services

    def getName(self) -> str:
        if self.services is None:
            return ''
        return self.services.serviceName()

    def getType(self):
        if self.services is None:
            return ''

        result = ''
        if self.services.type() & QtBt.QLowEnergyService.PrimaryService:
            result += 'primary'
        else:
            result += 'secondary'
        if self.services.type() & QtBt.QLowEnergyService.IncludedService:
            result += ' included'

        result = '<' + result + '>'
        return result

    def getUuid(self):
        if self.services is None:
            return ''

        uuid = self.services.serviceUuid()
        # print(f'uuid is: {uuid.toString()}')
        # print(f"gestripte uuid: {uuid.toString().replace('{', '').replace('}', '').replace('-', '')}")
        
        # waarom dit? de kortere uuids?
        # waarom geen argument bij toUint16??
        success = False
        result16 = uuid.toUInt16()
        if success:
            return '0x' + str(result16)    # nog hex van maken
        result32 = uuid.toUInt32()
        if success:
            return '0x' + str(result32)
        return uuid.toString().replace('{', '').replace('}', '')

    serviceName = pyqtProperty(str, getName, notify=serviceChanged)
    serviceUuid = pyqtProperty(str, getUuid, notify=serviceChanged)
    serviceType = pyqtProperty(str, getType, notify=serviceChanged)


class CharacteristicsInfo(QObject):

    characteristicChanged = pyqtSignal()

    def __init__(self, characteristic: QtBt.QLowEnergyCharacteristic = None):
        QObject.__init__(self)
        if characteristic is not None:
            self.characteristic = characteristic

    def setCharacteristic(self, characteristic: QtBt.QLowEnergyCharacteristic):
        self.characteristic = characteristic
        self.characteristicChanged.emit()

    def getName(self) -> str:
        name = self.characteristic.name()
        if name is not '':
            return name

        # find descriptor with CharacteristicUserDescription
        descriptors = self.characteristic.descriptors()
        for descriptor in descriptors:
            if descriptor.type() == QtBt.QBluetoothUuid.CharacteristicUserDescription:
                name = str(descriptor.value())
                # via descriptor komt de b'---' erbij!
                break

        if name is '':
            name = 'Unknown'

        return name

    def getUuid(self) -> str:
        uuid = self.characteristic.uuid()
        success = False
        result16 = uuid.toUInt16()
        if success:
            return '0x' + str()    # nog hex van maken
        result32 = uuid.toUInt32()
        if success:
            return '0x' + str(result32)
        return uuid.toString()  # {} er nog afhalen

    def getValue(self) -> str:
        a = self.characteristic.value()
        result = ''
        if a.isEmpty():
            result = '<none>'
            return result

        result = a
        result += '\n'
        result += a.toHex()
        return str(result)

    def getHandle(self) -> str:
        return '0x' + str(self.characteristic.handle())    # nog hex van maken

    def getPermission(self) -> str:
        properties = '( '
        permission = self.characteristic.properties()
        if permission & QtBt.QLowEnergyCharacteristic.Read:
            properties += ' Read'
        if permission & QtBt.QLowEnergyCharacteristic.Write:
            properties += ' Write'
        if permission & QtBt.QLowEnergyCharacteristic.Notify:
            properties += ' Notify'
        if permission & QtBt.QLowEnergyCharacteristic.Indicate:
            properties += ' Indicate'
        if permission & QtBt.QLowEnergyCharacteristic.ExtendedProperty:
            properties += ' ExtendedProperty'
        if permission & QtBt.QLowEnergyCharacteristic.Broadcasting:
            properties += ' Broadcast'
        if permission & QtBt.QLowEnergyCharacteristic.WriteNoResponse:
            properties += ' WriteNoResp'
        if permission & QtBt.QLowEnergyCharacteristic.WriteSigned:
            properties += ' WriteSigned'
        properties += ' )'
        return properties

    def getCharacteristic(self) -> QtBt.QLowEnergyCharacteristic:
        return self.characteristic

    characteristicName = pyqtProperty(str, getName, notify=characteristicChanged)
    characteristicUuid = pyqtProperty(str, getUuid, notify=characteristicChanged)
    characteristicValue = pyqtProperty(str, getValue, notify=characteristicChanged)
    characteristicHandle = pyqtProperty(str, getHandle, notify=characteristicChanged)
    characteristicPermission = pyqtProperty(str, getPermission, notify=characteristicChanged)


########################################################


class Device(QObject):

    # Signals
    devicesUpdated         = pyqtSignal()
    servicesUpdated        = pyqtSignal()
    characteristicsUpdated = pyqtSignal()
    updateChanged          = pyqtSignal()
    stateChanged           = pyqtSignal()
    disconnected           = pyqtSignal()
    randomAddressChanged   = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # instance variables. Er is maar 1 instance?
        self.currentDevice     = DeviceInfo()     # type: DeviceInfo
        self.devices           = []               # type: List[DeviceInfo]
        self.m_services        = []               # type: List[QObject]
        self.m_characteristics = []               # type: List[QObject]
        self.m_previousAddress = ''
        self.m_message         = ''
        self.connected         = False
        self.m_deviceScanState = False
        self.randomAddress     = False

        self.discoveryAgent = QtBt.QBluetoothDeviceDiscoveryAgent()
        self.discoveryAgent.setLowEnergyDiscoveryTimeout(5000)

        self.discoveryAgent.deviceDiscovered.connect(self.addDevice)
        self.discoveryAgent.error.connect(self.deviceScanError)   # goede error?
        self.discoveryAgent.finished.connect(self.deviceScanFinished)

        self.controller = None
        self.setUpdate('Search')

    # Slot ?? welke nog meer?
    @pyqtSlot()
    def startDeviceDiscovery(self):
        self.devices = []  # ok?
        self.devicesUpdated.emit()

        self.setUpdate('Scanning for devices ...')
        self.discoveryAgent.start(QtBt.QBluetoothDeviceDiscoveryAgent.DiscoveryMethod(2)) # ?

        if self.discoveryAgent.isActive():
            self.m_deviceScanState = True
            self.stateChanged.emit()

    @pyqtSlot(QtBt.QBluetoothDeviceInfo)
    def addDevice(self, info):
        if info.coreConfigurations() & QtBt.QBluetoothDeviceInfo.LowEnergyCoreConfiguration:
            self.setUpdate(f'Last device added: {info.name()}')

    @pyqtSlot()
    def deviceScanFinished(self):
        foundDevices = self.discoveryAgent.discoveredDevices()
        for nextDevice in foundDevices:
            if nextDevice.coreConfigurations() & QtBt.QBluetoothDeviceInfo.LowEnergyCoreConfiguration:
                # print(f'UUID: {nextDevice.address().toString()}, Name: {nextDevice.name()}')
                self.devices.append(DeviceInfo(nextDevice))

        self.devicesUpdated.emit()
        self.m_deviceScanState = False
        self.stateChanged.emit()
        if self.devices is []:
            self.setUpdate('No Low Engergy devices found...')
        else:
            self.setUpdate('Done! Scan Again!')

    # QVariant
    def getDevices(self):
        return self.devices

    def getServices(self):
        return self.m_services

    def getCharacteristics(self):
        return self.m_characteristics

    def getUpdate(self):
        return self.m_message

    @pyqtSlot(str)  # ?
    def scanServices(self, address: str):
        for d in self.devices:
            # qobject_cast<DeviceInfo *>(d)  ??  iets van "zinnig device?"
            if d.getAddress() == address:
                self.currentDevice.setDevice(d.getDevice())

        if not self.currentDevice.getDevice().isValid():
            print(f'Warning: Not a valid device')
            return

        self.m_characteristics = []
        self.characteristicsUpdated.emit()
        self.m_services = []
        self.servicesUpdated.emit()

        self.setUpdate('Back\n(Connecting to device...)')

        if self.controller and self.m_previousAddress != self.currentDevice.getAddress():
            self.controller.disconnectFromDevice()
            self.controller = None

        if self.controller == None:
            self.controller = QtBt.QLowEnergyController.createCentral(self.currentDevice.getDevice())
            self.controller.connected.connect(self.deviceConnected)
            self.controller.error.connect(self.errorReceived)
            self.controller.disconnected.connect(self.deviceDisconnected)
            self.controller.serviceDiscovered.connect(self.addLowEnergyService)
            self.controller.discoveryFinished.connect(self.serviceScanDone)

        if self.isRandomAddress():
            self.controller.setRemoteAddressType(QtBt.QLowEnergyController.RandomAddress)
        else:
            self.controller.setRemoteAddressType(QtBt.QLowEnergyController.PublicAddress)
        self.controller.connectToDevice()

        self.m_previousAddress = self.currentDevice.getAddress()

    @pyqtSlot(QtBt.QBluetoothUuid)
    def addLowEnergyService(self, servUuid: QtBt.QBluetoothUuid):
        service = self.controller.createServiceObject(servUuid)
        if not service:
            print('Warning: Cannot create service for uuid')
            return
        serv = ServiceInfo(service)
        self.m_services.append(serv)
        # print(f'Added {serv.getName()}  lijst {self.m_services}')
        self.servicesUpdated.emit()

    @pyqtSlot()
    def serviceScanDone(self):
        self.setUpdate('Back\n(Service scan done!)')
        if self.m_services == []:
            self.servicesUpdated.emit()

    @pyqtSlot(str)
    def connectToService(self, uuid: str):
        for s in self.m_services:
            serviceInfo = s
            if not serviceInfo:
                continue

            if serviceInfo.getUuid() == uuid:
                service = serviceInfo.service()
                break

        if not service:
            print('return from connecttoservice')
            return

        self.m_characteristics = []
        self.characteristicsUpdated.emit()

        if service.state() == QtBt.QLowEnergyService.DiscoveryRequired:
            service.stateChanged.connect(self.serviceDetailsDiscovered)
            service.discoverDetails()
            self.setUpdate('Back\n(Discovering details...)')
            return

        chars = service.characteristics()
        for ch in chars:
            cInfo = CharacteristicsInfo(ch)
            self.m_characteristics.append(cInfo)

        # ?
        QTimer.singleShot(0, self.characteristicsUpdated)

    @pyqtSlot()
    def deviceConnected(self):
        self.setUpdate('Back\n(Discovering services...)')
        self.connected = True
        self.controller.discoverServices()

    @pyqtSlot(QtBt.QLowEnergyController.Error)
    def errorReceived(self, error=None):
        # print(f'Error:  {self.controller.errorString()}')
        self.setUpdate(f'Back\n{self.controller.errorString()}')

    def setUpdate(self, s: str):
        self.m_message = s
        self.updateChanged.emit()

    @pyqtSlot()  # ??
    def disconnectFromDevice(self):
        if self.controller.state() != QtBt.QLowEnergyController.UnconnectedState:
            self.controller.disconnectFromDevice()
        else:
            self.deviceDisconnected()

    @pyqtSlot()
    def deviceDisconnected(self):
        print('Warning Disconnect from device')
        self.disconnected.emit()

    @pyqtSlot(QtBt.QLowEnergyService.ServiceState)
    def serviceDetailsDiscovered(self, newState: QtBt.QLowEnergyService.ServiceState):
        if newState != QtBt.QLowEnergyService.ServiceDiscovered:
            if newState != QtBt.QLowEnergyService.DiscoveringServices:
                QMetaObject.invokeMethod(self, "characteristicsUpdated", Qt.QueuedConnection)
            return

        # hoe de casting als in C++  ?
        # service = QtBt.QLowEnergyService.sender()
        service = self.sender()
        if not service:
            return

        chars = service.characteristics()
        for ch in chars:
            cInfo = CharacteristicsInfo(ch)
            # print(f'Characteristics name {cInfo.getName()},  value {cInfo.getValue()},  Uuid {cInfo.getUuid()},  Handle {cInfo.getHandle()},  Permission {cInfo.getPermission()}')
            self.m_characteristics.append(cInfo)

        self.characteristicsUpdated.emit()

    @pyqtSlot(QtBt.QBluetoothDeviceDiscoveryAgent.Error)
    def deviceScanError(self, error: QtBt.QBluetoothDeviceDiscoveryAgent.Error):
        if error == QtBt.QBluetoothDeviceDiscoveryAgent.PoweredOffError:
            self.setUpdate('The Bluetooth adaptor is powered off, power it on before doing discovery')
        elif error == QtBt.QBluetoothDeviceDiscoveryAgent.InputOutputError:
            self.setUpdate('Writing or reading from the device resulted in an error')
        else:
            qme = self.discoveryAgent.metaObject().enumerator(self.discoveryAgent.metaObject().indexOfEnumerator('Error'))
            x = qme.valueToKey(error)
            self.setUpdate('Error: ' + x)

        self.m_deviceScanState = False
        self.devicesUpdated.emit()
        self.stateChanged.emit()

    def state(self):
        return self.m_deviceScanState

    def hasControllerError(self):
        return self.controller and self.controller.error() != QtBt.QLowEnergyController.NoError

    def isRandomAddress(self):
        return self.randomAddress

    def setRandomAddress(self, newValue):
        self.RandomAddress = newValue
        self.randomAddressChanged.emit()

    devicesList = pyqtProperty(QVariant, getDevices, notify=devicesUpdated)
    servicesList = pyqtProperty(QVariant, getServices, notify=servicesUpdated)
    characteristicList = pyqtProperty(QVariant, getCharacteristics, notify=characteristicsUpdated)
    update = pyqtProperty(str, getUpdate, setUpdate, notify=updateChanged)
    useRandomAddress = pyqtProperty(bool, isRandomAddress, setRandomAddress, notify=randomAddressChanged)
    state = pyqtProperty(bool, state, notify=stateChanged)
    controllerError = pyqtProperty(bool, hasControllerError)


def startit():
    # Set trace
    # pyqtRemoveInputHook()
    # pdb.set_trace()

    # Create an instance of the application
    app = QGuiApplication(sys.argv)
    # Create QML engine
    engine = QQmlApplicationEngine()
    # Register Device class with QML
    qmlRegisterType(Device, 'Bluno', 1, 0, 'Device')

    # Load the qml file into the engine
    engine.load("assets/main.qml")

    engine.quit.connect(app.quit)
    sys.exit(app.exec_())


if __name__ == "__main__":
    startit()
# end
