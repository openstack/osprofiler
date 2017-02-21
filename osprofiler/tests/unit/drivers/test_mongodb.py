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

from osprofiler.drivers.mongodb import MongoDB
from osprofiler.tests import test


class MongoDBParserTestCase(test.TestCase):
    def setUp(self):
        super(MongoDBParserTestCase, self).setUp()
        self.mongodb = MongoDB("mongodb://localhost")

    def test_build_empty_tree(self):
        self.assertEqual([], self.mongodb._build_tree({}))

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

        result = self.mongodb._build_tree(test_input)
        self.assertEqual(expected_output, result)

    def test_get_report_empty(self):
        self.mongodb.db = mock.MagicMock()
        self.mongodb.db.profiler.find.return_value = []

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
        self.assertEqual(expected, self.mongodb.get_report(base_id))

    def test_get_report(self):
        self.mongodb.db = mock.MagicMock()
        results = [
            {
                "info": {
                    "project": None,
                    "host": "ubuntu",
                    "request": {
                        "path": "/v2/a322b5049d224a90bf8786c644409400/volumes",
                        "scheme": "http",
                        "method": "POST",
                        "query": ""
                    },
                    "service": None
                },
                "name": "wsgi-start",
                "service": "main",
                "timestamp": "2015-12-23T14:02:22.338776",
                "trace_id": "06320327-2c2c-45ae-923a-515de890276a",
                "project": "keystone",
                "parent_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4",
                "base_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4"
            },

            {
                "info": {
                    "project": None,
                    "host": "ubuntu",
                    "service": None
                },
                "name": "wsgi-stop",
                "service": "main",
                "timestamp": "2015-12-23T14:02:22.380405",
                "trace_id": "839ca3f1-afcb-45be-a4a1-679124c552bf",
                "project": "keystone",
                "parent_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4",
                "base_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4"
            },

            {
                "info": {
                    "project": None,
                    "host": "ubuntu",
                    "db": {
                        "params": {

                            },
                        "statement": "SELECT 1"
                    },
                    "service": None
                },
                "name": "db-start",
                "service": "main",
                "timestamp": "2015-12-23T14:02:22.395365",
                "trace_id": "1baf1d24-9ca9-4f4c-bd3f-01b7e0c0735a",
                "project": "keystone",
                "parent_id": "06320327-2c2c-45ae-923a-515de890276a",
                "base_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4"
            },

            {
                "info": {
                    "project": None,
                    "host": "ubuntu",
                    "service": None
                },
                "name": "db-stop",
                "service": "main",
                "timestamp": "2015-12-23T14:02:22.415486",
                "trace_id": "1baf1d24-9ca9-4f4c-bd3f-01b7e0c0735a",
                "project": "keystone",
                "parent_id": "06320327-2c2c-45ae-923a-515de890276a",
                "base_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4"
            },

            {
                "info": {
                    "project": None,
                    "host": "ubuntu",
                    "request": {
                        "path": "/v2/a322b5049d224a90bf8786c644409400/volumes",
                        "scheme": "http",
                        "method": "GET",
                        "query": ""
                    },
                    "service": None
                },
                "name": "wsgi-start",
                "service": "main",
                "timestamp": "2015-12-23T14:02:22.427444",
                "trace_id": "016c97fd-87f3-40b2-9b55-e431156b694b",
                "project": "keystone",
                "parent_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4",
                "base_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4"
            }]

        expected = {"children": [{"children": [{
            "children": [],
            "info": {"finished": 76,
                     "host": "ubuntu",
                     "meta.raw_payload.db-start": {
                         "base_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4",
                         "info": {"db": {"params": {},
                                         "statement": "SELECT 1"},
                                  "host": "ubuntu",
                                  "project": None,
                                  "service": None},
                         "name": "db-start",
                         "parent_id": "06320327-2c2c-45ae-923a-515de890276a",
                         "project": "keystone",
                         "service": "main",
                         "timestamp": "2015-12-23T14:02:22.395365",
                         "trace_id": "1baf1d24-9ca9-4f4c-bd3f-01b7e0c0735a"},
                     "meta.raw_payload.db-stop": {
                         "base_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4",
                         "info": {"host": "ubuntu",
                                  "project": None,
                                  "service": None},
                         "name": "db-stop",
                         "parent_id": "06320327-2c2c-45ae-923a-515de890276a",
                         "project": "keystone",
                         "service": "main",
                         "timestamp": "2015-12-23T14:02:22.415486",
                         "trace_id": "1baf1d24-9ca9-4f4c-bd3f-01b7e0c0735a"},
                     "name": "db",
                     "project": "keystone",
                     "service": "main",
                     "started": 56,
                     "exception": "None"},
            "parent_id": "06320327-2c2c-45ae-923a-515de890276a",
            "trace_id": "1baf1d24-9ca9-4f4c-bd3f-01b7e0c0735a"}],

            "info": {"finished": 0,
                     "host": "ubuntu",
                     "meta.raw_payload.wsgi-start": {
                         "base_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4",
                         "info": {"host": "ubuntu",
                                  "project": None,
                                  "request": {"method": "POST",
                                              "path": "/v2/a322b5049d224a90bf8"
                                              "786c644409400/volumes",
                                              "query": "",
                                              "scheme": "http"},
                                  "service": None},
                         "name": "wsgi-start",
                         "parent_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4",
                         "project": "keystone",
                         "service": "main",
                         "timestamp": "2015-12-23T14:02:22.338776",
                         "trace_id": "06320327-2c2c-45ae-923a-515de890276a"},
                     "name": "wsgi",
                     "project": "keystone",
                     "service": "main",
                     "started": 0},
            "parent_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4",
            "trace_id": "06320327-2c2c-45ae-923a-515de890276a"},

            {"children": [],
             "info": {"finished": 41,
                      "host": "ubuntu",
                      "meta.raw_payload.wsgi-stop": {
                          "base_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4",
                          "info": {"host": "ubuntu",
                                   "project": None,
                                   "service": None},
                          "name": "wsgi-stop",
                          "parent_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4",
                          "project": "keystone",
                          "service": "main",
                          "timestamp": "2015-12-23T14:02:22.380405",
                          "trace_id": "839ca3f1-afcb-45be-a4a1-679124c552bf"},
                      "name": "wsgi",
                      "project": "keystone",
                      "service": "main",
                      "started": 41,
                      "exception": "None"},
             "parent_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4",
             "trace_id": "839ca3f1-afcb-45be-a4a1-679124c552bf"},

            {"children": [],
             "info": {"finished": 88,
                      "host": "ubuntu",
                      "meta.raw_payload.wsgi-start": {
                          "base_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4",
                          "info": {"host": "ubuntu",
                                   "project": None,
                                   "request": {"method": "GET",
                                               "path": "/v2/a322b5049d224a90bf"
                                               "8786c644409400/volumes",
                                               "query": "",
                                               "scheme": "http"},
                                   "service": None},
                          "name": "wsgi-start",
                          "parent_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4",
                          "project": "keystone",
                          "service": "main",
                          "timestamp": "2015-12-23T14:02:22.427444",
                          "trace_id": "016c97fd-87f3-40b2-9b55-e431156b694b"},
                      "name": "wsgi",
                      "project": "keystone",
                      "service": "main",
                      "started": 88},
             "parent_id": "7253ca8c-33b3-4f84-b4f1-f5a4311ddfa4",
             "trace_id": "016c97fd-87f3-40b2-9b55-e431156b694b"}],
            "info": {
                "finished": 88,
                "name": "total",
                "started": 0,
                "last_trace_started": 88
            },
            "stats": {"db": {"count": 1, "duration": 20},
                      "wsgi": {"count": 3, "duration": 0}}}

        self.mongodb.db.profiler.find.return_value = results

        base_id = "10"

        result = self.mongodb.get_report(base_id)

        expected_filter = [{"base_id": base_id}, {"_id": 0}]
        self.mongodb.db.profiler.find.assert_called_once_with(
            *expected_filter)
        self.assertEqual(expected, result)
