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
from osprofiler.cmd import exc
from osprofiler.parsers import ceilometer as ceiloparser


class BaseCommand(object):
    group_name = None


class TraceCommands(BaseCommand):
    group_name = "trace"

    @cliutils.arg('trace_id', help='trace id')
    @cliutils.arg('--json', dest='use_json', action='store_true',
                  help='show trace in JSON')
    @cliutils.arg('--html', dest='use_html', action='store_true',
                  help='show trace in HTML')
    @cliutils.arg('--out', dest='file_name', help='save output in file')
    def show(self, args):
        """Displays trace-results by given trace id in HTML or JSON format."""
        try:
            import ceilometerclient.client
            import ceilometerclient.exc
            import ceilometerclient.shell
        except ImportError:
            raise ImportError(
                "To use this command, you should install 'ceilometerclient' "
                "manually. Use command:\n 'pip install ceilometerclient'.")
        try:
            client = ceilometerclient.client.get_client(
                args.ceilometer_api_version, **args.__dict__)
            notifications = ceiloparser.get_notifications(
                client, args.trace_id)
        except Exception as e:
            if hasattr(e, 'http_status') and e.http_status == 401:
                msg = "Invalid OpenStack Identity credentials."
            else:
                msg = "Something has gone wrong. See logs for more details."

            raise exc.CommandError(msg)

        if not notifications:
            msg = ("Trace with UUID %s not found. "
                   "There are 2 possible reasons: \n"
                   " 1) You are using not admin credentials\n"
                   " 2) You specified wrong trace id" % args.trace_id)
            raise exc.CommandError(msg)

        parsed_notifications = ceiloparser.parse_notifications(notifications)

        if args.use_json:
            output = json.dumps(parsed_notifications)
        elif args.use_html:
            with open(os.path.join(os.path.dirname(__file__),
                                   "template.html")) as html_template:
                output = html_template.read().replace(
                    "$DATA", json.dumps(parsed_notifications))
        else:
            raise exc.CommandError("You should choose one of the following "
                                   "output-formats: --json or --html.")

        if args.file_name:
            with open(args.file_name, 'w+') as output_file:
                output_file.write(output)
        else:
            print (output)
