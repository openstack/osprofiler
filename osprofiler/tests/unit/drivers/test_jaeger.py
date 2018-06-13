# Copyright 2018 Fujitsu Ltd.
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

import mock

from osprofiler.drivers import jaeger
from osprofiler.tests import test


class JaegerTestCase(test.TestCase):

    def setUp(self):
        super(JaegerTestCase, self).setUp()
        self.payload_start = {
            "name": "api-start",
            "base_id": "4e3e0ec6-2938-40b1-8504-09eb1d4b0dee",
            "trace_id": "1c089ea8-28fe-4f3d-8c00-f6daa2bc32f1",
            "parent_id": "e2715537-3d1c-4f0c-b3af-87355dc5fc5b",
            "timestamp": "2018-05-03T04:31:51.781381",
            "info": {
                "host": "test"
            }
        }

        self.payload_stop = {
            "name": "api-stop",
            "base_id": "4e3e0ec6-2938-40b1-8504-09eb1d4b0dee",
            "trace_id": "1c089ea8-28fe-4f3d-8c00-f6daa2bc32f1",
            "parent_id": "e2715537-3d1c-4f0c-b3af-87355dc5fc5b",
            "timestamp": "2018-05-03T04:31:51.781381",
            "info": {
                "host": "test",
                "function": {
                    "result": 1
                }
            }
        }

        self.driver = jaeger.Jaeger("jaeger://127.0.0.1:6831",
                                    project="nova", service="api")

    @mock.patch("osprofiler._utils.shorten_id")
    def test_notify_start(self, mock_shorten_id):
        self.driver.notify(self.payload_start)
        calls = [
            mock.call(self.payload_start["base_id"]),
            mock.call(self.payload_start["parent_id"]),
            mock.call(self.payload_start["trace_id"])
        ]
        mock_shorten_id.assert_has_calls(calls, any_order=True)

    @mock.patch("jaeger_client.span.Span")
    @mock.patch("time.time")
    def test_notify_stop(self, mock_time, mock_span):
        fake_time = 1525416065.5958152
        mock_time.return_value = fake_time

        span = mock_span()
        self.driver.spans.append(mock_span())

        self.driver.notify(self.payload_stop)

        mock_time.assert_called_once()
        mock_time.reset_mock()

        span.finish.assert_called_once_with(finish_time=fake_time)
