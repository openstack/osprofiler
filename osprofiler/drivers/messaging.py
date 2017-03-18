# Copyright 2016 Mirantis Inc.
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


class Messaging(base.Driver):
    def __init__(self, connection_str, messaging=None, context=None,
                 transport=None, project=None, service=None,
                 host=None, **kwargs):
        """Driver sending notifications via message queues."""

        super(Messaging, self).__init__(connection_str, project=project,
                                        service=service, host=host)

        self.messaging = messaging
        self.context = context

        self.client = messaging.Notifier(
            transport, publisher_id=self.host, driver="messaging",
            topics=["profiler"], retry=0)

    @classmethod
    def get_name(cls):
        return "messaging"

    def notify(self, info, context=None):
        """Send notifications to backend via oslo.messaging notifier API.

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
        self.client.info(context or self.context,
                         "profiler.%s" % info["service"],
                         info)
