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

import datetime


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


def _build_tree(nodes):
    """Builds the tree (forest) data structure based on the list of nodes.

   Works in O(n).

   :param nodes: list of nodes, where each node is a dictionary with fields
                 "parent_id", "trace_id", "info"
   :returns: list of top level ("root") nodes in form of dictionaries,
             each containing the "info" and "children" fields, where
             "children" is the list of child nodes ("children" will be
             empty for leafs)
   """

    tree = []

    # 1st pass through nodes - populating the cache with existing nodes
    for trace_id in nodes:
        nodes[trace_id]["children"] = []

    # 2nd pass through nodes - calculating parent-child relationships
    for trace_id, node in nodes.iteritems():
        if node["parent_id"] in nodes:
            nodes[node["parent_id"]]["children"].append(nodes[trace_id])
        else:
            tree.append(nodes[trace_id])  # no parent => top-level node

    for node in nodes:
        nodes[node]["children"].sort(key=lambda x: x["info"]["started"])

    return sorted(tree, key=lambda x: x["info"]["started"])


def parse_notifications(notifications):
    """Parse & builds tree structure from list of ceilometer notifications."""

    result = {}
    started_at = 0
    finished_at = 0

    for n in notifications:
        meta = n["metadata"]
        key = meta["trace_id"]

        if key not in result:
            result[key] = {
                "info": {
                    "service": meta["event_type"].split(".", 1)[1],
                    "host": meta["host"],
                    "name": meta["name"].split("-")[0]
                },
                "parent_id": meta["parent_id"],
                "trace_id": meta["trace_id"]
            }

        skip_keys = ["base_id", "trace_id", "parent_id", "name", "host",
                     "event_type"]

        for k, v in meta.iteritems():
            if k not in skip_keys:
                result[key]["info"][k] = v

        timestamp = datetime.datetime.strptime(n["timestamp"],
                                               "%Y-%m-%dT%H:%M:%S.%f")

        if meta["name"].endswith("stop"):
            result[key]["info"]["finished"] = timestamp
        else:
            result[key]["info"]["started"] = timestamp

        if not started_at or started_at > timestamp:
            started_at = timestamp

        if not finished_at or finished_at < timestamp:
            finished_at = timestamp

    def msec(deltatime):
        return (int)(deltatime.total_seconds() * 1000)

    for r in result.itervalues():
        r["info"]["started"] = msec(r["info"]["started"] - started_at)
        r["info"]["finished"] = msec(r["info"]["finished"] - started_at)

    return {
        "info": {
            "name": "total",
            "started": 0,
            "finished": msec(finished_at - started_at)
        },
        "children": _build_tree(result)
    }
