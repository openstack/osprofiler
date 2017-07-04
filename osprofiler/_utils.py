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
import os
import uuid

from oslo_utils import secretutils
from oslo_utils import uuidutils
import six


def split(text, strip=True):
    """Splits a comma separated text blob into its components.

    Does nothing if already a list or tuple.
    """
    if isinstance(text, (tuple, list)):
        return text
    if not isinstance(text, six.string_types):
        raise TypeError("Unknown how to split '%s': %s" % (text, type(text)))
    if strip:
        return [t.strip() for t in text.split(",") if t.strip()]
    else:
        return text.split(",")


def binary_encode(text, encoding="utf-8"):
    """Converts a string of into a binary type using given encoding.

    Does nothing if text not unicode string.
    """
    if isinstance(text, six.binary_type):
        return text
    elif isinstance(text, six.text_type):
        return text.encode(encoding)
    else:
        raise TypeError("Expected binary or string type")


def binary_decode(data, encoding="utf-8"):
    """Converts a binary type into a text type using given encoding.

    Does nothing if data is already unicode string.
    """
    if isinstance(data, six.binary_type):
        return data.decode(encoding)
    elif isinstance(data, six.text_type):
        return data
    else:
        raise TypeError("Expected binary or string type")


def generate_hmac(data, hmac_key):
    """Generate a hmac using a known key given the provided content."""
    h = hmac.new(binary_encode(hmac_key), digestmod=hashlib.sha1)
    h.update(binary_encode(data))
    return h.hexdigest()


def signed_pack(data, hmac_key):
    """Pack and sign data with hmac_key."""
    raw_data = base64.urlsafe_b64encode(binary_encode(json.dumps(data)))

    # NOTE(boris-42): Don't generate_hmac if there is no hmac_key, mostly
    #                 security reason, we shouldn't allow to use WsgiMiddleware
    #                 without hmac_key, cause everybody will be able to trigger
    #                 profiler and organize DDOS.
    return raw_data, generate_hmac(raw_data, hmac_key) if hmac_key else None


def signed_unpack(data, hmac_data, hmac_keys):
    """Unpack data and check that it was signed with hmac_key.

    :param data: json string that was singed_packed.
    :param hmac_data: hmac data that was generated from json by hmac_key on
                      user side
    :param hmac_keys: server side hmac_keys, one of these should be the same
                      as user used to sign with

    :returns: None in case of something wrong, Object in case of everything OK.
    """
    # NOTE(boris-42): For security reason, if there is no hmac_data or
    #                 hmac_keys we don't trust data => return None.
    if not (hmac_keys and hmac_data):
        return None
    hmac_data = hmac_data.strip()
    if not hmac_data:
        return None
    for hmac_key in hmac_keys:
        try:
            user_hmac_data = generate_hmac(data, hmac_key)
        except Exception:  # nosec
            pass
        else:
            if secretutils.constant_time_compare(hmac_data, user_hmac_data):
                try:
                    contents = json.loads(
                        binary_decode(base64.urlsafe_b64decode(data)))
                    contents["hmac_key"] = hmac_key
                    return contents
                except Exception:
                    return None
    return None


def itersubclasses(cls, _seen=None):
    """Generator over all subclasses of a given class in depth first order."""

    _seen = _seen or set()
    try:
        subs = cls.__subclasses__()
    except TypeError:   # fails only when cls is type
        subs = cls.__subclasses__(cls)
    for sub in subs:
        if sub not in _seen:
            _seen.add(sub)
            yield sub
            for sub in itersubclasses(sub, _seen):
                yield sub


def import_modules_from_package(package):
    """Import modules from package and append into sys.modules

    :param: package - Full package name. For example: rally.deploy.engines
    """
    path = [os.path.dirname(__file__), ".."] + package.split(".")
    path = os.path.join(*path)
    for root, dirs, files in os.walk(path):
        for filename in files:
            if filename.startswith("__") or not filename.endswith(".py"):
                continue
            new_package = ".".join(root.split(os.sep)).split("....")[1]
            module_name = "%s.%s" % (new_package, filename[:-3])
            __import__(module_name)


def shorten_id(span_id):
    """Convert from uuid4 to 64 bit id for OpenTracing"""
    try:
        short_id = uuid.UUID(span_id).int & (1 << 64) - 1
    except ValueError:
        # Return a new short id for this
        short_id = shorten_id(uuidutils.generate_uuid())
    return short_id
