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

from osprofiler.cmd import cliutils
from osprofiler.drivers import base
from osprofiler import exc


class BaseCommand(object):
    group_name = None


class TraceCommands(BaseCommand):
    group_name = "trace"

    @cliutils.arg("trace", help="File with trace or trace id")
    @cliutils.arg("--connection-string", dest="conn_str",
                  default="ceilometer://",
                  help="storage driver's connection string")
    @cliutils.arg("--json", dest="use_json", action="store_true",
                  help="show trace in JSON")
    @cliutils.arg("--html", dest="use_html", action="store_true",
                  help="show trace in HTML")
    @cliutils.arg("--out", dest="file_name", help="save output in file")
    def show(self, args):
        """Displays trace-results by given trace id in HTML or JSON format."""

        trace = None

        if os.path.exists(args.trace):
            trace = json.load(open(args.trace))
        else:
            try:
                engine = base.get_driver(args.conn_str, **args.__dict__)
            except Exception as e:
                raise exc.CommandError(e.message)

            trace = engine.get_report(args.trace)

        if not trace:
            msg = ("Trace with UUID %s not found. "
                   "There are 3 possible reasons: \n"
                   " 1) You are using not admin credentials\n"
                   " 2) You specified wrong trace id\n"
                   " 3) You specified wrong HMAC Key in original calling\n"
                   " 4) Ceilometer didn't enable profiler notification topic"
                   % args.trace)
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
            output = json.dumps(trace, default=datetime_json_serialize)
        elif args.use_html:
            with open(os.path.join(os.path.dirname(__file__),
                                   "template.html")) as html_template:
                output = html_template.read().replace(
                    "$DATA", json.dumps(trace, indent=2,
                                        default=datetime_json_serialize))
        else:
            raise exc.CommandError("You should choose one of the following "
                                   "output-formats: --json or --html.")

        if args.file_name:
            with open(args.file_name, "w+") as output_file:
                output_file.write(output)
        else:
            print(output)
