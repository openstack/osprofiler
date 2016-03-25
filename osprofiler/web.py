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

import six
import webob.dec

from osprofiler import _utils as utils
from osprofiler import profiler


# Trace keys that are required or optional, any other
# keys that are present will cause the trace to be rejected...
_REQUIRED_KEYS = ("base_id", "hmac_key")
_OPTIONAL_KEYS = ("parent_id",)

#: Http header that will contain the needed traces data.
X_TRACE_INFO = "X-Trace-Info"

#: Http header that will contain the traces data hmac (that will be validated).
X_TRACE_HMAC = "X-Trace-HMAC"


def get_trace_id_headers():
    """Adds the trace id headers (and any hmac) into provided dictionary."""
    p = profiler.get()
    if p and p.hmac_key:
        data = {"base_id": p.get_base_id(), "parent_id": p.get_id()}
        pack = utils.signed_pack(data, p.hmac_key)
        return {
            X_TRACE_INFO: pack[0],
            X_TRACE_HMAC: pack[1]
        }
    return {}


_ENABLED = None
_HMAC_KEYS = None


def disable():
    """Disable middleware.

    This is the alternative way to disable middleware. It will be used to be
    able to disable middleware via oslo.config.
    """
    global _ENABLED
    _ENABLED = False


def enable(hmac_keys=None):
    """Enable middleware."""
    global _ENABLED, _HMAC_KEYS
    _ENABLED = True
    _HMAC_KEYS = utils.split(hmac_keys or "")


class WsgiMiddleware(object):
    """WSGI Middleware that enables tracing for an application."""

    def __init__(self, application, hmac_keys=None, enabled=False):
        """Initialize middleware with api-paste.ini arguments.

        :application: wsgi app
        :hmac_keys: Only trace header that was signed with one of these
                    hmac keys will be processed. This limitation is
                    essential, because it allows to profile OpenStack
                    by only those who knows this key which helps
                    avoid DDOS.
        :enabled: This middleware can be turned off fully if enabled is False.
        """
        self.application = application
        self.name = "wsgi"
        self.enabled = enabled
        self.hmac_keys = utils.split(hmac_keys or "")

    @classmethod
    def factory(cls, global_conf, **local_conf):
        def filter_(app):
            return cls(app, **local_conf)
        return filter_

    def _trace_is_valid(self, trace_info):
        if not isinstance(trace_info, dict):
            return False
        trace_keys = set(six.iterkeys(trace_info))
        if not all(k in trace_keys for k in _REQUIRED_KEYS):
            return False
        if trace_keys.difference(_REQUIRED_KEYS + _OPTIONAL_KEYS):
            return False
        return True

    @webob.dec.wsgify
    def __call__(self, request):
        if (_ENABLED is not None and not _ENABLED or
                _ENABLED is None and not self.enabled):
            return request.get_response(self.application)

        trace_info = utils.signed_unpack(request.headers.get(X_TRACE_INFO),
                                         request.headers.get(X_TRACE_HMAC),
                                         _HMAC_KEYS or self.hmac_keys)

        if not self._trace_is_valid(trace_info):
            return request.get_response(self.application)

        profiler.init(**trace_info)
        info = {
            "request": {
                "path": request.path,
                "query": request.query_string,
                "method": request.method,
                "scheme": request.scheme
            }
        }
        try:
            with profiler.Trace(self.name, info=info):
                return request.get_response(self.application)
        finally:
            profiler._clean()
