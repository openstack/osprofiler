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

import mock

from osprofiler.drivers.ceilometer import Ceilometer
from osprofiler.tests import test


class CeilometerParserTestCase(test.TestCase):
    def setUp(self):
        super(CeilometerParserTestCase, self).setUp()
        self.ceilometer = Ceilometer("ceilometer://",
                                     ceilometer_api_version="2")

    def test_build_empty_tree(self):
        self.assertEqual([], self.ceilometer._build_tree({}))

    def test_build_complex_tree(self):
        test_input = {
            "2": {"parent_id": "0", "trace_id": "2", "info": {"started": 1}},
            "1": {"parent_id": "0", "trace_id": "1", "info": {"started": 0}},
            "21": {"parent_id": "2", "trace_id": "21", "info": {"started": 6}},
            "22": {"parent_id": "2", "trace_id": "22", "info": {"started": 7}},
            "11": {"parent_id": "1", "trace_id": "11", "info": {"started": 1}},
            "113": {"parent_id": "11", "trace_id": "113",
                    "info": {"started": 3}},
            "112": {"parent_id": "11", "trace_id": "112",
                    "info": {"started": 2}},
            "114": {"parent_id": "11", "trace_id": "114",
                    "info": {"started": 5}}
        }

        expected_output = [
            {
                "parent_id": "0",
                "trace_id": "1",
                "info": {"started": 0},
                "children": [
                    {
                        "parent_id": "1",
                        "trace_id": "11",
                        "info": {"started": 1},
                        "children": [
                            {"parent_id": "11", "trace_id": "112",
                             "info": {"started": 2}, "children": []},
                            {"parent_id": "11", "trace_id": "113",
                             "info": {"started": 3}, "children": []},
                            {"parent_id": "11", "trace_id": "114",
                             "info": {"started": 5}, "children": []}
                        ]
                    }
                ]
            },
            {
                "parent_id": "0",
                "trace_id": "2",
                "info": {"started": 1},
                "children": [
                    {"parent_id": "2", "trace_id": "21",
                     "info": {"started": 6}, "children": []},
                    {"parent_id": "2", "trace_id": "22",
                     "info": {"started": 7}, "children": []}
                ]
            }
        ]

        result = self.ceilometer._build_tree(test_input)
        self.assertEqual(expected_output, result)

    def test_get_report_empty(self):
        self.ceilometer.client = mock.MagicMock()
        self.ceilometer.client.events.list.return_value = []

        expected = {
            "info": {
                "name": "total",
                "started": 0,
                "finished": None,
                "last_trace_started": None
            },
            "children": [],
            "stats": {},
        }

        base_id = "10"
        self.assertEqual(expected, self.ceilometer.get_report(base_id))

    def test_get_report(self):
        self.ceilometer.client = mock.MagicMock()
        results = [mock.MagicMock(), mock.MagicMock(), mock.MagicMock(),
                   mock.MagicMock(), mock.MagicMock()]

        self.ceilometer.client.events.list.return_value = results
        results[0].to_dict.return_value = {
            "traits": [
                {
                    "type": "string",
                    "name": "base_id",
                    "value": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4"
                },
                {
                    "type": "string",
                    "name": "host",
                    "value": "ubuntu"
                },
                {
                    "type": "string",
                    "name": "method",
                    "value": "POST"
                },
                {
                    "type": "string",
                    "name": "name",
                    "value": "wsgi-start"
                },
                {
                    "type": "string",
                    "name": "parent_id",
                    "value": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4"
                },
                {
                    "type": "string",
                    "name": "project",
                    "value": "keystone"
                },
                {
                    "type": "string",
                    "name": "service",
                    "value": "main"
                },
                {
                    "type": "string",
                    "name": "timestamp",
                    "value": "2015-12-23T14:02:22.338776"
                },
                {
                    "type": "string",
                    "name": "trace_id",
                    "value": "06320327-2c2c-45ae-923a-515de890276a"
                }
            ],
            "raw": {},
            "generated": "2015-12-23T10:41:38.415793",
            "event_type": "profiler.main",
            "message_id": "65fc1553-3082-4a6f-9d1e-0e3183f57a47"}

        results[1].to_dict.return_value = {
            "traits":
                [
                    {
                        "type": "string",
                        "name": "base_id",
                        "value": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4"
                    },
                    {
                        "type": "string",
                        "name": "host",
                        "value": "ubuntu"
                    },
                    {
                        "type": "string",
                        "name": "name",
                        "value": "wsgi-stop"
                    },
                    {
                        "type": "string",
                        "name": "parent_id",
                        "value": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4"
                    },
                    {
                        "type": "string",
                        "name": "project",
                        "value": "keystone"
                    },
                    {
                        "type": "string",
                        "name": "service",
                        "value": "main"
                    },
                    {
                        "type": "string",
                        "name": "timestamp",
                        "value": "2015-12-23T14:02:22.380405"
                    },
                    {
                        "type": "string",
                        "name": "trace_id",
                        "value": "016c97fd-87f3-40b2-9b55-e431156b694b"
                    }
                ],
            "raw": {},
            "generated": "2015-12-23T10:41:38.406052",
            "event_type": "profiler.main",
            "message_id": "3256d9f1-48ba-4ac5-a50b-64fa42c6e264"}

        results[2].to_dict.return_value = {
            "traits":
                [
                    {
                        "type": "string",
                        "name": "base_id",
                        "value": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4"
                    },
                    {
                        "type": "string",
                        "name": "db.params",
                        "value": "[]"
                    },
                    {
                        "type": "string",
                        "name": "db.statement",
                        "value": "SELECT 1"
                    },
                    {
                        "type": "string",
                        "name": "host",
                        "value": "ubuntu"
                    },
                    {
                        "type": "string",
                        "name": "name",
                        "value": "db-start"
                    },
                    {
                        "type": "string",
                        "name": "parent_id",
                        "value": "06320327-2c2c-45ae-923a-515de890276a"
                    },
                    {
                        "type": "string",
                        "name": "project",
                        "value": "keystone"
                    },
                    {
                        "type": "string",
                        "name": "service",
                        "value": "main"
                    },
                    {
                        "type": "string",
                        "name": "timestamp",
                        "value": "2015-12-23T14:02:22.395365"
                    },
                    {
                        "type": "string",
                        "name": "trace_id",
                        "value": "1baf1d24-9ca9-4f4c-bd3f-01b7e0c0735a"
                    }
                ],
            "raw": {},
            "generated": "2015-12-23T10:41:38.984161",
            "event_type": "profiler.main",
            "message_id": "60368aa4-16f0-4f37-a8fb-89e92fdf36ff"}

        results[3].to_dict.return_value = {
            "traits":
                [
                    {
                        "type": "string",
                        "name": "base_id",
                        "value": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4"
                    },
                    {
                        "type": "string",
                        "name": "host",
                        "value": "ubuntu"
                    },
                    {
                        "type": "string",
                        "name": "name",
                        "value": "db-stop"
                    },
                    {
                        "type": "string",
                        "name": "parent_id",
                        "value": "06320327-2c2c-45ae-923a-515de890276a"
                    },
                    {
                        "type": "string",
                        "name": "project",
                        "value": "keystone"
                    },
                    {
                        "type": "string",
                        "name": "service",
                        "value": "main"
                    },
                    {
                        "type": "string",
                        "name": "timestamp",
                        "value": "2015-12-23T14:02:22.415486"
                    },
                    {
                        "type": "string",
                        "name": "trace_id",
                        "value": "1baf1d24-9ca9-4f4c-bd3f-01b7e0c0735a"
                    }
                ],
            "raw": {},
            "generated": "2015-12-23T10:41:39.019378",
            "event_type": "profiler.main",
            "message_id": "3fbeb339-55c5-4f28-88e4-15bee251dd3d"}

        results[4].to_dict.return_value = {
            "traits":
                [
                    {
                        "type": "string",
                        "name": "base_id",
                        "value": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4"
                    },
                    {
                        "type": "string",
                        "name": "host",
                        "value": "ubuntu"
                    },
                    {
                        "type": "string",
                        "name": "method",
                        "value": "GET"
                    },
                    {
                        "type": "string",
                        "name": "name",
                        "value": "wsgi-start"
                    },
                    {
                        "type": "string",
                        "name": "parent_id",
                        "value": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4"
                    },
                    {
                        "type": "string",
                        "name": "project",
                        "value": "keystone"
                    },
                    {
                        "type": "string",
                        "name": "service",
                        "value": "main"
                    },
                    {
                        "type": "string",
                        "name": "timestamp",
                        "value": "2015-12-23T14:02:22.427444"
                    },
                    {
                        "type": "string",
                        "name": "trace_id",
                        "value": "016c97fd-87f3-40b2-9b55-e431156b694b"
                    }
                ],
            "raw": {},
            "generated": "2015-12-23T10:41:38.360409",
            "event_type": "profiler.main",
            "message_id": "57b971a9-572f-4f29-9838-3ed2564c6b5b"}

        expected = {"children": [
            {"children": [{"children": [],
                           "info": {"finished": 76,
                                    "host": "ubuntu",
                                    "meta.raw_payload.db-start": {},
                                    "meta.raw_payload.db-stop": {},
                                    "name": "db",
                                    "project": "keystone",
                                    "service": "main",
                                    "started": 56,
                                    "exception": "None"},
                           "parent_id": "06320327-2c2c-45ae-923a-515de890276a",
                           "trace_id": "1baf1d24-9ca9-4f4c-bd3f-01b7e0c0735a"}
                          ],
             "info": {"finished": 0,
                      "host": "ubuntu",
                      "meta.raw_payload.wsgi-start": {},
                      "name": "wsgi",
                      "project": "keystone",
                      "service": "main",
                      "started": 0},
             "parent_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4",
             "trace_id": "06320327-2c2c-45ae-923a-515de890276a"},
            {"children": [],
             "info": {"finished": 41,
                      "host": "ubuntu",
                      "meta.raw_payload.wsgi-start": {},
                      "meta.raw_payload.wsgi-stop": {},
                      "name": "wsgi",
                      "project": "keystone",
                      "service": "main",
                      "started": 88,
                      "exception": "None"},
             "parent_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4",
             "trace_id": "016c97fd-87f3-40b2-9b55-e431156b694b"}],
            "info": {
                "finished": 88,
                "name": "total",
                "started": 0,
                "last_trace_started": 88
            },
            "stats": {"db": {"count": 1, "duration": 20},
                      "wsgi": {"count": 2, "duration": -47}},
        }

        base_id = "10"

        result = self.ceilometer.get_report(base_id)

        expected_filter = [{"field": "base_id", "op": "eq", "value": base_id}]
        self.ceilometer.client.events.list.assert_called_once_with(
            expected_filter, limit=100000)
        self.assertEqual(expected, result)
