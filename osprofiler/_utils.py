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
import six


def binary_encode(text, encoding='utf-8'):
    """Converts a string of into a binary type using given encoding.

    Does nothing if text not unicode string.
    """
    if isinstance(text, six.binary_type):
        return text
    elif isinstance(text, six.text_type):
        return text.encode(encoding)
    else:
        raise TypeError("Expected binary or string type")


def binary_decode(data, encoding='utf-8'):
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


def signed_unpack(data, hmac_data, hmac_key):
    """Unpack data and check that it was signed with hmac_key.

    :param data: json string that was singed_packed.
    :param hmac_data: hmac data that was generated from json by hmac_key on
                      user side
    :param hmac_key: server side hmac_key, that should be the same as user

    :returns: None in case of something wrong, Object in case of everything OK.
    """

    # NOTE(boris-42): For security reason, if there is no hmac_data or hmac_key
    #                 we don't trust data => return None.
    if not (hmac_key and hmac_data):
        return None

    try:
        if generate_hmac(data, hmac_key) != hmac_data.strip():
            return None

        return json.loads(binary_decode(base64.urlsafe_b64decode(data)))
    except Exception:
        return None
