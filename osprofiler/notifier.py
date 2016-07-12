# Copyright 2014 Mirantis Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from osprofiler.drivers import base


def _noop_notifier(info, context=None):
    """Do nothing on notify()."""


# NOTE(boris-42): By default we are using noop notifier.
__notifier = _noop_notifier
__driver_cache = {}


def notify(info):
    """Passes the profiling info to the notifier callable.

    :param info: dictionary with profiling information
    """
    __notifier(info)


def get():
    """Returns notifier callable."""
    return __notifier


def set(notifier):
    """Service that are going to use profiler should set callable notifier.

       Callable notifier is instance of callable object, that accept exactly
       one argument "info". "info" - is dictionary of values that contains
       profiling information.
    """
    global __notifier
    __notifier = notifier


def create(connection_string, *args, **kwargs):
    """Create notifier based on specified plugin_name

    :param connection_string: connection string which specifies the storage
                              driver for notifier
    :param *args: args that will be passed to the driver's __init__ method
    :param **kwargs: kwargs that will be passed to the driver's __init__ method
    :returns: Callable notifier method
    :raises TypeError: In case of invalid name of plugin raises TypeError
    """
    global __driver_cache
    if connection_string not in __driver_cache:
        __driver_cache[connection_string] = base.get_driver(connection_string,
                                                            *args,
                                                            **kwargs).notify
    return __driver_cache[connection_string]
