#!/usr/bin/env python3

# settings.py
# written by m.c.dixon 2020
# classes for storing settings and settings dialog

from PySide2.QtWidgets import QDialog, QWidget, QLineEdit, QFormLayout,\
    QTabWidget, QVBoxLayout, QDialogButtonBox

from PySide2.QtGui import QIcon, QIntValidator
from PySide2.QtCore import Qt, QSize

import ipaddress
import json


class SettingsDialog(QDialog):
    def __init__(self, app_name, logo_filename, settings):
        super().__init__()
        self.setWindowTitle(f"{app_name} - Settings")
        self.setModal(True)
        self.setFixedSize(400, 300)

        self.settings = settings

        # set icon
        self.setWindowIcon(QIcon(logo_filename))
        # don't show the context help button
        self.setWindowFlag(Qt.WindowContextHelpButtonHint, False)

        # create edit line widgets
        self.mqtt_host = QLineEdit()
        self.mqtt_host.textChanged.connect(self.mqtt_host_text_changed)
        self.mqtt_port = QLineEdit()
        self.mqtt_port.setValidator(QIntValidator(1024, 65535))
        self.mqtt_port.textChanged.connect(self.mqtt_port_text_changed)
        self.mqtt_username = QLineEdit()
        self.mqtt_password = QLineEdit()
        self.mqtt_password.setEchoMode(QLineEdit.Password)

        # create form layout
        form_layout = QFormLayout()
        form_layout.addRow("Broker &Address", self.mqtt_host)
        form_layout.addRow("Broker &Port", self.mqtt_port)
        form_layout.addRow("&Username", self.mqtt_username)
        form_layout.addRow("Pass&word", self.mqtt_password)

        # create tab
        self.tab = QTabWidget()

        # create page
        tab_page = QWidget()
        tab_page.setLayout(form_layout)
        self.tab.addTab(tab_page, QIcon("images\mqtt_icon_64x64.png"), "MQTT")

        # create button box
        self.button_box = \
            QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        save_button = self.button_box.buttons()[0]

        save_button.setIcon(QIcon("images\save_blue_128x128.png"))
        save_button.setIconSize(QSize(32, 32))
        cancel_button = self.button_box.buttons()[1]
        cancel_button.setIcon(QIcon("images\close_blue_128x128.png"))
        cancel_button.setIconSize(QSize(32, 32))

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        # create main dialog layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tab)
        main_layout.addWidget(self.button_box)
        self.setLayout(main_layout)

    def accept(self):
        # save settings
        self.settings.mqtt_host = self.mqtt_host.text()
        self.settings.mqtt_port = self.mqtt_port.text()
        self.settings.mqtt_username = self.mqtt_username.text()
        self.settings.mqtt_password = self.mqtt_password.text()
        self.settings.save()
        super().accept()

    def mqtt_host_text_changed(self, text):
        try:
            ip_address = ipaddress.ip_address(text)
            colour = "#C4DF9B"
        except ValueError:
            colour = "#F6989D"
        finally:
            self.mqtt_host.setStyleSheet(
                f"QLineEdit {{ background-color: {colour}}}")

    def mqtt_port_text_changed(self, text):
        if self.mqtt_port.validator().validate(text, 0)[0] == QIntValidator.Acceptable:
            colour = "#C4DF9B"
        else:
            colour = "#F6989D"
        self.mqtt_port.setStyleSheet(
            f"QLineEdit {{ background-color: {colour}}}")


class JSONSettings:
    def __init__(self, filename, defaults):
        self._settings_file = filename
        self._defaults = defaults
        self._dict = {}
        self.load()

    def load(self):
        try:
            self._dict = json.load(open(self._settings_file))
            self.add_items()
        except FileNotFoundError:
            # create settings from defaults
            self._dict = json.loads(self._defaults)
            self.add_items()
        except json.JSONDecodeError:
            # invalid json - corrupt settings file
            self._dict = {}
            # bubble up exception
            raise

    def add_items(self):
        for key, value in self._dict.items():
            setattr(self, key, value)

    def save(self):
        if self.loaded:
            # update setting values in dictionary from attribute values
            for key, value in self._dict.items():
                self._dict[key] = getattr(self, key)
            json.dump(self._dict, open(self._settings_file, 'w'))

    @property
    def loaded(self):
        return bool(self._dict)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.save()
