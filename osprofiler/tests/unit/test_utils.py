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
import uuid

import mock

from osprofiler import _utils as utils
from osprofiler.tests import test


class UtilsTestCase(test.TestCase):

    def test_split(self):
        self.assertEqual([1, 2], utils.split([1, 2]))
        self.assertEqual(["A", "B"], utils.split("A, B"))
        self.assertEqual(["A", " B"], utils.split("A, B", strip=False))

    def test_split_wrong_type(self):
        self.assertRaises(TypeError, utils.split, 1)

    def test_binary_encode_and_decode(self):
        self.assertEqual("text",
                         utils.binary_decode(utils.binary_encode("text")))

    def test_binary_encode_invalid_type(self):
        self.assertRaises(TypeError, utils.binary_encode, 1234)

    def test_binary_encode_binary_type(self):
        binary = utils.binary_encode("text")
        self.assertEqual(binary, utils.binary_encode(binary))

    def test_binary_decode_invalid_type(self):
        self.assertRaises(TypeError, utils.binary_decode, 1234)

    def test_binary_decode_text_type(self):
        self.assertEqual("text", utils.binary_decode("text"))

    def test_generate_hmac(self):
        hmac_key = "secrete"
        data = "my data"

        h = hmac.new(utils.binary_encode(hmac_key), digestmod=hashlib.sha1)
        h.update(utils.binary_encode(data))

        self.assertEqual(h.hexdigest(), utils.generate_hmac(data, hmac_key))

    def test_signed_pack_unpack(self):
        hmac = "secret"
        data = {"some": "data"}

        packed_data, hmac_data = utils.signed_pack(data, hmac)

        process_data = utils.signed_unpack(packed_data, hmac_data, [hmac])
        self.assertIn("hmac_key", process_data)
        process_data.pop("hmac_key")
        self.assertEqual(data, process_data)

    def test_signed_pack_unpack_many_keys(self):
        keys = ["secret", "secret2", "secret3"]
        data = {"some": "data"}
        packed_data, hmac_data = utils.signed_pack(data, keys[-1])

        process_data = utils.signed_unpack(packed_data, hmac_data, keys)
        self.assertEqual(keys[-1], process_data["hmac_key"])

    def test_signed_pack_unpack_many_wrong_keys(self):
        keys = ["secret", "secret2", "secret3"]
        data = {"some": "data"}
        packed_data, hmac_data = utils.signed_pack(data, "password")

        process_data = utils.signed_unpack(packed_data, hmac_data, keys)
        self.assertIsNone(process_data)

    def test_signed_unpack_wrong_key(self):
        data = {"some": "data"}
        packed_data, hmac_data = utils.signed_pack(data, "secret")

        self.assertIsNone(utils.signed_unpack(packed_data, hmac_data, "wrong"))

    def test_signed_unpack_no_key_or_hmac_data(self):
        data = {"some": "data"}
        packed_data, hmac_data = utils.signed_pack(data, "secret")
        self.assertIsNone(utils.signed_unpack(packed_data, hmac_data, None))
        self.assertIsNone(utils.signed_unpack(packed_data, None, "secret"))
        self.assertIsNone(utils.signed_unpack(packed_data, " ", "secret"))

    @mock.patch("osprofiler._utils.generate_hmac")
    def test_singed_unpack_generate_hmac_failed(self, mock_generate_hmac):
        mock_generate_hmac.side_effect = Exception
        self.assertIsNone(utils.signed_unpack("data", "hmac_data", "hmac_key"))

    def test_signed_unpack_invalid_json(self):
        hmac = "secret"
        data = base64.urlsafe_b64encode(utils.binary_encode("not_a_json"))
        hmac_data = utils.generate_hmac(data, hmac)

        self.assertIsNone(utils.signed_unpack(data, hmac_data, hmac))

    def test_shorten_id_with_valid_uuid(self):
        valid_id = "4e3e0ec6-2938-40b1-8504-09eb1d4b0dee"

        uuid_obj = uuid.UUID(valid_id)

        with mock.patch("uuid.UUID") as mock_uuid:
            mock_uuid.return_value = uuid_obj

            result = utils.shorten_id(valid_id)
            expected = 9584796812364680686

            self.assertEqual(expected, result)

    @mock.patch("oslo_utils.uuidutils.generate_uuid")
    def test_shorten_id_with_invalid_uuid(self, mock_gen_uuid):
        invalid_id = "invalid"
        mock_gen_uuid.return_value = "1c089ea8-28fe-4f3d-8c00-f6daa2bc32f1"

        result = utils.shorten_id(invalid_id)
        expected = 10088334584203457265

        self.assertEqual(expected, result)

    def test_itersubclasses(self):

        class A(object):
            pass

        class B(A):
            pass

        class C(A):
            pass

        class D(C):
            pass

        self.assertEqual([B, C, D], list(utils.itersubclasses(A)))

        class E(type):
            pass

        self.assertEqual([], list(utils.itersubclasses(E)))
