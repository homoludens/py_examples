import sys
from PyQt4.QtCore import QCoreApplication, QUrl
from PyQt4.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

class Test:

    def __init__(self):

        request = QNetworkRequest(QUrl("http://www.riverbankcomputing.co.uk/news"))
        self.manager = QNetworkAccessManager()
        self.manager.finished.connect(self.handleReply)



        self.manager.get(request)

    def handleReply(self, reply):
	print reply.readAll()
        print reply.error()
        QCoreApplication.quit()

if __name__ == "__main__":

    app = QCoreApplication(sys.argv)
    test = Test()
    sys.exit(app.exec_())

['DeleteOperation', 'GetOperation', 'HeadOperation', 'Operation', 'PostOperation', 'PutOperation', '__class__', '__delattr__', '__dict__', '__doc__', '__format__', '__getattribute__', '__hash__', '__init__', '__module__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', 'authenticationRequired', 'blockSignals', 'cache', 'childEvent', 'children', 'connect', 'connectNotify', 'cookieJar', 'createRequest', 'customEvent', 'deleteLater', 'deleteResource', 'destroyed', 'disconnect', 'disconnectNotify', 'dumpObjectInfo', 'dumpObjectTree', 'dynamicPropertyNames', 'emit', 'event', 'eventFilter', 'findChild', 'findChildren', 'finished', 'get', 'head', 'inherits', 'installEventFilter', 'isWidgetType', 'killTimer', 'metaObject', 'moveToThread', 'objectName', 'parent', 'post', 'property', 'proxy', 'proxyAuthenticationRequired', 'proxyFactory', 'put', 'pyqtConfigure', 'receivers', 'removeEventFilter', 'sender', 'setCache', 'setCookieJar', 'setObjectName', 'setParent', 'setProperty', 'setProxy', 'setProxyFactory', 'signalsBlocked', 'sslErrors', 'startTimer', 'staticMetaObject', 'thread', 'timerEvent', 'tr', 'trUtf8']



['Append', 'AuthenticationRequiredError', 'ConnectionRefusedError', 'ContentAccessDenied', 'ContentNotFoundError', 'ContentOperationNotPermittedError', 'ContentReSendError', 'HostNotFoundError', 'NetworkError', 'NoError', 'NotOpen', 'OpenMode', 'OpenModeFlag', 'OperationCanceledError', 'ProtocolFailure', 'ProtocolInvalidOperationError', 'ProtocolUnknownError', 'ProxyAuthenticationRequiredError', 'ProxyConnectionClosedError', 'ProxyConnectionRefusedError', 'ProxyNotFoundError', 'ProxyTimeoutError', 'ReadOnly', 'ReadWrite', 'RemoteHostClosedError', 'SslHandshakeFailedError', 'Text', 'TimeoutError', 'Truncate', 'Unbuffered', 'UnknownContentError', 'UnknownNetworkError', 'UnknownProxyError', 'WriteOnly', '__class__', '__delattr__', '__dict__', '__doc__', '__format__', '__getattribute__', '__hash__', '__init__', '__module__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__sizeof__', '__str__', '__subclasshook__', '__weakref__', 'abort', 'aboutToClose', 'atEnd', 'attribute', 'blockSignals', 'bytesAvailable', 'bytesToWrite', 'bytesWritten', 'canReadLine', 'childEvent', 'children', 'close', 'connect', 'connectNotify', 'customEvent', 'deleteLater', 'destroyed', 'disconnect', 'disconnectNotify', 'downloadProgress', 'dumpObjectInfo', 'dumpObjectTree', 'dynamicPropertyNames', 'emit', 'error', 'errorString', 'event', 'eventFilter', 'findChild', 'findChildren', 'finished', 'getChar', 'hasRawHeader', 'header', 'ignoreSslErrors', 'inherits', 'installEventFilter', 'isFinished', 'isOpen', 'isReadable', 'isRunning', 'isSequential', 'isTextModeEnabled', 'isWidgetType', 'isWritable', 'killTimer', 'manager', 'metaDataChanged', 'metaObject', 'moveToThread', 'objectName', 'open', 'openMode', 'operation', 'parent', 'peek', 'pos', 'property', 'putChar', 'pyqtConfigure', 'rawHeader', 'rawHeaderList', 'read', 'readAll', 'readBufferSize', 'readChannelFinished', 'readData', 'readLine', 'readLineData', 'readyRead', 'receivers', 'removeEventFilter', 'request', 'reset', 'seek', 'sender', 'setAttribute', 'setError', 'setErrorString', 'setHeader', 'setObjectName', 'setOpenMode', 'setOperation', 'setParent', 'setProperty', 'setRawHeader', 'setReadBufferSize', 'setRequest', 'setSslConfiguration', 'setTextModeEnabled', 'setUrl', 'signalsBlocked', 'size', 'sslConfiguration', 'sslErrors', 'startTimer', 'staticMetaObject', 'thread', 'timerEvent', 'tr', 'trUtf8', 'ungetChar', 'uploadProgress', 'url', 'waitForBytesWritten', 'waitForReadyRead', 'write', 'writeData']

