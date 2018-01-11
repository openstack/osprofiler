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
import sys

import ddt
import mock
import six

from osprofiler.cmd import shell
from osprofiler import exc
from osprofiler.tests import test


@ddt.ddt
class ShellTestCase(test.TestCase):

    TRACE_ID = "c598094d-bbee-40b6-b317-d76003b679d3"

    def setUp(self):
        super(ShellTestCase, self).setUp()
        self.old_environment = os.environ.copy()

    def tearDown(self):
        super(ShellTestCase, self).tearDown()
        os.environ = self.old_environment

    def _trace_show_cmd(self, format_=None):
        cmd = "trace show --connection-string redis:// %s" % self.TRACE_ID
        return cmd if format_ is None else "%s --%s" % (cmd, format_)

    @mock.patch("sys.stdout", six.StringIO())
    @mock.patch("osprofiler.cmd.shell.OSProfilerShell")
    def test_shell_main(self, mock_shell):
        mock_shell.side_effect = exc.CommandError("some_message")
        shell.main()
        self.assertEqual("some_message\n", sys.stdout.getvalue())

    def run_command(self, cmd):
        shell.OSProfilerShell(cmd.split())

    def _test_with_command_error(self, cmd, expected_message):
        try:
            self.run_command(cmd)
        except exc.CommandError as actual_error:
            self.assertEqual(str(actual_error), expected_message)
        else:
            raise ValueError(
                "Expected: `osprofiler.exc.CommandError` is raised with "
                "message: '%s'." % expected_message)

    @mock.patch("osprofiler.drivers.redis_driver.Redis.get_report")
    def test_trace_show_no_selected_format(self, mock_get):
        mock_get.return_value = self._create_mock_notifications()
        msg = ("You should choose one of the following output formats: "
               "json, html or dot.")
        self._test_with_command_error(self._trace_show_cmd(), msg)

    @mock.patch("osprofiler.drivers.redis_driver.Redis.get_report")
    @ddt.data(None, {"info": {"started": 0, "finished": 1, "name": "total"},
                     "children": []})
    def test_trace_show_trace_id_not_found(self, notifications, mock_get):
        mock_get.return_value = notifications

        msg = ("Trace with UUID %s not found. Please check the HMAC key "
               "used in the command." % self.TRACE_ID)

        self._test_with_command_error(self._trace_show_cmd(), msg)

    def _create_mock_notifications(self):
        notifications = {
            "info": {
                "started": 0,
                "finished": 1,
                "name": "total"
            },
            "children": [{
                "info": {
                    "started": 0,
                    "finished": 1,
                    "name": "total"
                },
                "children": []
            }]
        }
        return notifications

    @mock.patch("sys.stdout", six.StringIO())
    @mock.patch("osprofiler.drivers.redis_driver.Redis.get_report")
    def test_trace_show_in_json(self, mock_get):
        notifications = self._create_mock_notifications()
        mock_get.return_value = notifications

        self.run_command(self._trace_show_cmd(format_="json"))
        self.assertEqual("%s\n" % json.dumps(notifications, indent=2,
                                             separators=(",", ": "),),
                         sys.stdout.getvalue())

    @mock.patch("sys.stdout", six.StringIO())
    @mock.patch("osprofiler.drivers.redis_driver.Redis.get_report")
    def test_trace_show_in_html(self, mock_get):
        notifications = self._create_mock_notifications()
        mock_get.return_value = notifications

        # NOTE(akurilin): to simplify assert statement, html-template should be
        # replaced.
        html_template = (
            "A long time ago in a galaxy far, far away..."
            "    some_data = $DATA"
            "It is a period of civil war. Rebel"
            "spaceships, striking from a hidden"
            "base, have won their first victory"
            "against the evil Galactic Empire.")

        with mock.patch("osprofiler.cmd.commands.open",
                        mock.mock_open(read_data=html_template), create=True):
            self.run_command(self._trace_show_cmd(format_="html"))
            self.assertEqual("A long time ago in a galaxy far, far away..."
                             "    some_data = %s"
                             "It is a period of civil war. Rebel"
                             "spaceships, striking from a hidden"
                             "base, have won their first victory"
                             "against the evil Galactic Empire."
                             "\n" % json.dumps(notifications, indent=4,
                                               separators=(",", ": ")),
                             sys.stdout.getvalue())

    @mock.patch("sys.stdout", six.StringIO())
    @mock.patch("osprofiler.drivers.redis_driver.Redis.get_report")
    def test_trace_show_write_to_file(self, mock_get):
        notifications = self._create_mock_notifications()
        mock_get.return_value = notifications

        with mock.patch("osprofiler.cmd.commands.open",
                        mock.mock_open(), create=True) as mock_open:
            self.run_command("%s --out='/file'" %
                             self._trace_show_cmd(format_="json"))

            output = mock_open.return_value.__enter__.return_value
            output.write.assert_called_once_with(
                json.dumps(notifications, indent=2, separators=(",", ": ")))
