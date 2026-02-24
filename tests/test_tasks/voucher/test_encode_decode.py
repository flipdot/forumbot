import re

import pytest

from tasks.voucher import encode_voucher_identifier, decode_voucher_identifier

is_alphanumeric_lowercase = re.compile(r"^[a-z0-9]+$")


def test_encode_decode_voucher_identifier():
    congress_id = "39C3"
    for index in range(256):
        for history_length in range(256):
            encoded = encode_voucher_identifier(index, history_length, congress_id)
            assert encoded.startswith("39c3-")
            decoded_congress_id, decoded_index, decoded_history_length = (
                decode_voucher_identifier(encoded)
            )

            assert index == decoded_index
            assert history_length == decoded_history_length
            assert congress_id == decoded_congress_id


@pytest.mark.parametrize(
    "input_string",
    ["", "42", "ä", "abc-def", "39c3-invalid", "39c3-ä", "39c3-aaca-aaca"],
)
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
        encode_voucher_identifier(index, history_length, "39C3")
