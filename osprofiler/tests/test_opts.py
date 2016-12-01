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
from oslo_config import fixture

from osprofiler import opts
from osprofiler.tests import test


class ConfigTestCase(test.TestCase):
    def setUp(self):
        super(ConfigTestCase, self).setUp()
        self.conf_fixture = self.useFixture(fixture.Config())

    def test_options_defaults(self):
        opts.set_defaults(self.conf_fixture.conf)
        self.assertFalse(self.conf_fixture.conf.profiler.enabled)
        self.assertFalse(self.conf_fixture.conf.profiler.trace_sqlalchemy)
        self.assertEqual("SECRET_KEY",
                         self.conf_fixture.conf.profiler.hmac_keys)
        self.assertFalse(opts.is_trace_enabled(self.conf_fixture.conf))
        self.assertFalse(opts.is_db_trace_enabled(self.conf_fixture.conf))

    def test_options_defaults_override(self):
        opts.set_defaults(self.conf_fixture.conf, enabled=True,
                          trace_sqlalchemy=True,
                          hmac_keys="MY_KEY")
        self.assertTrue(self.conf_fixture.conf.profiler.enabled)
        self.assertTrue(self.conf_fixture.conf.profiler.trace_sqlalchemy)
        self.assertEqual("MY_KEY",
                         self.conf_fixture.conf.profiler.hmac_keys)
        self.assertTrue(opts.is_trace_enabled(self.conf_fixture.conf))
        self.assertTrue(opts.is_db_trace_enabled(self.conf_fixture.conf))

    @mock.patch("osprofiler.web.enable")
    @mock.patch("osprofiler.web.disable")
    def test_web_trace_disabled(self, mock_disable, mock_enable):
        opts.set_defaults(self.conf_fixture.conf, hmac_keys="MY_KEY")
        opts.enable_web_trace(self.conf_fixture.conf)
        opts.disable_web_trace(self.conf_fixture.conf)
        self.assertEqual(0, mock_enable.call_count)
        self.assertEqual(0, mock_disable.call_count)

    @mock.patch("osprofiler.web.enable")
    @mock.patch("osprofiler.web.disable")
    def test_web_trace_enabled(self, mock_disable, mock_enable):
        opts.set_defaults(self.conf_fixture.conf, enabled=True,
                          hmac_keys="MY_KEY")
        opts.enable_web_trace(self.conf_fixture.conf)
        opts.disable_web_trace(self.conf_fixture.conf)
        mock_enable.assert_called_once_with("MY_KEY")
        mock_disable.assert_called_once_with()
