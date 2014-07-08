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

    for trace_id in nodes:
        node = nodes[trace_id]
        node.setdefault("children", [])
        parent_id = node["parent_id"]
        if parent_id in nodes:
            nodes[parent_id].setdefault("children", [])
            nodes[parent_id]["children"].append(node)
        else:
            tree.append(node)  # no parent => top-level node

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
                    "name": meta["name"].split("-")[0]
                },
                "parent_id": meta["parent_id"],
                "trace_id": meta["trace_id"]
            }

        skip_keys = ["base_id", "trace_id", "parent_id", "name", "event_type"]

        for k in meta:
            if k not in skip_keys:
                result[key]["info"][k] = meta[k]

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

    def msec(dt):
        # NOTE(boris-42): Unfortunately this is the simplest way that works in
        #                 py26 and py27
        microsec = (dt.microseconds + (dt.seconds + dt.days * 24 * 3600) * 1e6)
        return (int)(microsec / 1000.0)

    for r in result.values():
        # NOTE(boris-42): We are not able to guarantee that ceilometer consumed
        #                 all messages => so we should at make duration 0ms.
        if "started" not in r["info"]:
            r["info"]["started"] = r["info"]["finished"]
        if "finished" not in r["info"]:
            r["info"]["finished"] = r["info"]["started"]

        r["info"]["started"] = msec(r["info"]["started"] - started_at)
        r["info"]["finished"] = msec(r["info"]["finished"] - started_at)

    return {
        "info": {
            "name": "total",
            "started": 0,
            "finished": msec(finished_at - started_at) if started_at else 0
        },
        "children": _build_tree(result)
    }


def get_notifications(ceilometer, base_id):
    """Retrieves and parses notification from ceilometer.

    :param ceilometer: Initialized ceilometer client.
    :param base_id: Base id of trace elements.
    """

    _filter = '{"=": {"resource_id": "profiler-%s"}}' % base_id
    return [n.to_dict()
            for n in ceilometer.query_samples.query(_filter, None, None)]
