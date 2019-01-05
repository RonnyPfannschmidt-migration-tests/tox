"""A minimal non-colored version of https://pypi.org/project/halo, to track list progress"""
from __future__ import absolute_import, unicode_literals

import os
import sys
import threading
import time
from datetime import datetime
from threading import RLock

threads = []

if os.name == "nt":
    import ctypes

    class _CursorInfo(ctypes.Structure):
        _fields_ = [("size", ctypes.c_int), ("visible", ctypes.c_byte)]


class Spinner(object):
    CLEAR_LINE = "\033[K"
    refresh_rate = 0.1
    max_width = 120
    frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, enabled=True):
        self._lock = RLock()
        self._envs = dict()
        self._frame_index = 0
        self.enabled = enabled
        self.stream = sys.stdout

    def add(self, name):
        self._envs[name] = datetime.now()

    def clear(self):
        if self.enabled:
            with self._lock:
                self.stream.write("\r")
                self.stream.write(self.CLEAR_LINE)

    def render(self):
        while not self._stop_spinner.is_set():
            self.render_frame()
            time.sleep(self.refresh_rate)
        return self

    def render_frame(self):
        if self.enabled:
            with self._lock:
                self.clear()
                self.stream.write("\r{}".format(self.frame()))

    def frame(self):
        frame = self.frames[self._frame_index]
        self._frame_index += 1
        self._frame_index = self._frame_index % len(self.frames)
        text_frame = "[{}] {}".format(len(self._envs), " | ".join(self._envs))
        if len(text_frame) > self.max_width - 1:
            text_frame = "{}...".format(text_frame[: self.max_width - 1 - 3])
        return "{} {}".format(*[(frame, text_frame)][0])

    def __enter__(self):
        if self.enabled:
            self.disable_cursor()

        self._stop_spinner = threading.Event()
        self._spinner_thread = threading.Thread(target=self.render)
        self._spinner_thread.setDaemon(True)
        self._spinner_id = self._spinner_thread.name
        self._spinner_thread.start()
        return self

    def succeed(self, key):
        self.finalize(key, "✔ OK")

    def fail(self, key):
        self.finalize(key, "✖ FAIL")

    def skip(self, key):
        self.finalize(key, "⚠ SKIP")

    def finalize(self, key, status):
        with self._lock:
            start_at = self._envs[key]
            del self._envs[key]
            if self.enabled:
                self.clear()
            self.stream.write(
                "{} {} in {}{}".format(
                    status, key, td_human_readable(datetime.now() - start_at), os.linesep
                )
            )
            if not self._envs:
                self.__exit__(None, None, None)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if not self._stop_spinner.is_set():
            if self._spinner_thread:
                self._stop_spinner.set()
                self._spinner_thread.join()

            self._frame_index = 0
            self._spinner_id = None
            if self.enabled:
                self.clear()
                self.enable_cursor()

        return self

    def disable_cursor(self):
        if self.stream.isatty():
            if os.name == "nt":
                ci = _CursorInfo()
                handle = ctypes.windll.kernel32.GetStdHandle(-11)
                ctypes.windll.kernel32.GetConsoleCursorInfo(handle, ctypes.byref(ci))
                ci.visible = False
                ctypes.windll.kernel32.SetConsoleCursorInfo(handle, ctypes.byref(ci))
            elif os.name == "posix":
                self.stream.write("\033[?25l")
                self.stream.flush()

    def enable_cursor(self):
        if self.stream.isatty():
            if os.name == "nt":
                ci = _CursorInfo()
                handle = ctypes.windll.kernel32.GetStdHandle(-11)
                ctypes.windll.kernel32.GetConsoleCursorInfo(handle, ctypes.byref(ci))
                ci.visible = True
                ctypes.windll.kernel32.SetConsoleCursorInfo(handle, ctypes.byref(ci))
            elif os.name == "posix":
                self.stream.write("\033[?25h")
                self.stream.flush()


def td_human_readable(delta):
    seconds = int(delta.total_seconds())
    periods = [
        ("year", 60 * 60 * 24 * 365),
        ("month", 60 * 60 * 24 * 30),
        ("day", 60 * 60 * 24),
        ("hour", 60 * 60),
        ("minute", 60),
        ("second", 1),
    ]

    texts = []
    for period_name, period_seconds in periods:
        if seconds > period_seconds or period_seconds == 1:
            period_value, seconds = divmod(seconds, period_seconds)
            if period_name == "second":
                ms = delta.total_seconds() - int(delta.total_seconds())
                period_value += round(ms, 3)
            has_s = "s" if period_value > 1 else ""
            texts.append("{} {}{}".format(period_value, period_name, has_s))
    return ", ".join(texts)
