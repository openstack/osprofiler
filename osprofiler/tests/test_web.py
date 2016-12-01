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
from webob import response as webob_response

from osprofiler import _utils as utils
from osprofiler import profiler
from osprofiler.tests import test
from osprofiler import web


def dummy_app(environ, response):
    res = webob_response.Response()
    return res(environ, response)


class WebTestCase(test.TestCase):

    def setUp(self):
        super(WebTestCase, self).setUp()
        profiler._clean()
        self.addCleanup(profiler._clean)

    def test_get_trace_id_headers_no_hmac(self):
        profiler.init(None, base_id="y", parent_id="z")
        headers = web.get_trace_id_headers()
        self.assertEqual(headers, {})

    def test_get_trace_id_headers(self):
        profiler.init("key", base_id="y", parent_id="z")
        headers = web.get_trace_id_headers()
        self.assertEqual(sorted(headers.keys()),
                         sorted(["X-Trace-Info", "X-Trace-HMAC"]))

        trace_info = utils.signed_unpack(headers["X-Trace-Info"],
                                         headers["X-Trace-HMAC"], ["key"])
        self.assertIn("hmac_key", trace_info)
        self.assertEqual("key", trace_info.pop("hmac_key"))
        self.assertEqual({"parent_id": "z", "base_id": "y"}, trace_info)

    @mock.patch("osprofiler.profiler.get")
    def test_get_trace_id_headers_no_profiler(self, mock_get_profiler):
        mock_get_profiler.return_value = False
        headers = web.get_trace_id_headers()
        self.assertEqual(headers, {})


class WebMiddlewareTestCase(test.TestCase):
    def setUp(self):
        super(WebMiddlewareTestCase, self).setUp()
        profiler._clean()
        # it's default state of _ENABLED param, so let's set it here
        web._ENABLED = None
        self.addCleanup(profiler._clean)

    def tearDown(self):
        web.enable()
        super(WebMiddlewareTestCase, self).tearDown()

    def test_factory(self):
        mock_app = mock.MagicMock()
        local_conf = {"enabled": True, "hmac_keys": "123"}

        factory = web.WsgiMiddleware.factory(None, **local_conf)
        wsgi = factory(mock_app)

        self.assertEqual(wsgi.application, mock_app)
        self.assertEqual(wsgi.name, "wsgi")
        self.assertTrue(wsgi.enabled)
        self.assertEqual(wsgi.hmac_keys, [local_conf["hmac_keys"]])

    def _test_wsgi_middleware_with_invalid_trace(self, headers, hmac_key,
                                                 mock_profiler_init,
                                                 enabled=True):
        request = mock.MagicMock()
        request.get_response.return_value = "yeah!"
        request.headers = headers

        middleware = web.WsgiMiddleware("app", hmac_key, enabled=enabled)
        self.assertEqual("yeah!", middleware(request))
        request.get_response.assert_called_once_with("app")
        self.assertEqual(0, mock_profiler_init.call_count)

    @mock.patch("osprofiler.web.profiler.init")
    def test_wsgi_middleware_disabled(self, mock_profiler_init):
        hmac_key = "secret"
        pack = utils.signed_pack({"base_id": "1", "parent_id": "2"}, hmac_key)
        headers = {
            "a": "1",
            "b": "2",
            "X-Trace-Info": pack[0],
            "X-Trace-HMAC": pack[1]
        }

        self._test_wsgi_middleware_with_invalid_trace(headers, hmac_key,
                                                      mock_profiler_init,
                                                      enabled=False)

    @mock.patch("osprofiler.web.profiler.init")
    def test_wsgi_middleware_no_trace(self, mock_profiler_init):
        headers = {
            "a": "1",
            "b": "2"
        }
        self._test_wsgi_middleware_with_invalid_trace(headers, "secret",
                                                      mock_profiler_init)

    @mock.patch("osprofiler.web.profiler.init")
    def test_wsgi_middleware_invalid_trace_headers(self, mock_profiler_init):
        headers = {
            "a": "1",
            "b": "2",
            "X-Trace-Info": "abbababababa",
            "X-Trace-HMAC": "abbababababa"
        }
        self._test_wsgi_middleware_with_invalid_trace(headers, "secret",
                                                      mock_profiler_init)

    @mock.patch("osprofiler.web.profiler.init")
    def test_wsgi_middleware_no_trace_hmac(self, mock_profiler_init):
        hmac_key = "secret"
        pack = utils.signed_pack({"base_id": "1", "parent_id": "2"}, hmac_key)
        headers = {
            "a": "1",
            "b": "2",
            "X-Trace-Info": pack[0]
        }
        self._test_wsgi_middleware_with_invalid_trace(headers, hmac_key,
                                                      mock_profiler_init)

    @mock.patch("osprofiler.web.profiler.init")
    def test_wsgi_middleware_invalid_hmac(self, mock_profiler_init):
        hmac_key = "secret"
        pack = utils.signed_pack({"base_id": "1", "parent_id": "2"}, hmac_key)
        headers = {
            "a": "1",
            "b": "2",
            "X-Trace-Info": pack[0],
            "X-Trace-HMAC": "not valid hmac"
        }
        self._test_wsgi_middleware_with_invalid_trace(headers, hmac_key,
                                                      mock_profiler_init)

    @mock.patch("osprofiler.web.profiler.init")
    def test_wsgi_middleware_invalid_trace_info(self, mock_profiler_init):
        hmac_key = "secret"
        pack = utils.signed_pack([{"base_id": "1"}, {"parent_id": "2"}],
                                 hmac_key)
        headers = {
            "a": "1",
            "b": "2",
            "X-Trace-Info": pack[0],
            "X-Trace-HMAC": pack[1]
        }
        self._test_wsgi_middleware_with_invalid_trace(headers, hmac_key,
                                                      mock_profiler_init)

    @mock.patch("osprofiler.web.profiler.init")
    def test_wsgi_middleware_key_passthrough(self, mock_profiler_init):
        hmac_key = "secret2"
        request = mock.MagicMock()
        request.get_response.return_value = "yeah!"
        request.url = "someurl"
        request.host_url = "someurl"
        request.path = "path"
        request.query_string = "query"
        request.method = "method"
        request.scheme = "scheme"

        pack = utils.signed_pack({"base_id": "1", "parent_id": "2"}, hmac_key)

        request.headers = {
            "a": "1",
            "b": "2",
            "X-Trace-Info": pack[0],
            "X-Trace-HMAC": pack[1]
        }

        middleware = web.WsgiMiddleware("app", "secret1,%s" % hmac_key,
                                        enabled=True)
        self.assertEqual("yeah!", middleware(request))
        mock_profiler_init.assert_called_once_with(hmac_key=hmac_key,
                                                   base_id="1",
                                                   parent_id="2")

    @mock.patch("osprofiler.web.profiler.init")
    def test_wsgi_middleware_key_passthrough2(self, mock_profiler_init):
        hmac_key = "secret1"
        request = mock.MagicMock()
        request.get_response.return_value = "yeah!"
        request.url = "someurl"
        request.host_url = "someurl"
        request.path = "path"
        request.query_string = "query"
        request.method = "method"
        request.scheme = "scheme"

        pack = utils.signed_pack({"base_id": "1", "parent_id": "2"}, hmac_key)

        request.headers = {
            "a": "1",
            "b": "2",
            "X-Trace-Info": pack[0],
            "X-Trace-HMAC": pack[1]
        }

        middleware = web.WsgiMiddleware("app", "%s,secret2" % hmac_key,
                                        enabled=True)
        self.assertEqual("yeah!", middleware(request))
        mock_profiler_init.assert_called_once_with(hmac_key=hmac_key,
                                                   base_id="1",
                                                   parent_id="2")

    @mock.patch("osprofiler.web.profiler.Trace")
    @mock.patch("osprofiler.web.profiler.init")
    def test_wsgi_middleware(self, mock_profiler_init, mock_profiler_trace):
        hmac_key = "secret"
        request = mock.MagicMock()
        request.get_response.return_value = "yeah!"
        request.url = "someurl"
        request.host_url = "someurl"
        request.path = "path"
        request.query_string = "query"
        request.method = "method"
        request.scheme = "scheme"

        pack = utils.signed_pack({"base_id": "1", "parent_id": "2"}, hmac_key)

        request.headers = {
            "a": "1",
            "b": "2",
            "X-Trace-Info": pack[0],
            "X-Trace-HMAC": pack[1]
        }

        middleware = web.WsgiMiddleware("app", hmac_key, enabled=True)
        self.assertEqual("yeah!", middleware(request))
        mock_profiler_init.assert_called_once_with(hmac_key=hmac_key,
                                                   base_id="1",
                                                   parent_id="2")
        expected_info = {
            "request": {
                "path": request.path,
                "query": request.query_string,
                "method": request.method,
                "scheme": request.scheme
            }
        }
        mock_profiler_trace.assert_called_once_with("wsgi", info=expected_info)

    @mock.patch("osprofiler.web.profiler.init")
    def test_wsgi_middleware_disable_via_python(self, mock_profiler_init):
        request = mock.MagicMock()
        request.get_response.return_value = "yeah!"
        web.disable()
        middleware = web.WsgiMiddleware("app", "hmac_key", enabled=True)
        self.assertEqual("yeah!", middleware(request))
        self.assertEqual(mock_profiler_init.call_count, 0)

    @mock.patch("osprofiler.web.profiler.init")
    def test_wsgi_middleware_enable_via_python(self, mock_profiler_init):
        request = mock.MagicMock()
        request.get_response.return_value = "yeah!"
        request.url = "someurl"
        request.host_url = "someurl"
        request.path = "path"
        request.query_string = "query"
        request.method = "method"
        request.scheme = "scheme"
        hmac_key = "super_secret_key2"

        pack = utils.signed_pack({"base_id": "1", "parent_id": "2"}, hmac_key)
        request.headers = {
            "a": "1",
            "b": "2",
            "X-Trace-Info": pack[0],
            "X-Trace-HMAC": pack[1]
        }

        web.enable("super_secret_key1,super_secret_key2")
        middleware = web.WsgiMiddleware("app", enabled=True)
        self.assertEqual("yeah!", middleware(request))
        mock_profiler_init.assert_called_once_with(hmac_key=hmac_key,
                                                   base_id="1",
                                                   parent_id="2")

    def test_disable(self):
        web.disable()
        self.assertFalse(web._ENABLED)

    def test_enabled(self):
        web.disable()
        web.enable()
        self.assertTrue(web._ENABLED)
