# Computer Assistant ![Current Version](https://img.shields.io/badge/version-0.1.0-blue.svg) ![Language](https://img.shields.io/badge/Python-3.8.8-blue) ![Mqtt Logo](https://img.shields.io/static/v1?label=&message=MQTT&color=blueviolet&logo=eclipse-mosquitto)

<p align="center">
  <img src="./images/computer-assistant-icon.png" alt="Computer Assistant Screenshot" height=256px>
</p>

## Introduction

This project integrates into [![Home Assistant Logo](https://img.shields.io/static/v1?label=&message=Home%20Assistant&color=41bdf5&logo=home-assistant&logoColor=white)](https://www.home-assistant.io/) automatically using **MQTT Discovery** to provide an entity to show whether your computer (\*\*\_Windows only**\*) is Online, Active or Offline.  
You can add an **MQTT Camera\*\* entity by updating your \_config.yaml\* file, so the currently active window is displayed in your Lovelace UI.  
Commands can be published via MQTT to retrieve a current snapshot of the active window or to send a notification that will pop up using the Windows Notification system.

<p align="center">
  <img src="./github_images/computer-assistant-snapshot.png" alt="Computer Assistant Screenshot" height=>
</p>

## Installation

The simplest method to get started is to copy computerassistant.exe from [releases](https://github.com/malcolmcdixon/computerassistant/releases) to any folder.  
**Suggestion**: add to the startup folder.

Alternatively, [clone or download](https://docs.github.com/en/github/getting-started-with-github/getting-changes-from-a-remote-repository#cloning-a-repository) the source code, preferably into a [virtual environment](https://docs.python.org/3/library/venv.html) and run  
`$ pip install -r requirements.txt`  
`$ python ca.py`

## Configuration

## How to Use

## Support

## Roadmap

## Author

## License
