#!/usr/bin/env python3

# mqtt.py
# written by Malcolm Dixon 2020
# classes for working with paho mqtt library

import sys
import time
from enum import Enum, IntEnum, unique
import paho.mqtt.client as mqtt
from PySide2.QtCore import Signal, Slot, QObject
from helpers import enum_name_to_str, camel_case_to_sent_case


@unique
class ConnectionStatus(Enum):
    '''Mqtt connection status'''
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    DISCONNECTING = 3
    RECONNECTING = 4
    CONNECTION_ERROR = 5


@unique
class ConnAck(IntEnum):
    '''Mqtt connection acknowledgements'''
    CONNECTION_SUCCESSFUL = 0
    INCORRECT_PROTOCOL_VERSION = 1
    INVALID_CLIENT_IDENTIFIER = 2
    SERVER_UNAVAILABLE = 3
    BAD_USERNAME_OR_PASSWORD = 4
    NOT_AUTHORISED = 5


class Mqtt(QObject):

    connecting = Signal()
    connected = Signal()
    connection_error = Signal(str)
    disconnected = Signal(int)
    reconnecting = Signal(int)
    reconnect_failure = Signal()

    def __init__(self, client_id="", clean=True):
        super().__init__()
        self.enabled = True
        self.client_id = client_id
        self.clean = clean
        self.client = mqtt.Client(self.client_id, self.clean)
        self.state = ConnectionStatus.DISCONNECTED
        self.host = ""
        self.port = 1883
        self.timeout = 15
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 2
        # connect callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        self.client.on_subscribe = self.on_subscribe
        self.client.on_disconnect = self.on_disconnect

    @Slot()
    def connect_to_broker(self):
        # connect to the MQTT broker
        self.reconnect_attempts = 0
        while self.enabled:
            # signal the reconnect attempt no. if applicable
            if self.reconnect_attempts > 0:
                self.reconnecting.emit(self.reconnect_attempts)
            try:
                self.client.loop_start()
                self.state = ConnectionStatus.CONNECTING
                self.connecting.emit()
                self.client.connect_async(self.host, self.port)

                # wait for successful connection
                waiting = 0
                while self.enabled and self.state == ConnectionStatus.CONNECTING:
                    time.sleep(1)
                    waiting += 1
                    if waiting >= self.timeout:
                        raise TimeoutError

                # loop until connection state changes to not connected
                while self.enabled and self.state == ConnectionStatus.CONNECTED:
                    time.sleep(1)

            except Exception:
                self.state = ConnectionStatus.CONNECTION_ERROR
                # get exception's class details
                exception = sys.exc_info()
                print(exception)
                exception_class = str(exception[0]).split("'")[1]
                self.connection_error.emit(
                    camel_case_to_sent_case(exception_class))

                # disable connection if not a timeout exception
                if exception_class != "TimeoutError":
                    self.enabled = False

            finally:
                # if connection still enabled then check if can reconnect
                if self.enabled:
                    self.reconnect_attempts += 1
                    if self.reconnect_attempts > self.max_reconnect_attempts:
                        self.reconnect_failure.emit()
                        # disable connection due to too many errors
                        self.enabled = False

        # disconnect from broker and stop the loop
        self.disconnect_from_broker()
        self.client.loop_stop()

    @Slot()
    def disconnect_from_broker(self):
        if self.client.is_connected():
            self.state = ConnectionStatus.DISCONNECTING
            self.client.disconnect()

    @Slot()
    def publish(self):
        # check rc, check for ValueError to ensure valid publish
        pass

    @Slot()
    def subscribe(self):
        pass

    def on_connect(self, client, userdata, flags, rc):
        if rc == ConnAck.CONNECTION_SUCCESSFUL:
            # 0: successful
            self.state = ConnectionStatus.CONNECTED
            self.connected.emit()
            # reset reconnection attempts
            self.reconnect_attempts = 0
        else:
            # 1: incorrect protocol version
            # 2: invalid client identifier
            # 3: server unavailable
            # 4: bad username or password
            # 5: not authorised
            conn_err = enum_name_to_str(ConnAck(rc).name)
            self.state = ConnectionStatus.CONNECTION_ERROR
            self.connection_error.emit(conn_err)

            # disable connection
            self.enabled = False

    def on_disconnect(self, client, userdata, rc):
        # rc != 0 is an unexpected disconnection
        self.state = ConnectionStatus.DISCONNECTED
        self.disconnected.emit(rc)

    def on_message(self, client, userdata, msg):
        pass

    def on_publish(self, client, userdata, result):
        pass

    def on_subscribe(self, client, userdata, mid, granted_qos):
        pass

    def __del__(self):
        self.client.disconnect()
