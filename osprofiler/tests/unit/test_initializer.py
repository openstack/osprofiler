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
import testtools

from osprofiler import initializer


class InitializerTestCase(testtools.TestCase):

    @mock.patch("osprofiler.notifier.set")
    @mock.patch("osprofiler.notifier.create")
    @mock.patch("osprofiler.web.enable")
    def test_initializer(self, web_enable_mock, notifier_create_mock,
                         notifier_set_mock):
        conf = mock.Mock()
        conf.profiler.connection_string = "driver://"
        conf.profiler.hmac_keys = "hmac_keys"
        context = {}
        project = "my-project"
        service = "my-service"
        host = "my-host"

        notifier_mock = mock.Mock()
        notifier_create_mock.return_value = notifier_mock

        initializer.init_from_conf(conf, context, project, service, host)

        notifier_create_mock.assert_called_once_with(
            "driver://", context=context, project=project, service=service,
            host=host, conf=conf)
        notifier_set_mock.assert_called_once_with(notifier_mock)
        web_enable_mock.assert_called_once_with("hmac_keys")
