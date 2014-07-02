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

from osprofiler import notifier

from tests import test


class NotifierTestCase(test.TestCase):

    def tearDown(self):
        notifier.__notifier = notifier._noop_notifier
        super(NotifierTestCase, self).tearDown()

    def test_set(self):

        def test(info):
            pass

        notifier.set(test)
        self.assertEqual(notifier.get(), test)

    def test_get_default_notifier(self):
        self.assertEqual(notifier.get(), notifier._noop_notifier)