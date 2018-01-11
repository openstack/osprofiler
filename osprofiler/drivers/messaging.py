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

import functools
import signal
import time

from oslo_utils import importutils

from osprofiler.drivers import base


class Messaging(base.Driver):
    def __init__(self, connection_str, project=None, service=None, host=None,
                 context=None, conf=None, transport_url=None,
                 idle_timeout=1, **kwargs):
        """Driver that uses messaging as transport for notifications

        :param connection_str: OSProfiler driver connection string,
               equals to messaging://
        :param project: project name that will be included into notification
        :param service: service name that will be included into notification
        :param host: host name that will be included into notification
        :param context: oslo.messaging context
        :param conf: oslo.config CONF object
        :param transport_url: oslo.messaging transport, e.g.
               rabbit://rabbit:password@devstack:5672/
        :param idle_timeout: how long to wait for new notifications after
               the last one seen in the trace; this parameter is useful to
               collect full trace of asynchronous commands, e.g. when user
               runs `osprofiler` right after `openstack server create`
        :param kwargs: black hole for any other parameters
        """

        self.oslo_messaging = importutils.try_import("oslo_messaging")
        if not self.oslo_messaging:
            raise ValueError("Oslo.messaging library is required for "
                             "messaging driver")

        super(Messaging, self).__init__(connection_str, project=project,
                                        service=service, host=host)

        self.context = context

        if not conf:
            oslo_config = importutils.try_import("oslo_config")
            if not oslo_config:
                raise ValueError("Oslo.config library is required for "
                                 "messaging driver")
            conf = oslo_config.cfg.CONF

        transport_kwargs = {}
        if transport_url:
            transport_kwargs["url"] = transport_url

        self.transport = self.oslo_messaging.get_notification_transport(
            conf, **transport_kwargs)
        self.client = self.oslo_messaging.Notifier(
            self.transport, publisher_id=self.host, driver="messaging",
            topics=["profiler"], retry=0)

        self.idle_timeout = idle_timeout

    @classmethod
    def get_name(cls):
        return "messaging"

    def notify(self, info, context=None):
        """Send notifications to backend via oslo.messaging notifier API.

        :param info:  Contains information about trace element.
                      In payload dict there are always 3 ids:
                      "base_id" - uuid that is common for all notifications
                                  related to one trace.
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

    def get_report(self, base_id):
        notification_endpoint = NotifyEndpoint(self.oslo_messaging, base_id)
        endpoints = [notification_endpoint]
        targets = [self.oslo_messaging.Target(topic="profiler")]
        server = self.oslo_messaging.notify.get_notification_listener(
            self.transport, targets, endpoints, executor="threading")

        state = dict(running=False)
        sfn = functools.partial(signal_handler, state=state)

        # modify signal handlers to handle interruption gracefully
        old_sigterm_handler = signal.signal(signal.SIGTERM, sfn)
        old_sigint_handler = signal.signal(signal.SIGINT, sfn)

        try:
            server.start()
        except self.oslo_messaging.server.ServerListenError:
            # failed to start the server
            raise
        except SignalExit:
            print("Execution interrupted while trying to connect to "
                  "messaging server. No data was collected.")
            return {}

        # connected to server, now read the data
        try:
            # run until the trace is complete
            state["running"] = True

            while state["running"]:
                last_read_time = notification_endpoint.get_last_read_time()
                wait = self.idle_timeout - (time.time() - last_read_time)
                if wait < 0:
                    state["running"] = False
                else:
                    time.sleep(wait)
        except SignalExit:
            print("Execution interrupted. Terminating")
        finally:
            server.stop()
            server.wait()

        # restore original signal handlers
        signal.signal(signal.SIGTERM, old_sigterm_handler)
        signal.signal(signal.SIGINT, old_sigint_handler)

        events = notification_endpoint.get_messages()

        if not events:
            print("No events are collected for Trace UUID %s. Please note "
                  "that osprofiler has read ALL events from profiler topic, "
                  "but has not found any for specified Trace UUID." % base_id)

        for n in events:
            trace_id = n["trace_id"]
            parent_id = n["parent_id"]
            name = n["name"]
            project = n["project"]
            service = n["service"]
            host = n["info"]["host"]
            timestamp = n["timestamp"]

            self._append_results(trace_id, parent_id, name, project, service,
                                 host, timestamp, n)

        return self._parse_results()


class NotifyEndpoint(object):

    def __init__(self, oslo_messaging, base_id):
        self.received_messages = []
        self.last_read_time = time.time()
        self.filter_rule = oslo_messaging.NotificationFilter(
            payload={"base_id": base_id})

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        self.received_messages.append(payload)
        self.last_read_time = time.time()

    def get_messages(self):
        return self.received_messages

    def get_last_read_time(self):
        return self.last_read_time  # time when the latest event was received


class SignalExit(BaseException):
    pass


def signal_handler(signum, frame, state):
    state["running"] = False
    raise SignalExit()
