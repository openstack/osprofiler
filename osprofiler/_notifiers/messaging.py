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

from osprofiler._notifiers import base


class Messaging(base.Notifier):

    def __init__(self, messaging, context, transport, project, service, host):
        """Init Messaging notify driver.

        """
        super(Messaging, self).__init__()
        self.messaging = messaging
        self.context = context
        self.project = project
        self.service = service

        self.notifier = messaging.Notifier(
            transport, publisher_id=host, driver="messaging",
            topic="profiler", retry=0)

    def notify(self, info, context=None):
        """Send notifications to Ceilometer via oslo.messaging notifier API.

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

        info["project"] = self.project
        info["service"] = self.service
        self.notifier.info(context or self.context,
                           "profiler.%s" % self.service, info)
