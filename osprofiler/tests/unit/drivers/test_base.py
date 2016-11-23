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

from osprofiler.drivers import base
from osprofiler.tests import test


class NotifierBaseTestCase(test.TestCase):

    def test_factory(self):

        class A(base.Driver):
            @classmethod
            def get_name(cls):
                return "a"

            def notify(self, a):
                return a

        self.assertEqual(10, base.get_driver("a://").notify(10))

    def test_factory_with_args(self):

        class B(base.Driver):

            def __init__(self, c_str, a, b=10):
                self.a = a
                self.b = b

            @classmethod
            def get_name(cls):
                return "b"

            def notify(self, c):
                return self.a + self.b + c

        self.assertEqual(22, base.get_driver("b://", 5, b=7).notify(10))

    def test_driver_not_found(self):
        self.assertRaises(ValueError, base.get_driver,
                          "Driver not found for connection string: "
                          "nonexisting://")

    def test_plugins_are_imported(self):
        base.get_driver("messaging://", mock.MagicMock(), "context",
                        "transport", "host")

    def test_build_empty_tree(self):
        class C(base.Driver):
            @classmethod
            def get_name(cls):
                return "c"

        self.assertEqual([], base.get_driver("c://")._build_tree({}))

    def test_build_complex_tree(self):
        class D(base.Driver):
            @classmethod
            def get_name(cls):
                return "d"

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

        self.assertEqual(
            expected_output, base.get_driver("d://")._build_tree(test_input))
