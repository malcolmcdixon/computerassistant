# Computer Assistant ![Current Version](https://img.shields.io/badge/version-0.1.0-blue.svg) ![Language](https://img.shields.io/badge/Python-3.8.8-blue)

## Introduction

This project integrates into [![Home Assistant Logo](https://img.shields.io/static/v1?label=&message=Home%20Assistant&color=blue&logo=home-assistant)](https://www.home-assistant.io/) automatically using ![Mqtt Logo](https://img.shields.io/static/v1?label=&message=%20&color=blueviolet&logo=eclipse-mosquitto) **MQTT Discovery** to provide an entity to show whether your computer (Windows only) is Online, Active or Offline.
You can add an **MQTT Camera** entity by updating your _config.yaml_ file, so that the currently active window is displayed in your Lovelace UI.
Commands can be sent via ![Mqtt Logo](https://img.shields.io/static/v1?label=&message=MQTT&color=blueviolet&logo=eclipse-mosquitto) to retrieve a current snapshot of the active window or to send a notification that will pop up using the Windows Notification system.

---
