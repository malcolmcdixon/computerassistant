#!/usr/bin/env python3

# systray.py
# written by m.c.dixon 2020
# class to create a system tray icon for computer assistant

from PySide2.QtWidgets import QApplication, QMenu, QSystemTrayIcon
from PySide2.QtGui import QIcon
from PySide2.QtCore import Signal


class SystemTrayIcon(QSystemTrayIcon):
    open_settings = Signal()
    exit_menu = Signal()
    message_clicked = Signal()

    def __init__(self, icon):
        super().__init__(icon)
        if self.isSystemTrayAvailable():
            # create a menu for system tray icon
            menu = QMenu()
            # add Settings menu option with bold font
            action = menu.addAction("Settings", self.settings)
            action.setIcon(QIcon("images\settings_blue_128x128.png"))
            font = action.font()
            font.setBold(True)
            action.setFont(font)
            # add a menu separator
            menu.addSeparator()
            # add Exit menu option
            action = menu.addAction("Exit", self.exit)
            action.setIcon(QIcon("images\close_blue_128x128.png"))
            # add menu to system tray icon
            self.setContextMenu(menu)

    def settings(self):
        self.open_settings.emit()

    def exit(self):
        self.exit_menu.emit()
