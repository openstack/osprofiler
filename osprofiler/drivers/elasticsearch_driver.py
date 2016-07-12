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

import six.moves.urllib.parse as parser

from oslo_config import cfg
from osprofiler.drivers import base
from osprofiler import exc


class ElasticsearchDriver(base.Driver):
    def __init__(self, connection_str, index_name="osprofiler-notifications",
                 project=None, service=None, host=None, conf=cfg.CONF,
                 **kwargs):
        """Elasticsearch driver for OSProfiler."""

        super(ElasticsearchDriver, self).__init__(connection_str,
                                                  project=project,
                                                  service=service, host=host)
        try:
            from elasticsearch import Elasticsearch
        except ImportError:
            raise exc.CommandError(
                "To use this command, you should install "
                "'elasticsearch' manually. Use command:\n "
                "'pip install elasticsearch'.")

        client_url = parser.urlunparse(parser.urlparse(self.connection_str)
                                       ._replace(scheme="http"))
        self.conf = conf
        self.client = Elasticsearch(client_url)
        self.index_name = index_name

    @classmethod
    def get_name(cls):
        return "elasticsearch"

    def notify(self, info):
        """Send notifications to Elasticsearch.

        :param info:  Contains information about trace element.
                      In payload dict there are always 3 ids:
                      "base_id" - uuid that is common for all notifications
                                  related to one trace. Used to simplify
                                  retrieving of all trace elements from
                                  Elasticsearch.
                      "parent_id" - uuid of parent element in trace
                      "trace_id" - uuid of current element in trace

                      With parent_id and trace_id it's quite simple to build
                      tree of trace elements, which simplify analyze of trace.

        """

        info = info.copy()
        info["project"] = self.project
        info["service"] = self.service
        self.client.index(index=self.index_name,
                          doc_type=self.conf.profiler.es_doc_type, body=info)

    def _hits(self, response):
        """Returns all hits of search query using scrolling

        :param response: ElasticSearch query response
        """
        scroll_id = response["_scroll_id"]
        scroll_size = len(response["hits"]["hits"])
        result = []

        while scroll_size > 0:
            for hit in response["hits"]["hits"]:
                result.append(hit["_source"])
            response = self.client.scroll(scroll_id=scroll_id,
                                          scroll=self.conf.profiler.
                                          es_scroll_time)
            scroll_id = response["_scroll_id"]
            scroll_size = len(response["hits"]["hits"])

        return result

    def list_traces(self, query={"match_all": {}}, fields=[]):
        """Returns array of all base_id fields that match the given criteria

        :param query: dict that specifies the query criteria
        :param fields: iterable of strings that specifies the output fields
        """
        for base_field in ["base_id", "timestamp"]:
            if base_field not in fields:
                fields.append(base_field)

        response = self.client.search(index=self.index_name,
                                      doc_type=self.conf.profiler.es_doc_type,
                                      size=self.conf.profiler.es_scroll_size,
                                      scroll=self.conf.profiler.es_scroll_time,
                                      body={"_source": fields, "query": query,
                                            "sort": [{"timestamp": "asc"}]})

        return self._hits(response)

    def get_report(self, base_id):
        """Retrieves and parses notification from Elasticsearch.

        :param base_id: Base id of trace elements.
        """
        response = self.client.search(index=self.index_name,
                                      doc_type=self.conf.profiler.es_doc_type,
                                      size=self.conf.profiler.es_scroll_size,
                                      scroll=self.conf.profiler.es_scroll_time,
                                      body={"query": {
                                          "match": {"base_id": base_id}}})

        for n in self._hits(response):
            trace_id = n["trace_id"]
            parent_id = n["parent_id"]
            name = n["name"]
            project = n["project"]
            service = n["service"]
            host = n["info"]["host"]
            timestamp = n["timestamp"]

            self._append_results(trace_id, parent_id, name, project, service,
                                 host, timestamp, n)

        return self._parse_results()
