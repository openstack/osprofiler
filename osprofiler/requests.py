from osprofiler import profiler
import re

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
    profiler.start("http_client", info={"requests": {
        "method": request.method,
        "url": request.url,
        "path": request.path_url
    }
    })
    response = orig_HTTPAdapter_send(http_adapter, request, **kwargs)
    profiler.stop(info={"requests": {"status_code": response.status_code}})
    return response