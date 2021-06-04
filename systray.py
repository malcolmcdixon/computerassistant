#!/usr/bin/env python3

# systray.py
# written by Malcolm Dixon 2020
# class to create a system tray icon for computer assistant

from PySide2.QtWidgets import QMenu, QSystemTrayIcon
from PySide2.QtGui import QIcon

from constants import (
    CA_RECONNECT_ICON,
    CA_SETTINGS_ICON,
    CA_CLOSE_ICON
)


class SystemTrayIcon(QSystemTrayIcon):

    def __init__(self, icon):
        super().__init__(icon)
        if self.isSystemTrayAvailable():
            # create a menu for system tray icon
            menu = QMenu()

            # add Reconnect menu option, only visible once disconnected
            action = menu.addAction("Reconnect")
            action.setIcon(QIcon(CA_RECONNECT_ICON))
            action.setVisible(False)

            # add Settings menu option with bold font
            action = menu.addAction("Settings")
            action.setIcon(QIcon(CA_SETTINGS_ICON))
            font = action.font()
            font.setBold(True)
            action.setFont(font)
            # add a menu separator
            menu.addSeparator()
            # add Exit menu option
            action = menu.addAction("Exit")
            action.setIcon(QIcon(CA_CLOSE_ICON))
            # add menu to system tray icon
            self.setContextMenu(menu)

    def notify(self, title, message, icon):
        if self.supportsMessages():
            # can use QSystemTrayIcon.MessageIcon.Information |
            # Critical | Warning | NoIcon for icon
            self.showMessage(title, message, icon)

    def tooltip(self, tooltip_str):
        self.setToolTip(tooltip_str)
