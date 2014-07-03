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

from osprofiler import _utils as utils


class Notifier(object):

    def notify(self, info, context=None):
        """This method will be called on each notifier.notify() call.

        To add new drivers you should, create new subclass of this class and
        implement notify method.

        :param info:  Contains information about trace element.
                      In payload dict there are always 3 ids:
                      "base_id" - uuid that is common for all notifications
                                  related to one trace. Used to simplify
                                  retrieving of all trace elements from
                                  Ceilometer.
                      "parent_id" - uuid of parent element in trace
                      "trace_id" - uuid of current element in trace

                      With parent_id and trace_id it's quite simple to build
                      tree of trace elements, which simplify analyze of trace.

        :param context: request context that is mostly used to specify
                        current active user and tenant.
        """

    @staticmethod
    def factory(name, *args, **kwargs):
        for driver in utils.itersubclasses(Notifier):
            if name == driver.__name__:
                return driver(*args, **kwargs).notify

        raise TypeError("There is no driver, with name: %s" % name)
