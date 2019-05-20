# Copyright 2016 Mirantis Inc.
# Copyright 2016 IBM Corporation.
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

from debtcollector import removals

from oslo_config import cfg
from oslo_serialization import jsonutils
import six.moves.urllib.parse as parser

from osprofiler.drivers import base
from osprofiler import exc


class Redis(base.Driver):
    @removals.removed_kwarg("db", message="'db' parameter is deprecated "
                                          "and will be removed in future. "
                                          "Please specify 'db' in "
                                          "'connection_string' instead.")
    def __init__(self, connection_str, db=0, project=None,
                 service=None, host=None, conf=cfg.CONF, **kwargs):
        """Redis driver for OSProfiler."""

        super(Redis, self).__init__(connection_str, project=project,
                                    service=service, host=host,
                                    conf=conf, **kwargs)
        try:
            from redis import StrictRedis
        except ImportError:
            raise exc.CommandError(
                "To use this command, you should install "
                "'redis' manually. Use command:\n "
                "'pip install redis'.")

        # only connection over network is supported with schema
        # redis://[:password]@host[:port][/db]
        self.db = StrictRedis.from_url(self.connection_str)
        self.namespace_opt = "osprofiler_opt:"
        self.namespace = "osprofiler:"  # legacy
        self.namespace_error = "osprofiler_error:"

    @classmethod
    def get_name(cls):
        return "redis"

    def notify(self, info):
        """Send notifications to Redis.

        :param info:  Contains information about trace element.
                      In payload dict there are always 3 ids:
                      "base_id" - uuid that is common for all notifications
                                  related to one trace. Used to simplify
                                  retrieving of all trace elements from
                                  Redis.
                      "parent_id" - uuid of parent element in trace
                      "trace_id" - uuid of current element in trace

                      With parent_id and trace_id it's quite simple to build
                      tree of trace elements, which simplify analyze of trace.

        """
        data = info.copy()
        data["project"] = self.project
        data["service"] = self.service
        key = self.namespace_opt + data["base_id"]
        self.db.lpush(key, jsonutils.dumps(data))

        if (self.filter_error_trace
                and data.get("info", {}).get("etype") is not None):
            self.notify_error_trace(data)

    def notify_error_trace(self, data):
        """Store base_id and timestamp of error trace to a separate key."""
        key = self.namespace_error + data["base_id"]
        value = jsonutils.dumps({
            "base_id": data["base_id"],
            "timestamp": data["timestamp"]
        })
        self.db.set(key, value)

    def list_traces(self, fields=None):
        """Query all traces from the storage.

        :param fields: Set of trace fields to return. Defaults to 'base_id'
               and 'timestamp'
        :return List of traces, where each trace is a dictionary containing
                at least `base_id` and `timestamp`.
        """
        fields = set(fields or self.default_trace_fields)

        # first get legacy events
        result = self._list_traces_legacy(fields)

        # with optimized schema trace events are stored in a list
        ids = self.db.scan_iter(match=self.namespace_opt + "*")
        for i in ids:
            # for each trace query the first event to have a timestamp
            first_event = jsonutils.loads(self.db.lindex(i, 1))
            result.append({key: value for key, value in first_event.items()
                           if key in fields})
        return result

    def _list_traces_legacy(self, fields):
        # With current schema every event is stored under its own unique key
        # To query all traces we first need to get all keys, then
        # get all events, sort them and pick up only the first one
        ids = self.db.scan_iter(match=self.namespace + "*")
        traces = [jsonutils.loads(self.db.get(i)) for i in ids]
        traces.sort(key=lambda x: x["timestamp"])
        seen_ids = set()
        result = []
        for trace in traces:
            if trace["base_id"] not in seen_ids:
                seen_ids.add(trace["base_id"])
                result.append({key: value for key, value in trace.items()
                               if key in fields})
        return result

    def list_error_traces(self):
        """Returns all traces that have error/exception."""
        ids = self.db.scan_iter(match=self.namespace_error + "*")
        traces = [jsonutils.loads(self.db.get(i)) for i in ids]
        traces.sort(key=lambda x: x["timestamp"])
        seen_ids = set()
        result = []
        for trace in traces:
            if trace["base_id"] not in seen_ids:
                seen_ids.add(trace["base_id"])
                result.append(trace)

        return result

    def get_report(self, base_id):
        """Retrieves and parses notification from Redis.

        :param base_id: Base id of trace elements.
        """
        def iterate_events():
            for key in self.db.scan_iter(
                    match=self.namespace + base_id + "*"):  # legacy
                yield self.db.get(key)

            for event in self.db.lrange(self.namespace_opt + base_id, 0, -1):
                yield event

        for data in iterate_events():
            n = jsonutils.loads(data)
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


class RedisSentinel(Redis, base.Driver):
    @removals.removed_kwarg("db", message="'db' parameter is deprecated "
                                          "and will be removed in future. "
                                          "Please specify 'db' in "
                                          "'connection_string' instead.")
    def __init__(self, connection_str, db=0, project=None,
                 service=None, host=None, conf=cfg.CONF, **kwargs):
        """Redis driver for OSProfiler."""

        super(RedisSentinel, self).__init__(connection_str, project=project,
                                            service=service, host=host,
                                            conf=conf, **kwargs)
        try:
            from redis.sentinel import Sentinel
        except ImportError:
            raise exc.CommandError(
                "To use this command, you should install "
                "'redis' manually. Use command:\n "
                "'pip install redis'.")

        self.conf = conf
        socket_timeout = self.conf.profiler.socket_timeout
        parsed_url = parser.urlparse(self.connection_str)
        sentinel = Sentinel([(parsed_url.hostname, int(parsed_url.port))],
                            password=parsed_url.password,
                            socket_timeout=socket_timeout)
        self.db = sentinel.master_for(self.conf.profiler.sentinel_service_name,
                                      socket_timeout=socket_timeout)

    @classmethod
    def get_name(cls):
        return "redissentinel"
