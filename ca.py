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
from PySide2.QtCore import QTimer, Slot, QThread
import keyboard
import mouse
from PIL import ImageGrab
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
from mqtt import Mqtt, ConnectionStatus


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
        #self.client = None
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
        print("event fired")
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
        mqtt.client.publish(HA_TOPIC + self.computer_name + "/config",
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


@Slot()
def mqtt_connecting():
    print("MQTT connecting...")


@Slot()
def mqtt_connected():
    notify("MQTT Connection",
           f"Connected to MQTT broker @ {mqtt.host}:{mqtt.port}")

    # publish device configuration to home assistant
    ca.publish_ha_config()

    # publish online status
    mqtt.client.publish(ca.status_topic, "online")
    mqtt.client.publish(ca.state_topic, ca.state.name.title())

    # subscribe to cmd topic
    result = mqtt.client.subscribe(ca.subscribe_topic, 1)
    if result[0] != 0:
        notify("No Commands",
               "Could not subscribe, no command function available")


@Slot()
def mqtt_connection_error(err):
    print(f"An error occurred:{err}")


@Slot()
def mqtt_disconnected(rc):
    if rc == 0:
        print("Disconnected")
    else:
        print("Unexpected disconnection...")


@Slot()
def mqtt_reconnecting(reconnect_attempt):
    print(f"reconnecting...{reconnect_attempt} time(s)")


@Slot()
def mqtt_reconnect_failure():
    print("Cannot reconnect...please check settings")


def do_update():
    if mqtt.state != ConnectionStatus.CONNECTED:
        return
    print("running loop...")
    if ca.can_trigger():
        print("triggered...")
        ca.update_previous_time()
        if ca.state != Status.ACTIVE:
            ca.state = Status.ACTIVE
            mqtt.client.publish(ca.state_topic, ca.state.name.title())

        window_title = get_window_title()
        current_window = json.dumps(window_title)

        print(f"current window: {current_window}")

        mqtt.client.publish(ca.attribute_topic, '{"Last Active At":"' +
                            ca.last_time_used.strftime("%d/%m/%Y %H:%M:%S") +
                            '","Current Window":' + current_window + '}')

        # TODO: check have valid screenshot else send screen grab error image

        image = screenshot()
        if image is not None:
            mqtt.client.publish(ca.screenshot_topic, image)
    elif ca.state == Status.ACTIVE and ca.is_idle():
        ca.state = Status.ONLINE
        mqtt.client.publish(ca.state_topic, ca.state.name.title())


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
    # update broker details
    host = dialog.mqtt_host.text()
    port = dialog.mqtt_port.text()
    username = dialog.mqtt_username.text()
    password = dialog.mqtt_password.text()


@Slot()
def message_clicked():
    logging.debug("Message clicked")


@Slot()
def menu_item_clicked(action):
    menu_item = action.iconText()
    if menu_item == "Settings":
        dialog.show()
    elif menu_item == "Exit":
        # publish offline status if connected
        if mqtt.state == ConnectionStatus.CONNECTED:

            ca.state = Status.OFFLINE
            mqtt_message_info = mqtt.client.publish(
                ca.status_topic, ca.state.name.lower())
            mqtt_message_info.wait_for_publish()
            print(f"MQTTMessageInfo = {mqtt_message_info}")
            print(f"Published: {mqtt_message_info.is_published()}")

        mqtt.enabled = False
        mqtt_thread.quit()
        mqtt_thread.wait()
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

    # create an instance of the ComputerAssistant class with the computer's name
    ca = ComputerAssistant(uname().node)

    # create and configure the mqtt client
    mqtt = Mqtt(APP_NAME)

    mqtt.host = settings.mqtt_host
    mqtt.port = int(settings.mqtt_port)
    mqtt.client.username_pw_set(settings.mqtt_username, settings.mqtt_password)

    # connect signals to slots
    mqtt.connecting.connect(mqtt_connecting)
    mqtt.connected.connect(mqtt_connected)
    mqtt.connection_error.connect(mqtt_connection_error)
    mqtt.disconnected.connect(mqtt_disconnected)
    mqtt.reconnecting.connect(mqtt_reconnecting)
    mqtt.reconnect_failure.connect(mqtt_reconnect_failure)

    # add on message callback for screenshot command
    # mqtt.client.message_callback_add(
    #     f'{ca.cmd_topic}/screenshot', ca.on_cmd_screenshot)

    # add on message call back for notify command
    # mqtt.client.message_callback_add(f'{ca.cmd_topic}/notify', on_cmd_notify)

    # set the LWT, so if disconnected abruptly the state is set to Offline
    mqtt.client.will_set(ca.state_topic, Status.OFFLINE.name.title(),
                         qos=1, retain=False)

    # create a thread for mqtt
    mqtt_thread = QThread()
    # connect signals to slots
    mqtt_thread.finished.connect(mqtt.deleteLater)
    mqtt_thread.started.connect(mqtt.connect_to_broker)
    # move mqtt process to new thread and start
    mqtt.moveToThread(mqtt_thread)
    mqtt_thread.start()

    frequency = QTimer()
    frequency.timeout.connect(do_update)
    frequency.start(ca.freq * 1000)

    sys.exit(app.exec_())
