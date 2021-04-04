# Computer Assistant

[!(https://img.shields.io/github/pipenv/locked/python-version/:user/:repo)]

## Introduction

This Python project integrates into Home Assistant automatically using MQTT discovery to provide an entity to show whether the computer is Online, Active or Offline.
You can add an MQTT camera entity by updating your config.yaml file, so that the currently active window is displayed.
Commands can be sent to retrieve a current snapshot of the active window or to send a notification that will pop up using the Windows Notification system.
