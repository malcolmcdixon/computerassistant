#!/usr/bin/env python3

# settings.py
# written by Malcolm Dixon 2020
# classes for storing settings and settings dialog

import ipaddress
import json
from PySide2.QtWidgets import QDialog, QWidget, QLineEdit, QFormLayout,\
    QTabWidget, QVBoxLayout, QDialogButtonBox, QSpinBox, QLabel

from PySide2.QtGui import QIcon, QIntValidator
from PySide2.QtCore import Qt, QSize

from constants import (
    CA_MQTT_ICON,
    CA_SAVE_ICON,
    CA_CLOSE_ICON,
    CA_TIMER_ICON)


class SettingsDialog(QDialog):
    def __init__(self, app_name, logo_filename, settings):
        super().__init__()
        # form is dirty property
        self._dirty = False
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
        self.mqtt_username.textChanged.connect(self.dirty_form)
        self.mqtt_password = QLineEdit()
        self.mqtt_password.setEchoMode(QLineEdit.Password)
        self.mqtt_password.textChanged.connect(self.dirty_form)

        # create form layout
        form_layout = QFormLayout()
        form_layout.addRow("Broker &Address", self.mqtt_host)
        form_layout.addRow("Broker &Port", self.mqtt_port)
        form_layout.addRow("&Username", self.mqtt_username)
        form_layout.addRow("Pass&word", self.mqtt_password)

        # create tab
        self.tab = QTabWidget()

        # create MQTT settings page
        tab_page = QWidget()
        tab_page.setLayout(form_layout)
        self.tab.addTab(tab_page, QIcon(CA_MQTT_ICON), "&MQTT")

        # create Timings settings page
        self.frequency = QSpinBox()
        self.frequency.setMinimum(5)
        self.frequency.setMaximum(3600)
        self.frequency.setSingleStep(5)
        self.frequency.valueChanged.connect(self.dirty_form)
        self.active_timeout = QSpinBox()
        self.active_timeout.setMinimum(30)
        self.active_timeout.setMaximum(3600)
        self.active_timeout.setSingleStep(5)
        self.active_timeout.valueChanged.connect(self.dirty_form)
        self.mqtt_timeout = QSpinBox()
        self.mqtt_timeout.setMinimum(5)
        self.mqtt_timeout.setMaximum(600)
        self.mqtt_timeout.setSingleStep(5)
        self.mqtt_timeout.valueChanged.connect(self.dirty_form)

        form_layout = QFormLayout()
        form_layout.addRow(QLabel("All timings are in seconds"))
        form_layout.addRow("Update &Frequency (5 - 3600)", self.frequency)
        form_layout.addRow("Active &Status Timeout (30 - 3600)",
                           self.active_timeout)
        form_layout.addRow(
            "MQTT &Connection Timeout (5 - 600)", self.mqtt_timeout)

        tab_page = QWidget()
        tab_page.setLayout(form_layout)
        self.tab.addTab(tab_page, QIcon(CA_TIMER_ICON), "&Timings")

        # create button box
        button_box = QDialogButtonBox(
            QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        self.save_button = button_box.buttons()[0]

        self.save_button.setIcon(QIcon(CA_SAVE_ICON))
        self.save_button.setIconSize(QSize(32, 32))
        self.save_button.setEnabled(False)
        cancel_button = button_box.buttons()[1]
        cancel_button.setIcon(QIcon(CA_CLOSE_ICON))
        cancel_button.setIconSize(QSize(32, 32))

        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        # create main dialog layout
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tab)
        main_layout.addWidget(button_box)
        self.setLayout(main_layout)

    @property
    def dirty(self):
        return self._dirty

    @dirty.setter
    def dirty(self, value):
        self._dirty = value
        self.save_button.setEnabled(value)

    def show(self):
        # load mqtt settings into dialog
        self.mqtt_host.setText(str(self.settings.mqtt_host))
        self.mqtt_port.setText(str(self.settings.mqtt_port))
        self.mqtt_username.setText(str(self.settings.mqtt_username))
        self.mqtt_password.setText(str(self.settings.mqtt_password))
        # load timing settings into dialog
        self.frequency.setValue(self.settings.frequency)
        self.active_timeout.setValue(self.settings.active_timeout)
        self.mqtt_timeout.setValue(self.settings.mqtt_timeout)
        # form not dirty when loaded
        self.dirty = False
        super().show()

    def accept(self):
        # save settings
        self._dirty = False
        self.settings.mqtt_host = self.mqtt_host.text()
        self.settings.mqtt_port = self.mqtt_port.text()
        self.settings.mqtt_username = self.mqtt_username.text()
        self.settings.mqtt_password = self.mqtt_password.text()
        self.settings.frequency = self.frequency.value()
        self.settings.active_timeout = self.active_timeout.value()
        self.settings.mqtt_timeout = self.mqtt_timeout.value()
        self.settings.save()
        super().accept()

    def mqtt_host_text_changed(self, text):
        try:
            # test if valid IP address
            ip_address = ipaddress.ip_address(text)
            colour = "#C4DF9B"
            self.dirty_form()
        except ValueError:
            colour = "#F6989D"
        finally:
            self.mqtt_host.setStyleSheet(
                f"QLineEdit {{ background-color: {colour}}}")

    def mqtt_port_text_changed(self, text):
        if self.mqtt_port.validator().validate(text, 0)[0] == QIntValidator.Acceptable:
            colour = "#C4DF9B"
            self.dirty_form()
        else:
            colour = "#F6989D"
        self.mqtt_port.setStyleSheet(
            f"QLineEdit {{ background-color: {colour}}}")

    def dirty_form(self):
        self.dirty = True


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
            for key in self._dict.keys():
                self._dict[key] = getattr(self, key)
            json.dump(self._dict, open(self._settings_file, 'w'))

    @property
    def loaded(self):
        return bool(self._dict)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.save()
