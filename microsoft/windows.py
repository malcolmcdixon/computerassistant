#!/usr/bin/env python3

# windows.py
# written by Malcolm Dixon 2020
# functions for working with MS Windows windows

from ctypes import windll, wintypes, create_unicode_buffer, byref


def active_window() -> int:
    # hwnd can be null/None so need to cater for that, SEND DESKTOP hwnd = 0
    hwnd = windll.user32.GetForegroundWindow()
    return hwnd if type(hwnd) == int else 0


def get_window_title(hwnd: int) -> str:
    user32 = windll.user32
    length = user32.GetWindowTextLengthW(hwnd)
    title_buffer = create_unicode_buffer(length + 1)
    user32.GetWindowTextW(hwnd, title_buffer, length + 1)
    return title_buffer.value


def get_window_rect(hwnd: int) -> wintypes.RECT:
    rect = wintypes.RECT()
    windll.user32.GetWindowRect(hwnd, byref(rect))
    return rect
