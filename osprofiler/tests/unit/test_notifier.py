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

from unittest import mock

from osprofiler import notifier
from osprofiler.tests import test


class NotifierTestCase(test.TestCase):

    def tearDown(self):
        notifier.set(notifier._noop_notifier)  # restore defaults
        notifier.clear_notifier_cache()
        super().tearDown()

    def test_set(self):

        def test(info):
            pass

        notifier.set(test)
        self.assertEqual(notifier.get(), test)

    def test_get_default_notifier(self):
        self.assertEqual(notifier.get(), notifier._noop_notifier)

    def test_notify(self):
        m = mock.MagicMock()
        notifier.set(m)
        notifier.notify(10)

        m.assert_called_once_with(10)

    @mock.patch("osprofiler.notifier.base.get_driver")
    def test_create(self, mock_factory):

        result = notifier.create("test", 10, b=20)
        mock_factory.assert_called_once_with("test", 10, b=20)
        self.assertEqual(mock_factory.return_value.notify, result)

    @mock.patch("osprofiler.notifier.base.get_driver")
    def test_create_driver_init_failure(self, mock_get_driver):
        mock_get_driver.side_effect = Exception()

        result = notifier.create("test", 10, b=20)
        mock_get_driver.assert_called_once_with("test", 10, b=20)
        self.assertEqual(notifier._noop_notifier, result)
