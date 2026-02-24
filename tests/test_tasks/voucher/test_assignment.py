import freezegun
from datetime import datetime

import pytz

from tasks.voucher import process_voucher_distribution


def test_voucher_message_is_sent(mocker, dummy_storage_client):
    mocker.patch.object(
        dummy_storage_client, "create_post", return_value={"topic_id": 123}
    )

    dummy_storage_client.storage.put(
        "voucher",
        {
            "demand": {"alice": 1},
            "queue": [],
            "voucher": [
                {
                    "index": 0,
                    "voucher": "CHAOS123",
                    "owner": None,
                    "message_id": None,
                    "history": [],
                }
            ],
            "voucher_topics": {"40C3": 999},
        },
    )

    with freezegun.freeze_time("2026-10-15T12:00:00Z"):
        process_voucher_distribution(dummy_storage_client)
        expected_received_at = datetime.now().astimezone(pytz.timezone("Europe/Berlin"))

    # Check if create_post was called to send the PM
    assert len(dummy_storage_client.create_post.call_args_list) == 1
    pm_call = dummy_storage_client.create_post.call_args_list[0]

    assert pm_call.kwargs["archetype"] == "private_message"
    assert pm_call.kwargs["target_recipients"] == "alice"
    assert pm_call.kwargs["title"] == "Dein 40C3 Voucher"

    # Verify message content contains the voucher
    content = pm_call.args[0]
    assert "CHAOS123" in content
    assert "https://tickets.events.ccc.de" in content

    # Check if storage was updated
    assert dummy_storage_client.storage.get("voucher") == {
        "demand": {"alice": 0},
        "queue": [],
        "voucher": [
            {
                "index": 0,
                "voucher": "CHAOS123",
                "owner": "alice",
                "received_at": expected_received_at,
                "message_id": 123,
                "history": [
                    {"username": "alice", "received_at": "2026-10-15T12:00:00+02:00"}
                ],
                "retry_counter": 0,
            }
        ],
        "voucher_topics": {"40C3": 999},
    }
