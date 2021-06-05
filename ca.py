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
from PySide2.QtCore import QTimer, Slot, QThread, Signal, QObject
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
    CA_WARNING_ICON,
    CA_CRITICAL_ICON,
    CA_SETTINGS
)

# import constants
from settings import JSONSettings, SettingsDialog
from systray import SystemTrayIcon
from microsoft import windows
from imageprocess import convert
from mqtt import Mqtt, ConnectionStatus


class ComputerAssistant(QObject):
    attempt_reconnect = Signal()

    def __init__(self, computer_name: str):
        super().__init__()
        self._ltu = datetime.datetime.now()
        self._ptu = self._ltu
        # frequency to check for activity and active timeout
        self._freq = 15
        self._active_timeout = 120
        self.timer = QTimer()
        self.freq = 15
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

    @freq.setter
    def freq(self, value):
        self._freq = value
        self.timer.setInterval(value * 1000)

    @property
    def active_timeout(self):
        return self._active_timeout

    @active_timeout.setter
    def active_timeout(self, value):
        self._active_timeout = value

    def can_trigger(self):
        return (self._ltu - self._ptu).seconds > self._freq

    def is_idle(self):
        return (datetime.datetime.now() - self._ltu).seconds >\
            self._active_timeout

    def event_fired(self, event):
        if isinstance(event, mouse.MoveEvent):
            return
        self.update_last_time_used()

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
    tray_icon.tooltip(f"{APP_NAME} - Connecting")


@Slot()
def mqtt_connected():
    tray_icon.tooltip(f"{APP_NAME} - Connected")
    tray_icon.setIcon(QIcon(CA_ICON))
    tray_icon.notify("MQTT Connection",
                     f"Connected to MQTT broker @ {mqtt.host}:{mqtt.port}", tray_icon.MessageIcon.Information)

    # hide reconnect menu action if visible
    tray_icon.contextMenu().actions()[0].setVisible(False)

    # publish device configuration to home assistant
    ca.publish_ha_config()

    # publish online status
    mqtt.client.publish(ca.status_topic, "online")
    mqtt.client.publish(ca.state_topic, ca.state.name.title())

    # subscribe to cmd topic
    result = mqtt.client.subscribe(ca.subscribe_topic, 1)
    if result[0] != 0:
        tray_icon.notify("No Commands",
                         "Could not subscribe, no command function available", tray_icon.MessageIcon.Warning)


@Slot()
def mqtt_connection_error(err):
    tray_icon.tooltip(f"{APP_NAME} - Connection Error")
    tray_icon.setIcon(QIcon(CA_WARNING_ICON))


@Slot()
def mqtt_disconnected(rc):
    if rc == 0:
        tray_icon.tooltip(f"{APP_NAME} - Disconnected")
    else:
        tray_icon.tooltip(f"{APP_NAME} - Disconnected Unexpectedly")
        tray_icon.setIcon(QIcon(CA_WARNING_ICON))
        tray_icon.notify("MQTT Disconnected",
                         "An unexpected disconnection occurred, attempting automatic reconnection", tray_icon.MessageIcon.Warning)


@Slot()
def mqtt_reconnecting(reconnect_attempt):
    tray_icon.tooltip(
        f"{APP_NAME} - Reconnecting...attempt: {reconnect_attempt}")


@Slot()
def mqtt_reconnect_failure():
    # display reconnect menu option
    tray_icon.contextMenu().actions()[0].setVisible(True)

    tray_icon.tooltip(f"{APP_NAME} - Reconnection Failed")
    tray_icon.setIcon(QIcon(CA_CRITICAL_ICON))
    tray_icon.notify("MQTT Connection Error",
                     "Cannot connect to the MQTT broker, reconnection attempts failed.\n Please check your settings and/or the status of your broker service.", tray_icon.MessageIcon.Critical)


def do_update():
    if mqtt.state != ConnectionStatus.CONNECTED:
        return
    if ca.can_trigger():
        ca.update_previous_time()
        if ca.state != Status.ACTIVE:
            ca.state = Status.ACTIVE
            mqtt.client.publish(ca.state_topic, ca.state.name.title())

        window_title = get_window_title()
        current_window = json.dumps(window_title)

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


def on_cmd_notify(client, userdata, msg):
    notification = json.loads(msg.payload)
    tray_icon.notify(
        notification["title"], notification["message"], tray_icon.MessageIcon.Information)


def on_cmd_screenshot(self, client, userdata):
    mqtt.client.publish(ca.screenshot_topic, screenshot())


@Slot()
def dialog_saved():
    # update mqtt connection details
    mqtt_changed = False
    if mqtt.host != settings.mqtt_host:
        mqtt.host = settings.mqtt_host
        mqtt_changed = True
    if mqtt.port != int(settings.mqtt_port):
        mqtt.port = int(settings.mqtt_port)
        mqtt_changed = True
    if mqtt.username != settings.mqtt_username:
        mqtt.username = settings.mqtt_username
        mqtt_changed = True
    if mqtt.password != settings.mqtt_password:
        mqtt.password = settings.mqtt_password
        mqtt_changed = True
    mqtt.timeout = settings.mqtt_timeout
    # update timings
    ca.freq = settings.frequency
    ca.active_timeout = settings.active_timeout

    # reconnect if mqtt details changed
    if mqtt_changed:
        # disable connection
        mqtt.enabled = False
        # emit signal to reconnect to broker with new details
        ca.attempt_reconnect.emit()


@Slot()
def message_clicked():
    # TODO add functionality to allow user-defined action when notification clicked
    pass


@Slot()
def menu_item_clicked(action):
    menu_item = action.iconText()
    if menu_item == "Settings":
        dialog.show()
    elif menu_item == "Reconnect":
        ca.attempt_reconnect.emit()
    elif menu_item == "Exit":
        # publish offline status if connected
        if mqtt.state == ConnectionStatus.CONNECTED:

            ca.state = Status.OFFLINE
            mqtt.client.publish(ca.state_topic, ca.state.name.title())
            mqtt_message_info = mqtt.client.publish(
                ca.status_topic, ca.state.name.lower())
            mqtt_message_info.wait_for_publish()
            #print(f"MQTTMessageInfo = {mqtt_message_info}")
            #print(f"Published: {mqtt_message_info.is_published()}")

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
    tray_icon.tooltip(APP_NAME)
    tray_icon.messageClicked.connect(message_clicked)
    # connect triggered signal of context menu to menu_item_clicked function
    tray_icon.contextMenu().triggered.connect(menu_item_clicked)
    tray_icon.show()

    # load settings.json
    try:
        settings = JSONSettings(CA_SETTINGS, DEFAULT_SETTINGS)
        if not settings.loaded:
            tray_icon.notify("Settings Error",
                             "Unable to load settings even default settings!", tray_icon.MessageIcon.Critical)
    except json.JSONDecodeError:
        tray_icon.notify(
            "Invalid JSON", "The settings file is not valid JSON", tray_icon.MessageIcon.Critical)

    # create settings dialog
    dialog = SettingsDialog(APP_NAME, CA_ICON, settings)
    dialog.accepted.connect(dialog_saved)

    # create an instance of the ComputerAssistant class with the computer's name
    ca = ComputerAssistant(uname().node)
    ca.freq = settings.frequency
    ca.active_timeout = settings.active_timeout

    # create and configure the mqtt client
    mqtt = Mqtt(APP_NAME)

    mqtt.host = settings.mqtt_host
    mqtt.port = int(settings.mqtt_port)
    mqtt.username = settings.mqtt_username
    mqtt.password = settings.mqtt_password
    mqtt.timeout = settings.mqtt_timeout

    # set the LWT, so if disconnected abruptly the state is set to Offline
    mqtt.client.will_set(ca.state_topic, Status.OFFLINE.name.title(),
                         qos=1, retain=False)

    # connect signals to slots
    mqtt.connecting.connect(mqtt_connecting)
    mqtt.connected.connect(mqtt_connected)
    mqtt.connection_error.connect(mqtt_connection_error)
    mqtt.disconnected.connect(mqtt_disconnected)
    mqtt.reconnecting.connect(mqtt_reconnecting)
    mqtt.reconnect_failure.connect(mqtt_reconnect_failure)
    ca.attempt_reconnect.connect(mqtt.reconnect_to_broker)

    # add on message callback for screenshot command
    mqtt.client.message_callback_add(
        f'{ca.cmd_topic}/screenshot', on_cmd_screenshot)

    # add on message call back for notify command
    mqtt.client.message_callback_add(f'{ca.cmd_topic}/notify', on_cmd_notify)

    # create a thread for mqtt
    mqtt_thread = QThread()
    # connect signals to slots
    mqtt_thread.finished.connect(mqtt.deleteLater)
    mqtt_thread.started.connect(mqtt.connect_to_broker)
    # move mqtt process to new thread and start
    mqtt.moveToThread(mqtt_thread)
    mqtt_thread.start()

    ca.timer.timeout.connect(do_update)
    ca.timer.start()

    sys.exit(app.exec_())
