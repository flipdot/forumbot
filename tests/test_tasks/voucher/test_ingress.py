import logging
from datetime import datetime
from email import message_from_string
from email.message import Message

import freezegun
import pytest
import pytz
from tasks.voucher import (
    process_email_voucheringress,
    encode_voucher_identifier,
    get_congress_id,
)


def create_email(subject, content) -> Message:
    msg_str = f"""To: voucher@flipdot.org
From: tickets@cccv.de
Subject: {subject}

{content}"""
    return message_from_string(msg_str)


def test_process_email_new_voucherlist_already_in_progress(dummy_storage_client):
    # Setup storage with existing vouchers
    existing_vouchers = [{"index": 0, "voucher": "CHAOSOLD", "owner": "someone"}]
    dummy_storage_client.storage.put("voucher", {"voucher": existing_vouchers})

    msg = create_email(
        "Vouchers for Kassel",
        """BEGIN VOUCHER LIST
CHAOSNEW
END VOUCHER LIST""",
    )

    process_email_voucheringress(dummy_storage_client, None, msg)

    # Verify vouchers were NOT overridden
    data = dummy_storage_client.storage.get("voucher")
    assert data["voucher"] == existing_vouchers


def test_process_email_new_voucherlist_success(dummy_storage_client, mocker):
    congress_id = get_congress_id()
    dummy_storage_client.storage.put(
        "voucher", {"voucher": [], "voucher_topics": {congress_id: 123}}
    )

    # Mock create_post to avoid real API calls
    mocker.patch.object(dummy_storage_client, "create_post")

    msg = create_email(
        "Vouchers for Kassel",
        """BEGIN VOUCHER LIST
CHAOS1
CHAOS2
END VOUCHER LIST""",
    )

    with freezegun.freeze_time("2026-02-08T12:00:00Z"):
        expected_now = datetime.now(pytz.timezone("Europe/Berlin"))
        process_email_voucheringress(dummy_storage_client, None, msg)

    # Verify vouchers stored
    data = dummy_storage_client.storage.get("voucher")
    assert data["voucher"] == [
        {
            "index": 0,
            "voucher": "CHAOS1",
            "owner": None,
            "history": [],
            "old_owner": "testbot_username",
            "received_at": expected_now,
            "message_id": None,
        },
        {
            "index": 1,
            "voucher": "CHAOS2",
            "owner": None,
            "history": [],
            "old_owner": "testbot_username",
            "received_at": expected_now,
            "message_id": None,
        },
    ]

    # Verify post was created in the correct topic
    dummy_storage_client.create_post.assert_called()
    args, kwargs = dummy_storage_client.create_post.call_args
    assert kwargs["topic_id"] == 123


def test_process_email_new_voucherlist_invalid_format(dummy_storage_client, caplog):
    dummy_storage_client.storage.put("voucher", {"voucher": []})

    # Missing BEGIN/END markers
    msg = create_email("Vouchers for Kassel", "CHAOS1\nCHAOS2")

    caplog.set_level(logging.ERROR)
    process_email_voucheringress(dummy_storage_client, None, msg)

    # Verify nothing stored
    data = dummy_storage_client.storage.get("voucher")
    assert data["voucher"] == []

    # Verify error logged
    assert "No voucher list found in email" in caplog.text
    assert caplog.records[0].mail_to == "voucher@flipdot.org"
    assert caplog.records[0].mail_from == "tickets@cccv.de"
    assert caplog.records[0].mail_subject == "Vouchers for Kassel"
    assert "CHAOS1\nCHAOS2" in caplog.records[0].mail_content


def test_process_email_voucher_returned_success(dummy_storage_client, mocker):
    congress_id = get_congress_id()

    voucher_data = {
        "index": 0,
        "voucher": "CHAOSOLD",
        "owner": "user1",
        "message_id": 999,
        "history": [
            {
                "username": "user1",
                "received_at": "2026-02-08T02:28:33.202692+01:00",
                "persons": 1,
            }
        ],
    }
    dummy_storage_client.storage.put(
        "voucher", {"voucher": [voucher_data], "voucher_topics": {congress_id: 123}}
    )

    # Mock create_post to avoid real API calls
    mocker.patch.object(dummy_storage_client, "create_post")

    # Encode param for index 0 and history length 1
    mail_param = encode_voucher_identifier(0, 1, congress_id)

    msg = create_email(
        "You received a voucher",
        """
Someone has instructed us to send you the following voucher code for the 39C3:

CHAOSRETURNED

You can use it to buy a ticket for 39C3 here""",
    )

    process_email_voucheringress(dummy_storage_client, mail_param, msg)

    # Verify voucher is updated
    data = dummy_storage_client.storage.get("voucher")
    voucher = data["voucher"][0]
    assert voucher["voucher"] == "CHAOSRETURNED"
    assert voucher["owner"] is None
    assert voucher["old_owner"] == "user1"
    assert voucher["message_id"] is None


def test_process_email_voucher_returned_no_code(dummy_storage_client, caplog):
    congress_id = get_congress_id()
    congress_id_lower = congress_id.lower()
    voucher_data = {
        "voucher": [
            {
                "index": 0,
                "voucher": "CHAOSOLD",
                "owner": "user1",
                "message_id": 999,
                "history": [
                    {
                        "username": "user1",
                        "received_at": "2026-02-08T02:28:33.202692+01:00",
                        "persons": 1,
                    }
                ],
            }
        ],
        "voucher_topics": {congress_id: 123},
    }
    dummy_storage_client.storage.put("voucher", voucher_data)

    mail_param = encode_voucher_identifier(0, 1, congress_id_lower)
    # Email without CHAOS voucher
    msg = create_email("Nonsense", "That is a fake email, not sent by CCC")

    caplog.set_level(logging.ERROR)
    process_email_voucheringress(dummy_storage_client, mail_param, msg)

    # Verify voucher NOT updated
    data = dummy_storage_client.storage.get("voucher")
    assert data == voucher_data

    # Verify error logged
    assert "Couldn't find voucher code in email" in caplog.text
    assert caplog.records[0].mail_to == "voucher@flipdot.org"
    assert caplog.records[0].mail_from == "tickets@cccv.de"
    assert caplog.records[0].mail_subject == "Nonsense"


@pytest.mark.parametrize(
    "invalid_param", ["invalid", "0", "!", "39c3-", "39c3-invalid"]
)
def test_process_email_voucher_returned_invalid_param(
    dummy_storage_client, caplog, invalid_param
):
    msg = create_email("You received a voucher", "CHAOS123")

    caplog.set_level(logging.ERROR)
    process_email_voucheringress(dummy_storage_client, invalid_param, msg)

    assert "Invalid mail_param in email" in caplog.text


def test_process_email_voucher_returned_no_active_topic(dummy_storage_client, mocker):
    congress_id_lower = "39c3"
    voucher_data = {
        "index": 0,
        "voucher": "CHAOSOLD",
        "owner": "user1",
        "message_id": 999,
        "history": [
            {
                "username": "user1",
                "received_at": "2026-02-08T02:28:33.202692+01:00",
                "persons": 1,
            }
        ],
    }
    # No voucher_topics set for current congress
    dummy_storage_client.storage.put(
        "voucher", {"voucher": [voucher_data], "voucher_topics": {}}
    )

    # Mock create_post to avoid real API calls
    mocker.patch.object(dummy_storage_client, "create_post")

    mail_param = encode_voucher_identifier(0, 1, congress_id_lower)

    msg = create_email(
        "You received a voucher",
        "CHAOSRETURNED",
    )

    process_email_voucheringress(dummy_storage_client, mail_param, msg)

    # Verify voucher was NOT updated because there is no active topic
    data = dummy_storage_client.storage.get("voucher")
    voucher = data["voucher"][0]
    # The expected behavior is that the voucher remains unchanged
    assert voucher["voucher"] == "CHAOSOLD"
    assert voucher["owner"] == "user1"


def test_process_email_voucher_returned_after_deadline(dummy_storage_client, mocker):
    congress_id = get_congress_id()
    congress_id_lower = congress_id.lower()
    voucher_data = {
        "index": 0,
        "voucher": "CHAOSOLD",
        "owner": "user1",
        "message_id": 999,
        "history": [
            {
                "username": "user1",
                "received_at": "2026-02-08T02:28:33.202692+01:00",
                "persons": 1,
            }
        ],
    }

    dummy_storage_client.storage.put(
        "voucher",
        {
            "voucher": [voucher_data],
            "voucher_topics": {congress_id: 123},
            "voucher_phase_range": {
                congress_id: {
                    "start": datetime(
                        2025, 10, 1, tzinfo=pytz.timezone("Europe/Berlin")
                    ),
                    "end": datetime(
                        2025, 12, 30, tzinfo=pytz.timezone("Europe/Berlin")
                    ),
                }
            },
        },
    )

    # Mock create_post
    mocker.patch.object(dummy_storage_client, "create_post")

    mail_param = encode_voucher_identifier(0, 1, congress_id_lower)

    msg = create_email(
        "You received a voucher",
        "CHAOSRETURNED",
    )

    # We are in the future relative to the end date
    with freezegun.freeze_time("2026-02-08T12:00:00Z"):
        process_email_voucheringress(dummy_storage_client, mail_param, msg)

    # Verify voucher was NOT updated because the phase has ended
    data = dummy_storage_client.storage.get("voucher")
    voucher = data["voucher"][0]
    assert voucher["voucher"] == "CHAOSOLD"
    assert voucher["owner"] == "user1"
