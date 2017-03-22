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

import json
import os

from oslo_utils import uuidutils

from osprofiler.cmd import cliutils
from osprofiler.drivers import base
from osprofiler import exc


class BaseCommand(object):
    group_name = None


class TraceCommands(BaseCommand):
    group_name = "trace"

    @cliutils.arg("trace", help="File with trace or trace id")
    @cliutils.arg("--connection-string", dest="conn_str",
                  default=(cliutils.env("OSPROFILER_CONNECTION_STRING") or
                           "ceilometer://"),
                  help="Storage driver's connection string. Defaults to "
                       "env[OSPROFILER_CONNECTION_STRING] if set, else "
                       "ceilometer://")
    @cliutils.arg("--json", dest="use_json", action="store_true",
                  help="show trace in JSON")
    @cliutils.arg("--html", dest="use_html", action="store_true",
                  help="show trace in HTML")
    @cliutils.arg("--dot", dest="use_dot", action="store_true",
                  help="show trace in DOT language")
    @cliutils.arg("--render-dot", dest="render_dot_filename",
                  help="filename for rendering the dot graph in pdf format")
    @cliutils.arg("--out", dest="file_name", help="save output in file")
    def show(self, args):
        """Display trace results in HTML, JSON or DOT format."""

        trace = None

        if not uuidutils.is_uuid_like(args.trace):
            trace = json.load(open(args.trace))
        else:
            try:
                engine = base.get_driver(args.conn_str, **args.__dict__)
            except Exception as e:
                raise exc.CommandError(e.message)

            trace = engine.get_report(args.trace)

        if not trace or not trace.get("children"):
            msg = ("Trace with UUID %s not found. Please check the HMAC key "
                   "used in the command." % args.trace)
            raise exc.CommandError(msg)

        # NOTE(ayelistratov): Ceilometer translates datetime objects to
        # strings, other drivers store this data in ISO Date format.
        # Since datetime.datetime is not JSON serializable by default,
        # this method will handle that.
        def datetime_json_serialize(obj):
            if hasattr(obj, "isoformat"):
                return obj.isoformat()
            else:
                return obj

        if args.use_json:
            output = json.dumps(trace, default=datetime_json_serialize,
                                separators=(",", ": "),
                                indent=2)
        elif args.use_html:
            with open(os.path.join(os.path.dirname(__file__),
                                   "template.html")) as html_template:
                output = html_template.read().replace(
                    "$DATA", json.dumps(trace, indent=4,
                                        separators=(",", ": "),
                                        default=datetime_json_serialize))
        elif args.use_dot:
            dot_graph = self._create_dot_graph(trace)
            output = dot_graph.source
            if args.render_dot_filename:
                dot_graph.render(args.render_dot_filename, cleanup=True)
        else:
            raise exc.CommandError("You should choose one of the following "
                                   "output formats: json, html or dot.")

        if args.file_name:
            with open(args.file_name, "w+") as output_file:
                output_file.write(output)
        else:
            print(output)

    def _create_dot_graph(self, trace):
        try:
            import graphviz
        except ImportError:
            raise exc.CommandError(
                "graphviz library is required to use this option.")

        dot = graphviz.Digraph(format="pdf")
        next_id = [0]

        def _create_node(info):
            time_taken = info["finished"] - info["started"]
            service = info["service"] + ":" if "service" in info else ""
            name = info["name"]
            label = "%s%s - %d ms" % (service, name, time_taken)

            if name == "wsgi":
                req = info["meta.raw_payload.wsgi-start"]["info"]["request"]
                label = "%s\\n%s %s.." % (label, req["method"],
                                          req["path"][:30])
            elif name == "rpc" or name == "driver":
                raw = info["meta.raw_payload.%s-start" % name]
                fn_name = raw["info"]["function"]["name"]
                label = "%s\\n%s" % (label, fn_name.split(".")[-1])

            node_id = str(next_id[0])
            next_id[0] += 1
            dot.node(node_id, label)
            return node_id

        def _create_sub_graph(root):
            rid = _create_node(root["info"])
            for child in root["children"]:
                cid = _create_sub_graph(child)
                dot.edge(rid, cid)
            return rid

        _create_sub_graph(trace)
        return dot
