import contextlib
import logging as log

from oslo_utils import reflection

from osprofiler import profiler
import re
LOG = log.getLogger(__name__)

try:
    import requests.adapters
except ImportError:
    pass
else:
    orig_HTTPAdapter_send = requests.adapters.HTTPAdapter.send


def enable():
    try:
        import requests.adapters
    except ImportError:
        return
    requests.adapters.HTTPAdapter.send = send_wrapper


def send_wrapper(http_adapter, request, **kwargs):
    profiler.start("requests", info={
        "method": request.method,
        "url": request.url,
        "path": request.path_url
    })
    response = orig_HTTPAdapter_send(http_adapter, request, **kwargs)
    profiler.stop(info={
        "status_code": response.status_code
    })
    return response


HOST_PORT_RE = re.compile(r'^(.*):(\d+)$')


def split_host_and_port(host_string, scheme='http'):
    is_secure = True if scheme == 'https' else False
    m = HOST_PORT_RE.match(host_string)
    if m:
        host, port = m.groups()
        return host, int(port)
    elif is_secure is None:
        return host_string, None
    elif is_secure:
        return host_string, 443
    else:
        return host_string, 80
