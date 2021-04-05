# Computer Assistant ![Current Version](https://img.shields.io/badge/version-0.1.0-blue.svg) ![Language](https://img.shields.io/badge/Python-3.8.8-blue)

## Introduction

This project integrates into [Home Assistant](https://www.home-assistant.io/) automatically using **MQTT Discovery** to provide an entity to show whether your computer (Windows only) is Online, Active or Offline.
You can add an **MQTT Camera** entity by updating your _config.yaml_ file, so that the currently active window is displayed in your Lovelace UI.
Commands can be sent via ![mqtt logo](https://github.com/malcolmcdixon/computerassistant/blob/master/images/mqtt_icon_64x64.png)MQTT to retrieve a current snapshot of the active window or to send a notification that will pop up using the Windows Notification system.

---
