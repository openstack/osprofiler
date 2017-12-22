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

import datetime
import logging

import six.moves.urllib.parse as urlparse

from osprofiler import _utils

LOG = logging.getLogger(__name__)


def get_driver(connection_string, *args, **kwargs):
    """Create driver's instance according to specified connection string"""
    # NOTE(ayelistratov) Backward compatibility with old Messaging notation
    # Remove after patching all OS services
    # NOTE(ishakhat) Raise exception when ParsedResult.scheme is empty
    if "://" not in connection_string:
        connection_string += "://"

    parsed_connection = urlparse.urlparse(connection_string)
    LOG.debug("String %s looks like a connection string, trying it.",
              connection_string)

    backend = parsed_connection.scheme
    for driver in _utils.itersubclasses(Driver):
        if backend == driver.get_name():
            return driver(connection_string, *args, **kwargs)

    raise ValueError("Driver not found for connection string: "
                     "%s" % connection_string)


class Driver(object):
    """Base Driver class.

    This class provides protected common methods that
    do not rely on a specific storage backend. Public methods notify() and/or
    get_report(), which require using storage backend API, must be overridden
    and implemented by any class derived from this class.
    """

    default_trace_fields = {"base_id", "timestamp"}

    def __init__(self, connection_str, project=None, service=None, host=None,
                 **kwargs):
        self.connection_str = connection_str
        self.project = project
        self.service = service
        self.host = host
        self.result = {}
        self.started_at = None
        self.finished_at = None
        # Last trace started time
        self.last_started_at = None

        profiler_config = kwargs.get("conf", {}).get("profiler", {})
        if hasattr(profiler_config, "filter_error_trace"):
            self.filter_error_trace = profiler_config.filter_error_trace
        else:
            self.filter_error_trace = False

    def notify(self, info, **kwargs):
        """This method will be called on each notifier.notify() call.

        To add new drivers you should, create new subclass of this class and
        implement notify method.

        :param info:  Contains information about trace element.
                      In payload dict there are always 3 ids:
                      "base_id" - uuid that is common for all notifications
                                  related to one trace. Used to simplify
                                  retrieving of all trace elements from
                                  the backend.
                      "parent_id" - uuid of parent element in trace
                      "trace_id" - uuid of current element in trace

                      With parent_id and trace_id it's quite simple to build
                      tree of trace elements, which simplify analyze of trace.

        """
        raise NotImplementedError("{0}: This method is either not supported "
                                  "or has to be overridden".format(
                                      self.get_name()))

    def get_report(self, base_id):
        """Forms and returns report composed from the stored notifications.

        :param base_id: Base id of trace elements.
        """
        raise NotImplementedError("{0}: This method is either not supported "
                                  "or has to be overridden".format(
                                      self.get_name()))

    @classmethod
    def get_name(cls):
        """Returns backend specific name for the driver."""
        return cls.__name__

    def list_traces(self, fields=None):
        """Query all traces from the storage.

        :param fields: Set of trace fields to return. Defaults to 'base_id'
               and 'timestamp'
        :return List of traces, where each trace is a dictionary containing
                at least `base_id` and `timestamp`.
        """
        raise NotImplementedError("{0}: This method is either not supported "
                                  "or has to be overridden".format(
                                      self.get_name()))

    def list_error_traces(self):
        """Query all error traces from the storage.

        :return List of traces, where each trace is a dictionary containing
                `base_id` and `timestamp`.
        """
        raise NotImplementedError("{0}: This method is either not supported "
                                  "or has to be overridden".format(
                                      self.get_name()))

    @staticmethod
    def _build_tree(nodes):
        """Builds the tree (forest) data structure based on the list of nodes.

       Tree building works in O(n*log(n)).

       :param nodes: dict of nodes, where each node is a dictionary with fields
                     "parent_id", "trace_id", "info"
       :returns: list of top level ("root") nodes in form of dictionaries,
                 each containing the "info" and "children" fields, where
                 "children" is the list of child nodes ("children" will be
                 empty for leafs)
       """

        tree = []

        for trace_id in nodes:
            node = nodes[trace_id]
            node.setdefault("children", [])
            parent_id = node["parent_id"]
            if parent_id in nodes:
                nodes[parent_id].setdefault("children", [])
                nodes[parent_id]["children"].append(node)
            else:
                tree.append(node)  # no parent => top-level node

        for trace_id in nodes:
            nodes[trace_id]["children"].sort(
                key=lambda x: x["info"]["started"])

        return sorted(tree, key=lambda x: x["info"]["started"])

    def _append_results(self, trace_id, parent_id, name, project, service,
                        host, timestamp, raw_payload=None):
        """Appends the notification to the dictionary of notifications.

        :param trace_id: UUID of current trace point
        :param parent_id: UUID of parent trace point
        :param name: name of operation
        :param project: project name
        :param service: service name
        :param host: host name or FQDN
        :param timestamp: Unicode-style timestamp matching the pattern
                          "%Y-%m-%dT%H:%M:%S.%f" , e.g. 2016-04-18T17:42:10.77
        :param raw_payload: raw notification without any filtering, with all
                            fields included
        """
        timestamp = datetime.datetime.strptime(timestamp,
                                               "%Y-%m-%dT%H:%M:%S.%f")
        if trace_id not in self.result:
            self.result[trace_id] = {
                "info": {
                    "name": name.split("-")[0],
                    "project": project,
                    "service": service,
                    "host": host,
                },
                "trace_id": trace_id,
                "parent_id": parent_id,
            }

        self.result[trace_id]["info"]["meta.raw_payload.%s"
                                      % name] = raw_payload

        if name.endswith("stop"):
            self.result[trace_id]["info"]["finished"] = timestamp
            self.result[trace_id]["info"]["exception"] = "None"
            if raw_payload and "info" in raw_payload:
                exc = raw_payload["info"].get("etype", "None")
                self.result[trace_id]["info"]["exception"] = exc
        else:
            self.result[trace_id]["info"]["started"] = timestamp
            if not self.last_started_at or self.last_started_at < timestamp:
                self.last_started_at = timestamp

        if not self.started_at or self.started_at > timestamp:
            self.started_at = timestamp

        if not self.finished_at or self.finished_at < timestamp:
            self.finished_at = timestamp

    def _parse_results(self):
        """Parses Driver's notifications placed by _append_results() .

        :returns: full profiling report
        """

        def msec(dt):
            # NOTE(boris-42): Unfortunately this is the simplest way that works
            # in py26 and py27
            microsec = (dt.microseconds + (dt.seconds + dt.days * 24 * 3600) *
                        1e6)
            return int(microsec / 1000.0)

        stats = {}

        for r in self.result.values():
            # NOTE(boris-42): We are not able to guarantee that the backend
            # consumed all messages => so we should at make duration 0ms.

            if "started" not in r["info"]:
                r["info"]["started"] = r["info"]["finished"]
            if "finished" not in r["info"]:
                r["info"]["finished"] = r["info"]["started"]

            op_type = r["info"]["name"]
            op_started = msec(r["info"]["started"] - self.started_at)
            op_finished = msec(r["info"]["finished"] -
                               self.started_at)
            duration = op_finished - op_started

            r["info"]["started"] = op_started
            r["info"]["finished"] = op_finished

            if op_type not in stats:
                stats[op_type] = {
                    "count": 1,
                    "duration": duration
                    }
            else:
                stats[op_type]["count"] += 1
                stats[op_type]["duration"] += duration

        return {
            "info": {
                "name": "total",
                "started": 0,
                "finished": msec(self.finished_at -
                                 self.started_at) if self.started_at else None,
                "last_trace_started": msec(
                    self.last_started_at - self.started_at
                ) if self.started_at else None
            },
            "children": self._build_tree(self.result),
            "stats": stats
        }
