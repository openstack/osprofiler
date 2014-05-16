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

import base64
import hashlib
import hmac
import json
import webob.dec

from osprofiler import profiler


def add_trace_id_header(headers):
    p = profiler.get_profiler()
    if p:
        idents = {"base_id": p.get_base_id(), "parent_id": p.get_id()}
        raw_content = json.dumps(idents)
        headers["X-Trace-Info"] = base64.b64encode(raw_content)
        if p.hmac_key:
            headers["X-Trace-HMAC"] = generate_hmac(raw_content, p.hmac_key)


def generate_hmac(content, hmac_key):
    """Generate a hmac using a known key given the provided content."""
    h = hmac.new(hmac_key, digestmod=hashlib.sha1)
    h.update(content)
    return h.hexdigest()


def validate_hmac(content, expected_hmac, hmac_key):
    """Validate the content using a known key against the expected hmac, or
    raise an io error if this can not be done (meaning this data is not valid
    or was being faked).
    """
    if hmac_key:
        h = hmac.new(hmac_key, digestmod=hashlib.sha1)
        h.update(content)
        if h.hexdigest() != expected_hmac:
            raise IOError("Invalid hmac detected")


class WsgiMiddleware(object):
    """WSGI Middleware that enables tracing for an application."""

    def __init__(self, application, name='WSGI', enabled=False, hmac_key=None):
        self.application = application
        self.name = name
        self.enabled = enabled
        self.hmac_key = hmac_key

    @classmethod
    def factory(cls, global_conf, **local_conf):
        def filter_(app):
            return cls(app, **local_conf)
        return filter_

    @webob.dec.wsgify
    def __call__(self, request):
        if not self.enabled:
            return request.get_response(self.application)

        trace_info_enc = request.headers.get("X-Trace-Info")
        trace_hmac = request.headers.get("X-Trace-HMAC")
        if trace_hmac:
            trace_hmac = trace_hmac.strip()
        if trace_info_enc:
            trace_raw = base64.b64decode(trace_info_enc)
            try:
                validate_hmac(trace_raw, trace_hmac, self.hmac_key)
            except IOError:
                pass
            else:
                trace_info = json.loads(trace_raw)

                p = profiler.init(trace_info.get("base_id"),
                                  trace_info.get("parent_id"),
                                  self.hmac_key)

                info = {
                    "request": {
                        "host_url": request.host_url,
                        "path": request.path,
                        "query": request.query_string,
                        "method": request.method,
                        "scheme": request.scheme
                    }
                }

                with p(self.name, info=info):
                    return request.get_response(self.application)

        return request.get_response(self.application)
