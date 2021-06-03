#!/usr/bin/env python3

# constants.py
# written by m.c.dixon 2020
# Constants used in computer assistant

import os
import sys
from enum import Enum, unique


# Device status
@unique
class Status(Enum):
    OFFLINE = 0
    ONLINE = 1
    ACTIVE = 2


# Application Name
APP_NAME = "Computer Assistant"
TOPIC_APP_NAME = (APP_NAME.lower()).replace(" ", "-")

# MQTT Topics
HA_TOPIC = f"homeassistant/sensor/{TOPIC_APP_NAME}/"
BASE_TOPIC = f"{TOPIC_APP_NAME}/sensor/"

MQTT_TIMEOUT = 30

# Initial settings
DEFAULT_SETTINGS = """{
                        "mqtt_host": "",
                        "mqtt_port": 1883,
                        "mqtt_username": "",
                        "mqtt_password": ""
                      }"""

# RESOURCES
# Resource Base Path
SETTINGS_PATH = os.getcwd()
RESOURCE_BASE_PATH = getattr(sys, '_MEIPASS', SETTINGS_PATH)

# ICONS
# Computer Assistant Icon
CA_ICON = f"{RESOURCE_BASE_PATH}/images/computer-assistant-icon.png"
CA_WARNING_ICON = f"{RESOURCE_BASE_PATH}/images/computer-assistant-icon-warning.png"
CA_CRITICAL_ICON = f"{RESOURCE_BASE_PATH}/images/computer-assistant-icon-critical.png"
CA_MQTT_ICON = f"{RESOURCE_BASE_PATH}/images/mqtt_icon_64x64.png"
CA_SAVE_ICON = f"{RESOURCE_BASE_PATH}/images/save_blue_128x128.png"
CA_CLOSE_ICON = f"{RESOURCE_BASE_PATH}/images/close_blue_128x128.png"
CA_SETTINGS_ICON = f"{RESOURCE_BASE_PATH}/images/settings_blue_128x128.png"

# FILES
# Settings file
CA_SETTINGS = f"{SETTINGS_PATH}/settings.json"
