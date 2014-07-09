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

import webob.dec

from osprofiler import _utils as utils
from osprofiler import profiler


def get_trace_id_headers():
    """Adds the trace id headers (and any hmac) into provided dictionary."""
    p = profiler.get()
    if p and p.hmac_key:
        data = {"base_id": p.get_base_id(), "parent_id": p.get_id()}
        pack = utils.signed_pack(data, p.hmac_key)
        return {
            "X-Trace-Info": pack[0],
            "X-Trace-HMAC": pack[1]
        }
    return {}


_DISABLED = False


def disable():
    """Disable middleware.

    This is the alternative way to disable middleware. It will be used to be
    able to disable middleware via oslo.config.
    """
    global _DISABLED
    _DISABLED = True


def enable():
    """Enable middleware."""
    global _DISABLED
    _DISABLED = False


class WsgiMiddleware(object):
    """WSGI Middleware that enables tracing for an application."""

    def __init__(self, application, hmac_key, enabled=False):
        """Initialize middleware with api-paste.ini arguments.

        :application: wsgi app
        :hmac_key: Only trace header that was signed with this hmac key will be
                   processed. This limitation is essential, cause it allows
                   to profile OpenStack who knows this key => avoid DDOS.
        :enabled: This middleware can be turned off fully if enabled is False.
        """
        self.application = application
        self.name = "wsgi"
        self.enabled = enabled
        self.hmac_key = hmac_key

    @classmethod
    def factory(cls, global_conf, **local_conf):
        def filter_(app):
            return cls(app, **local_conf)
        return filter_

    def _trace_is_valid(self, trace_info):
        return (isinstance(trace_info, dict) and "base_id" in trace_info)

    @webob.dec.wsgify
    def __call__(self, request):
        if _DISABLED or not self.enabled:
            return request.get_response(self.application)

        trace_info = utils.signed_unpack(request.headers.get("X-Trace-Info"),
                                         request.headers.get("X-Trace-HMAC"),
                                         self.hmac_key)

        if not self._trace_is_valid(trace_info):
            return request.get_response(self.application)

        profiler.init(self.hmac_key,
                      base_id=trace_info.get("base_id"),
                      parent_id=trace_info.get("parent_id"))
        info = {
            "request": {
                "host_url": request.host_url,
                "path": request.path,
                "query": request.query_string,
                "method": request.method,
                "scheme": request.scheme
            }
        }
        with profiler.Trace(self.name, info=info):
            return request.get_response(self.application)
