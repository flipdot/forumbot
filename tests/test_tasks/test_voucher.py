import re

import pytest

from tasks.voucher import encode_voucher_identifier, decode_voucher_identifier

is_alphanumeric_lowercase = re.compile(r"^[a-z0-9]+$")


def test_encode_decode_voucher_identifier():
    for index in range(256):
        for history_length in range(256):
            encoded = encode_voucher_identifier(index, history_length)
            assert (
                is_alphanumeric_lowercase.match(encoded) is not None
            ), f"Encoded string '{encoded}' does not match the expected format"
            decoded_index, decoded_history_length = decode_voucher_identifier(encoded)

            assert index == decoded_index
            assert history_length == decoded_history_length


@pytest.mark.parametrize("input_string", ["", "42", "ä"])
def test_decode_raises_value_error_on_invalid_string(input_string):
    with pytest.raises(ValueError):
        decode_voucher_identifier(input_string)


@pytest.mark.parametrize(
    "index, history_length", [(-1, 0), (0, -1), (256, 0), (0, 256)]
)
def test_encode_voucher_identifier_raises_value_error_on_out_of_range_values(
    index, history_length
):
    with pytest.raises(ValueError):
        encode_voucher_identifier(index, history_length)
