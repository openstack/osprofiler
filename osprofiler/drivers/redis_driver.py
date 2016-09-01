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

from oslo_config import cfg
from oslo_serialization import jsonutils
import six.moves.urllib.parse as parser

from osprofiler.drivers import base
from osprofiler import exc


class Redis(base.Driver):
    def __init__(self, connection_str, db=0, project=None,
                 service=None, host=None, **kwargs):
        """Redis driver for OSProfiler."""

        super(Redis, self).__init__(connection_str, project=project,
                                    service=service, host=host)
        try:
            from redis import StrictRedis
        except ImportError:
            raise exc.CommandError(
                "To use this command, you should install "
                "'redis' manually. Use command:\n "
                "'pip install redis'.")

        parsed_url = parser.urlparse(self.connection_str)
        self.db = StrictRedis(host=parsed_url.hostname,
                              port=parsed_url.port,
                              db=db)
        self.namespace = "osprofiler:"

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
        key = self.namespace + data["base_id"] + "_" + data["trace_id"] + "_" + \
            data["timestamp"]
        self.db.set(key, jsonutils.dumps(data))

    def list_traces(self, query="*", fields=[]):
        """Returns array of all base_id fields that match the given criteria

        :param query: string that specifies the query criteria
        :param fields: iterable of strings that specifies the output fields
        """
        for base_field in ["base_id", "timestamp"]:
            if base_field not in fields:
                fields.append(base_field)
        ids = self.db.scan_iter(match=self.namespace + query)
        traces = [jsonutils.loads(self.db.get(i)) for i in ids]
        result = []
        for trace in traces:
            result.append({key: value for key, value in trace.iteritems()
                           if key in fields})
        return result

    def get_report(self, base_id):
        """Retrieves and parses notification from Redis.

        :param base_id: Base id of trace elements.
        """
        for key in self.db.scan_iter(match=self.namespace + base_id + "*"):
            data = self.db.get(key)
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
    def __init__(self, connection_str, db=0, project=None,
                 service=None, host=None, conf=cfg.CONF, **kwargs):
        """Redis driver for OSProfiler."""

        super(RedisSentinel, self).__init__(connection_str, project=project,
                                            service=service, host=host)
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
                            socket_timeout=socket_timeout)
        self.db = sentinel.master_for(self.conf.profiler.sentinel_service_name,
                                      socket_timeout=socket_timeout)

    @classmethod
    def get_name(cls):
        return "redissentinel"
