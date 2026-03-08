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

from collections.abc import Callable
import logging as log
from typing import Any
from urllib import parse as parser

from osprofiler import profiler
from osprofiler import web


# Register an OSProfiler HTTP Adapter that will profile any call made with
# requests.

LOG = log.getLogger(__name__)

_FUNC: Callable[..., Any] | None = None

try:
    from requests.adapters import HTTPAdapter
except ImportError:
    pass
else:

    def send(self: Any, request: Any, *args: Any, **kwargs: Any) -> Any:
        parsed_url = parser.urlparse(request.url)

        # Best effort guessing port if needed
        port: int | str = parsed_url.port or ""
        if not port and parsed_url.scheme == "http":
            port = 80
        elif not port and parsed_url.scheme == "https":
            port = 443

        profiler.start(
            parsed_url.scheme,
            info={
                "requests": {
                    "method": request.method,
                    "query": parsed_url.query,
                    "path": parsed_url.path,
                    "hostname": parsed_url.hostname,
                    "port": port,
                    "scheme": parsed_url.scheme,
                }
            },
        )

        # Profiling headers are overrident to take in account this new
        # context/span.
        request.headers.update(web.get_trace_id_headers())

        if _FUNC is None:
            raise RuntimeError("osprofiler requests adapter not initialized")
        response = _FUNC(self, request, *args, **kwargs)

        profiler.stop(info={"requests": {"status_code": response.status_code}})

        return response

    _FUNC = HTTPAdapter.send


def enable() -> None:
    if _FUNC:
        HTTPAdapter.send = send  # type: ignore[method-assign]
        LOG.debug("profiling requests enabled")
    else:
        LOG.warning(
            "unable to activate profiling for requests, "
            "please ensure that python requests is installed."
        )
