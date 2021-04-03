#!/usr/bin/env python3

# mqtt.py
# written by m.c.dixon 2020
# classes for working with paho mqtt library


import time
from enum import Enum, unique
import paho.mqtt.client as mqtt
from PySide2.QtCore import Signal, Slot


@unique
class Status(Enum):
    DISCONNECTED = 0
    CONNECTING = 1
    CONNECTED = 2
    DISCONNECTING = 3
    RECONNECTING = 4
    CONNECTION_ERROR = 5


MQTT_TIMEOUT = 30


class MQTTClient:
    disconnected = Signal()
    username_pw_set = Signal()
    connection_error = Signal()
    connected = Signal()

    def __init__(self, client_id="", clean=True):
        self.client_id = client_id
        self.clean = clean
        self.reinitialise()
        self.client = mqtt.Client(self.client_id, self.clean)
        self.state = Status.DISCONNECTED
        self.host = ""
        self.port = 1883
        # connect callbacks
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        self.client.on_subscribe = self.on_subscribe
        self.client.on_disconnect = self.on_disconnect

    def reinitialise(self):
        self.client.reinitialise(self.client_id, self.clean)
        self.state = Status.DISCONNECTED
        self.disconnected.emit()

    @Slot
    def username_pw_set(self, username, password=None):
        self.client.username_pw_set(username, password)
        self.username_pw_set.emit()

    def will_set(self, topic, payload=None, qos=0, retain=False):
        self.client.will_set(topic, payload, qos, retain)

    @Slot
    def connect(self, host, port: int = 1883):
        # connect to the MQTT broker
        self.host = host
        self.port = port
        self.client.loop_start()
        try:
            self.client.connect(self.host, self.port)
            self.state = Status.CONNECTING
            # wait for successful connection
            waiting = 0
            while not Status.CONNECTED:
                time.sleep(1)
                waiting += 1
                if waiting == MQTT_TIMEOUT:
                    raise TimeoutError
        except (ConnectionRefusedError, ValueError, TimeoutError):
            self.client.loop_stop()
            self.state = Status.CONNECTION_ERROR
            self.connection_error.emit()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            # 0: successful
            self.state = Status.CONNECTED
            self.connected.emit()
        else:
            # 1: incorrect protocol version
            # 2: invalid client identifier
            # 3: server unavailable
            # 4: bad username or password
            # 5: not authorised
            self.state = Status.CONNECTION_ERROR
            self.connection_error.emit()

    def disconnect(self):
        self.client.disconnect()
        self.state = Status.DISCONNECTING

    def on_disconnect(self, client, userdata, rc):
        self.client.loop_stop()
        self.state = Status.DISCONNECTED
        self.disconnected.emit()

    def on_message(self, client, userdata, msg):
        # print("Message received:", msg.payload)
        pass

    def publish(self):
        pass

    def on_publish(self, client, userdata, result):
        pass

    def subscribe(self):
        pass

    def on_subscribe(self, client, userdata, mid, granted_qos):
        pass
