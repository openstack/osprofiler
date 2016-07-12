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

from osprofiler.drivers.elasticsearch_driver import ElasticsearchDriver
from osprofiler.tests import test


class ElasticsearchTestCase(test.TestCase):

    def setUp(self):
        super(ElasticsearchTestCase, self).setUp()
        self.elasticsearch = ElasticsearchDriver("elasticsearch://localhost")
        self.elasticsearch.project = "project"
        self.elasticsearch.service = "service"

    def test_init_and_notify(self):
        self.elasticsearch.client = mock.MagicMock()
        self.elasticsearch.client.reset_mock()
        project = "project"
        service = "service"
        host = "host"

        info = {
            "a": 10,
            "project": project,
            "service": service,
            "host": host
        }
        self.elasticsearch.notify(info)

        self.elasticsearch.client\
            .index.assert_called_once_with(index="osprofiler-notifications",
                                           doc_type="notification",
                                           body=info)

    def test_get_empty_report(self):
        self.elasticsearch.client = mock.MagicMock()
        self.elasticsearch.client.search = mock\
            .MagicMock(return_value={"_scroll_id": "1", "hits": {"hits": []}})
        self.elasticsearch.client.reset_mock()

        get_report = self.elasticsearch.get_report
        base_id = "abacaba"

        get_report(base_id)

        self.elasticsearch.client\
            .search.assert_called_once_with(index="osprofiler-notifications",
                                            doc_type="notification",
                                            size=10000,
                                            scroll="2m",
                                            body={"query": {
                                                "match": {"base_id": base_id}}
                                            })

    def test_get_non_empty_report(self):
        base_id = "1"
        elasticsearch_first_response = {
            "_scroll_id": "1",
            "hits": {
                "hits": [
                    {
                        "_source": {
                            "timestamp": "2016-08-10T16:58:03.064438",
                            "base_id": base_id,
                            "project": "project",
                            "service": "service",
                            "parent_id": "0",
                            "name": "test",
                            "info": {
                                "host": "host"
                            },
                            "trace_id": "1"
                        }
                    }
                ]}}
        elasticsearch_second_response = {
            "_scroll_id": base_id,
            "hits": {"hits": []}}
        self.elasticsearch.client = mock.MagicMock()
        self.elasticsearch.client.search = \
            mock.MagicMock(return_value=elasticsearch_first_response)
        self.elasticsearch.client.scroll = \
            mock.MagicMock(return_value=elasticsearch_second_response)

        self.elasticsearch.client.reset_mock()

        self.elasticsearch.get_report(base_id)

        self.elasticsearch.client\
            .search.assert_called_once_with(index="osprofiler-notifications",
                                            doc_type="notification",
                                            size=10000,
                                            scroll="2m",
                                            body={"query": {
                                                "match": {"base_id": base_id}}
                                            })

        self.elasticsearch.client\
            .scroll.assert_called_once_with(scroll_id=base_id, scroll="2m")
