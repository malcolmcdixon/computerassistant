#!/usr/bin/env python3

# ca.py
# written by Malcolm Dixon 2020
# computer assistant is a program that configures a device in home assistant
# so that the HA user can see activity on computers and see a screenshot of
# the last active window. Notifications can be sent to computer assistant
# from home assistant using MQTT.


import time
import datetime
import json
import sys
import logging
from platform import uname
from PySide2.QtWidgets import QApplication
from PySide2.QtGui import QIcon
from PySide2.QtCore import QTimer, QThread, Slot
import keyboard
import mouse
from PIL import ImageGrab
import paho.mqtt.client as mqtt
from psutil import WINDOWS, LINUX

from constants import (
    APP_NAME,
    HA_TOPIC,
    BASE_TOPIC,
    MQTT_TIMEOUT,
    Status,
    DEFAULT_SETTINGS,
    CA_ICON,
    CA_SETTINGS
)
from settings import JSONSettings, SettingsDialog
from systray import SystemTrayIcon
from microsoft import windows
from imageprocess import convert


class ComputerAssistant:
    def __init__(self, computer_name: str):
        self._ltu = datetime.datetime.now()
        self._ptu = self._ltu
        # frequency to check for activity and active timeout
        self._freq = 15
        self._active_timeout = 120
        # get computer name to use as unique id and within mqtt topics
        self.computer_name = computer_name

        # set up mqtt and topics
        self.client = None
        self.base_topic = BASE_TOPIC + self.computer_name
        self.screenshot_topic = self.base_topic + "/screenshot"
        self.status_topic = self.base_topic + "/status"
        self.state_topic = self.base_topic + "/state"
        self.attribute_topic = self.base_topic + "/attributes"
        self.cmd_topic = self.base_topic + "/cmd"
        self.subscribe_topic = self.cmd_topic + "/#"

        # activity state
        self._state = Status.ONLINE

        # valid settings
        self.valid_settings = False

        # set up keyboard and mouse hooks
        keyboard.on_press(self.event_fired)
        mouse.hook(self.event_fired)

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, value: Status):
        self._state = value

    @property
    def last_time_used(self):
        return self._ltu

    def update_last_time_used(self):
        self._ltu = datetime.datetime.now()

    @property
    def previous_time(self):
        return self._ptu

    def update_previous_time(self):
        self._ptu = self._ltu

    @property
    def freq(self):
        return self._freq

    def can_trigger(self):
        return (self._ltu - self._ptu).seconds > self._freq

    def is_idle(self):
        return (datetime.datetime.now() - self._ltu).seconds >\
            self._active_timeout

    def event_fired(self, event):
        if isinstance(event, mouse.MoveEvent):
            return
        self.update_last_time_used()

    def on_cmd_screenshot(self, client, userdata, msg):
        client.publish(self.screenshot_topic, screenshot())

    def publish_ha_config(self):
        # build payload for home assistant system config
        payload = f'{{"availability_topic":"{self.status_topic}",' \
            f'"device": {{' \
            f'"identifiers": "{self.computer_name}",' \
            f'"name": "{self.computer_name}"}},' \
            f'"icon":"mdi:microsoft",' \
            f'"json_attributes_topic":"{self.attribute_topic}",' \
            f'"name":"{self.computer_name}",' \
            f'"payload_available":"online",' \
            f'"payload_not_available":"offline",' \
            f'"qos":"1",' \
            f'"state_topic":"{self.state_topic}",' \
            f'"unique_id":"{self.computer_name}"}}'

        # publish system config for Home Assistant
        # NOTE: send empty payload to delete device
        self.client.publish(HA_TOPIC + self.computer_name + "/config",
                            payload=payload, qos=0, retain=True)


# return active window handle
def get_active_window() -> int:
    if WINDOWS:
        return windows.active_window()
    elif LINUX:
        pass
    else:
        return 0


# return current window title
def get_window_title() -> str:
    if WINDOWS:
        hwnd = windows.active_window()
        return windows.get_window_title(hwnd)
    elif LINUX:
        pass
    else:
        return "Unknown"


def screenshot() -> bytearray:
    # grab a screenshot of the active window
    hwnd = get_active_window()
    rect = windows.get_window_rect(hwnd)
    bbox = (rect.left, rect.top, rect.right, rect.bottom)
    # Windows and OSX only (all_screens=True Windows only)
    img = ImageGrab.grab(bbox, False, all_screens=True)
    return convert.to_byte_array(img)


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        # 0: successful
        client.connected = True
    else:
        # 1: incorrect protocol version
        # 2: invalid client identifier
        # 3: server unavailable
        # 4: bad username or password
        # 5: not authorised
        client.connected = False


def on_disconnect(client, userdata, rc):
    client.connected = False
    client.loop_stop()


def on_message(client, userdata, msg):
    # print("Message received:", msg.payload)
    pass


def on_publish(client, userdata, result):
    # print("publish result:", result)
    pass


def on_subscribe(client, userdata, mid, granted_qos):
    pass


def mqtt_connect(client, broker, port):
    # connect to the MQTT broker
    client.loop_start()
    try:
        client.connected = False
        client.connect(broker, int(port), 60)
        # wait for successful connection
        waiting = 0
        while not client.connected:
            time.sleep(1)
            waiting += 1
            if waiting == MQTT_TIMEOUT:
                print("MQTT connection timeout, cannot connect")
                client.loop_stop()
                sys.exit()
    except ConnectionRefusedError:
        print("MQTT broker refused connection or is not available")
        client.loop_stop()
        sys.exit()
    except ValueError:
        # invalid host
        return
    except TimeoutError:
        notify("MQTT", "A TimeOutError occurred while connecting to broker")


def do_update():
    if not mqttc.connected:
        # disconnected from mqtt broker so connect again
        mqtt_connect(mqttc, broker, port)

    if ca.can_trigger():
        ca.update_previous_time()
        if ca.state != Status.ACTIVE:
            ca.state = Status.ACTIVE
            mqttc.publish(ca.state_topic, ca.state.name.title())

        window_title = get_window_title()
        current_window = json.dumps(window_title)
        mqttc.publish(ca.attribute_topic, '{"Last Active At":"' +
                      ca.last_time_used.strftime("%d/%m/%Y %H:%M:%S") +
                      '","Current Window":' + current_window + '}')
        # TODO: check have valid screenshot else send screen grab error image
        image = screenshot()
        if image is not None:
            mqttc.publish(ca.screenshot_topic, image)
    elif ca.state == Status.ACTIVE and ca.is_idle():
        ca.state = Status.ONLINE
        mqttc.publish(ca.state_topic, ca.state.name.title())


def notify(title, message):
    if tray_icon.supportsMessages():
        # can use QSystemTrayIcon.Information |
        # Critical | Warning | NoIcon for icon
        tray_icon.showMessage(title, message,
                              QIcon(CA_ICON))


def on_cmd_notify(client, userdata, msg):
    notification = json.loads(msg.payload)
    notify(notification["title"], notification["message"])


@Slot()
def dialog_saved():
    logging.debug("Settings just saved")


@Slot()
def message_clicked():
    logging.debug("Message clicked")


@Slot()
def menu_item_clicked(action):
    menu_item = action.iconText()
    if menu_item == "Settings":
        dialog.show()
    elif menu_item == "Exit":
        app.exit()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    # create qt application
    app = QApplication(sys.argv)
    # ensure app does not close when settings window closes
    app.setQuitOnLastWindowClosed(False)

    # create notification area ui
    icon_image = QIcon(CA_ICON)
    tray_icon = SystemTrayIcon(icon_image)
    tray_icon.setToolTip(APP_NAME)
    # tray_icon.exit_menu.connect(clean_up)
    tray_icon.messageClicked.connect(message_clicked)
    # connect triggered signal of context menu to menu_item_clicked function
    tray_icon.contextMenu().triggered.connect(menu_item_clicked)
    tray_icon.show()

    # load settings.json
    try:
        settings = JSONSettings(CA_SETTINGS, DEFAULT_SETTINGS)
        if not settings.loaded:
            notify("Settings Error",
                   "Unable to load settings even default settings!")
    except json.JSONDecodeError:
        notify("Invalid JSON", "The settings file is not valid JSON")

    # create settings dialog
    dialog = SettingsDialog(APP_NAME, CA_ICON, settings)

    # load mqtt settings into dialog
    dialog.mqtt_host.setText(str(settings.mqtt_host))
    dialog.mqtt_port.setText(str(settings.mqtt_port))
    dialog.mqtt_username.setText(str(settings.mqtt_username))
    dialog.mqtt_password.setText(str(settings.mqtt_password))

    dialog.accepted.connect(dialog_saved)

    #tray_icon.open_settings.connect(lambda: dialog.show())

    # get broker details
    broker = settings.mqtt_host
    port = settings.mqtt_port
    username = settings.mqtt_username
    password = settings.mqtt_password
    # TODO if settings not valid then pointless trying to connect
    ca = ComputerAssistant(uname().node)
    # init the mqtt client
    ca.client = mqtt.Client()
    mqttc = ca.client

    mqttc.on_connect = on_connect
    mqttc.on_message = on_message
    mqttc.on_publish = on_publish
    mqttc.on_subscribe = on_subscribe
    mqttc.on_disconnect = on_disconnect
    mqttc.username_pw_set(username, password)
    # set the LWT, so if disconnected abruptly the state is set to Offline
    mqttc.will_set(ca.state_topic, Status.OFFLINE.name.title(),
                   qos=1, retain=False)

    # connect to mqtt broker
    mqtt_connect(mqttc, broker, port)
    notify("MQTT Connection", f"Connected to MQTT broker @ {broker}:{port}")

    # publish device configuration to home assistant
    ca.publish_ha_config()

    # publish online status
    mqttc.publish(ca.status_topic, "online")
    mqttc.publish(ca.state_topic, ca.state.name.title())

    # add on message callback for screenshot command
    mqttc.message_callback_add(
        f'{ca.cmd_topic}/screenshot', ca.on_cmd_screenshot)
    # add on message call back for notify command
    mqttc.message_callback_add(f'{ca.cmd_topic}/notify', on_cmd_notify)
    # subscribe to cmd topic
    result = mqttc.subscribe(ca.subscribe_topic, 1)
    if result[0] != 0:
        notify("No Commands",
               "Could not subscribe, no command function available")

    frequency = QTimer()
    frequency.timeout.connect(do_update)
    frequency.start(ca.freq)

    sys.exit(app.exec_())
