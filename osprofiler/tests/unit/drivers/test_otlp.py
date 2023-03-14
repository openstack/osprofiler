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

from unittest import mock

from oslo_config import cfg

from osprofiler.drivers import otlp
from osprofiler import opts
from osprofiler.tests import test


class OTLPTestCase(test.TestCase):

    def setUp(self):
        super(OTLPTestCase, self).setUp()

        opts.set_defaults(cfg.CONF)

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

        self.driver = otlp.OTLP(
            "otlp://127.0.0.1:6831",
            project="nova", service="api",
            conf=cfg.CONF)

    def test_notify_start(self):
        self.driver.notify(self.payload_start)
        self.assertEqual(1, len(self.driver.spans))

    def test_notify_stop(self):
        mock_end = mock.MagicMock()
        self.driver.notify(self.payload_start)
        self.driver.spans[0].end = mock_end
        self.driver.notify(self.payload_stop)
        mock_end.assert_called_once()

    def test_service_name_default(self):
        self.assertEqual("pr1-svc1", self.driver._get_service_name(
            cfg.CONF, "pr1", "svc1"))

    def test_service_name_prefix(self):
        cfg.CONF.set_default(
            "service_name_prefix", "prx1", "profiler_otlp")
        self.assertEqual("prx1-pr1-svc1", self.driver._get_service_name(
            cfg.CONF, "pr1", "svc1"))

    def test_process_tags(self):
        # Need to be implemented.
        pass
