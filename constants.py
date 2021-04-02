#!/usr/bin/env python3

# constants.py
# written by m.c.dixon 2020
# Constants used in computer assistant

from enum import Enum, unique


# Device status
@unique
class Status(Enum):
    OFFLINE = 0
    ONLINE = 1
    ACTIVE = 2


# Application Name
APP_NAME = "computer-assistant"

# MQTT Topics
HA_TOPIC = f"homeassistant/sensor/{APP_NAME}/"
BASE_TOPIC = f"{APP_NAME}/sensor/"

MQTT_TIMEOUT = 30

# Initial settings
DEFAULT_SETTINGS = """{
                        "mqtt_host": "",
                        "mqtt_port": 1883,
                        "mqtt_username": "",
                        "mqtt_password": ""
                      }"""

# Computer Assistant logo
CA_LOGO = "images/computer-assistant-logo.png"