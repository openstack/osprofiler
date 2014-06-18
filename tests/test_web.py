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

import json
import mock

from webob import request as webob_request
from webob import response as webob_response

from osprofiler import profiler
from osprofiler import utils
from osprofiler import web

from tests import test


def dummy_app(environ, response):
    res = webob_response.Response()
    return res(environ, response)


class WebMiddlewareTestCase(test.TestCase):
    def setUp(self):
        super(WebMiddlewareTestCase, self).setUp()
        profiler._clean()
        self.addCleanup(profiler._clean)

    @mock.patch("osprofiler.web.utils.binary_encode")
    @mock.patch("osprofiler.web.json.dumps")
    @mock.patch("osprofiler.web.profiler.get_profiler")
    def test_add_trace_id_header(self, mock_get_profiler,
                                 mock_dumps, mock_b64encode):
        mock_dumps.return_value = "dump"
        mock_b64encode.return_value = "b64"
        p = mock.MagicMock()
        p.get_base_id.return_value = 1
        p.get_id.return_value = 2
        p.hmac_key = None
        mock_get_profiler.return_value = p

        headers = {"a": 10, "b": 20}
        web.add_trace_id_header(headers)

        self.assertEqual(sorted(headers.keys()),
                         sorted(["a", "b", "X-Trace-Info"]))
        self.assertEqual(headers["X-Trace-Info"], "b64")
        mock_b64encode.assert_called_once_with("dump")
        mock_dumps.assert_called_once_with({"base_id": 1, "parent_id": 2})

    @mock.patch("osprofiler.profiler.get_profiler")
    def test_add_trace_id_header_no_profiler(self, mock_get_profiler):
        mock_get_profiler.return_value = False
        headers = {"a": "a", "b": 1}
        old_headers = dict(headers)

        web.add_trace_id_header(headers)
        self.assertEqual(old_headers, headers)

    def test_wsgi_hmac_no_headers(self):
        req = webob_request.Request.blank("/")
        m = web.WsgiMiddleware(dummy_app, enabled=True,
                               hmac_key="secret_password")
        m(req)
        p = profiler.get_profiler()
        self.assertIsNone(p)

    def test_wsgi_hmac_headers_init_profiler(self):
        hmac_key = 'secret_password'
        profiler.init(base_id="b", parent_id="a", hmac_key=hmac_key)
        headers = {
            'Content-Type': 'text/javascript',
        }
        web.add_trace_id_header(headers)
        profiler._clean()
        self.assertIsNone(profiler.get_profiler())

        req = webob_request.Request.blank("/", headers=headers)
        m = web.WsgiMiddleware(dummy_app, enabled=True, hmac_key=hmac_key)
        m(req)

        p = profiler.get_profiler()
        self.assertIsNotNone(p)
        self.assertEqual('a', p.get_id())
        self.assertEqual('b', p.get_base_id())

    def test_wsgi_hmac_headers_init_profiler_spaces(self):
        hmac_key = 'secret_password'
        profiler.init(base_id="b", parent_id="a", hmac_key=hmac_key)
        headers = {
            'Content-Type': 'text/javascript',
        }
        web.add_trace_id_header(headers)
        headers['X-Trace-HMAC'] = "\t " + headers['X-Trace-HMAC'] + "    \n"
        profiler._clean()
        self.assertIsNone(profiler.get_profiler())

        req = webob_request.Request.blank("/", headers=headers)
        m = web.WsgiMiddleware(dummy_app, enabled=True, hmac_key=hmac_key)
        m(req)

        p = profiler.get_profiler()
        self.assertIsNotNone(p)
        self.assertEqual('a', p.get_id())
        self.assertEqual('b', p.get_base_id())

    def test_wsgi_hmac_headers_no_init_profiler(self):
        profiler.init(base_id="b", parent_id="a", hmac_key="hacked_password")
        headers = {
            'Content-Type': 'text/javascript',
        }
        web.add_trace_id_header(headers)
        profiler._clean()
        self.assertIsNone(profiler.get_profiler())

        req = webob_request.Request.blank("/", headers=headers)
        m = web.WsgiMiddleware(dummy_app, enabled=True,
                               hmac_key="secret_password")
        m(req)

        p = profiler.get_profiler()
        self.assertIsNone(p)

    def test_hmac_generation(self):
        profiler.init(base_id="b", parent_id="a", hmac_key="secret_password")
        headers = {
            'Content-Type': 'text/javascript',
        }
        web.add_trace_id_header(headers)
        self.assertIn('X-Trace-HMAC', headers)
        self.assertTrue(len(headers['X-Trace-HMAC']) > 0)

    def test_hmac_no_generation(self):
        profiler.init(base_id="b", parent_id="a")
        headers = {
            'Content-Type': 'text/javascript',
        }
        web.add_trace_id_header(headers)
        self.assertNotIn('X-Trace-HMAC', headers)
        self.assertIn('X-Trace-Info', headers)
        self.assertEqual(2, len(headers))

    def test_hmac_validation(self):
        profiler.init(base_id="b", parent_id="a", hmac_key="secret_password")
        headers = {
            'Content-Type': 'text/javascript',
        }
        web.add_trace_id_header(headers)
        content = headers.get("X-Trace-Info")
        web.validate_hmac(content, headers['X-Trace-HMAC'], "secret_password")

    def test_invalid_hmac(self):
        profiler.init(base_id="b", parent_id="a", hmac_key="secret_password")
        headers = {
            'Content-Type': 'text/javascript',
        }
        web.add_trace_id_header(headers)
        content = headers.get("X-Trace-Info")
        content += b"_changed"
        self.assertRaises(IOError, web.validate_hmac, content,
                          headers['X-Trace-HMAC'], "secret_password")

    def test_hmac_faked(self):
        headers = {
            'Content-Type': 'text/javascript',
            'X-Trace-HMAC': 'fake',
            'X-Trace-Info': '{}',
        }
        content = headers.get("X-Trace-Info")
        self.assertRaises(IOError, web.validate_hmac, content,
                          headers['X-Trace-HMAC'], 'secret_password')

    def test_wsgi_middleware_no_trace(self):
        request = mock.MagicMock()
        request.get_response.return_value = "yeah!"
        request.headers = {"a": "1", "b": "2"}

        middleware = web.WsgiMiddleware("app", enabled=True)
        self.assertEqual("yeah!", middleware(request))
        request.get_response.assert_called_once_with("app")

    def test_wsgi_middleware_disabled(self):
        request = mock.MagicMock()
        request.get_response.return_value = "yeah!"
        request.headers = {"a": "1", "b": "2"}

        middleware = web.WsgiMiddleware("app", enabled=False)
        self.assertEqual("yeah!", middleware(request))
        request.get_response.assert_called_once_with("app")

    @mock.patch("osprofiler.web.profiler.Trace")
    @mock.patch("osprofiler.web.profiler.init")
    def test_wsgi_middleware(self, mock_profiler_init, mock_profiler_trace):
        request = mock.MagicMock()
        request.get_response.return_value = "yeah!"
        request.url = "someurl"
        request.host_url = "someurl"
        request.path = "path"
        request.query_string = "query"
        request.method = "method"
        request.scheme = "scheme"

        trace_info = {"base_id": "1", "parent_id": "2"}
        request.headers = {
            "a": "1",
            "b": "2",
            "X-Trace-Info": utils.binary_encode(json.dumps(trace_info))
        }

        middleware = web.WsgiMiddleware("app", enabled=True)
        self.assertEqual("yeah!", middleware(request))
        mock_profiler_init.assert_called_once_with("1", "2", None)
        expected_info = {
            "request": {
                "host_url": request.host_url,
                "path": request.path,
                "query": request.query_string,
                "method": request.method,
                "scheme": request.scheme
            }
        }
        mock_profiler_trace.assert_called_once_with("wsgi", info=expected_info)
