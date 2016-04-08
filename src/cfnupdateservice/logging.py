#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

from __future__ import print_function # make print patchable by mock

from datetime import datetime

import json
import syslog


class Level(object):
    """An object denoting the logging level of a logging event and logger."""

    def __init__(self, name, priority):
        self.__name = name
        self.__priority = priority

    @property
    def name(self):
        return self.__name

    @property
    def priority(self):
        return self.__priority


class Levels(object):
    """An enumeration of valid logging levels."""

    TRACE = Level("TRACE", 0)
    DEBUG = Level("DEBUG", 1)
    INFO = Level("INFO", 2)
    WARN = Level("WARN", 3)
    ERROR = Level("ERROR", 4)

    @classmethod
    def get_all(cls):
        return (cls.TRACE, cls.DEBUG, cls.INFO, cls.WARN, cls.ERROR)


class Logger(object):
    """Simple logger implementation with plain/JSON output to stdout and syslog."""

    def __init__(self, name, syslog=False, json=False, level=Levels.INFO):
        self.name = name
        self.syslog = syslog
        self.json = json
        self.level = level


    def get_timestamp(self):
        """Get a UTC timestamp in a standards-compliant format."""
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


    def generate_event(self, level, message):
        """Generate a logging event."""
        return {'level': level.name, 'logger': self.name, 'message': message, 'timestamp': self.get_timestamp()}


    def format(self, event):
        """Format an event into a string for output."""
        if self.json:
            return json.dumps(event)
        else:
            return "%(timestamp)s [%(level)-5s] %(logger)s - %(message)s" % event


    def write(self, text):
        """Write a message to the given output stream."""
        if self.syslog:
            syslog.syslog(text)
        else:
            print(text)


    def emit(self, level, message):
        if level not in Levels.get_all():
            return False # narp

        if not level.priority >= self.level.priority:
            return False # narp

        # create event
        event = self.generate_event(level, message)
        # format event
        message = self.format(event)
        # send message
        self.write(message)

        return True


    def trace(self, message):
        self.emit(Levels.TRACE, message)


    def debug(self, message):
        self.emit(Levels.DEBUG, message)


    def info(self, message):
        self.emit(Levels.INFO, message)


    def warn(self, message):
        self.emit(Levels.WARN, message)


    def error(self, message):
        self.emit(Levels.ERROR, message)
