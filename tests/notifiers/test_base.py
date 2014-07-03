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

import mock

from osprofiler._notifiers import base
from tests import test


class NotifierBaseTestCase(test.TestCase):

    def test_factory(self):

        class A(base.Notifier):

            def notify(self, a):
                return a

        self.assertEqual(base.Notifier.factory("A")(10), 10)

    def test_factory_with_args(self):

        class B(base.Notifier):

            def __init__(self, a, b=10):
                self.a = a
                self.b = b

            def notify(self, c):
                return self.a + self.b + c

        self.assertEqual(base.Notifier.factory("B", 5, b=7)(10), 22)

    def test_factory_not_found(self):
        self.assertRaises(TypeError, base.Notifier.factory, "non existing")

    def test_notify(self):
        base.Notifier().notify("")

    def test_plugins_are_imported(self):
        base.Notifier.factory("Messaging", mock.MagicMock(), "context",
                              "transport", "project", "service", "host")
