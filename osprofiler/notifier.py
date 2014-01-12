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


class Notifier(object):
    """Base notifier that should be implemented by every service that would
    like to use profiler lib.
    """

    def notify(self, event_type, payload):
        pass


# NOTE(boris-42): By default we will use base Notfier that does nothing.
__notifier = Notifier()


def get_notifier():
    return __notifier


def set_notifier(notifier):
    """This method should be called by service that use profiler with proper
    instance of notfier.
    """
    if not isinstance(notifier, Notifier):
        raise TypeError("notifier should be instance of subclass of "
                        "notfier.Notifer")
    global __notifier
    __notifier = notifier
