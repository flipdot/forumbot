import freezegun
from datetime import datetime

import pytz

from tasks.voucher import process_voucher_distribution


def test_offer_is_made(mocker, dummy_storage_client):
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
                    "offered_to": [],
                    "message_id": None,
                    "history": [],
                }
            ],
            "voucher_topics": {"40C3": 999},
        },
    )

    with freezegun.freeze_time("2026-10-15T12:00:00+00:00"):
        process_voucher_distribution(dummy_storage_client)
        expected_offered_at = datetime.now(pytz.timezone("Europe/Berlin"))

    # Check if create_post was called to send the PM
    assert len(dummy_storage_client.create_post.call_args_list) == 1
    pm_call = dummy_storage_client.create_post.call_args_list[0]

    assert pm_call.kwargs["archetype"] == "private_message"
    assert pm_call.kwargs["target_recipients"] == "alice"
    assert pm_call.kwargs["title"] == "Dein 40C3 Voucher"

    # Verify message content contains the offer
    content = pm_call.args[0]
    assert "Dein Voucher steht bereit" in content
    assert "VOUCHER_JETZT_EINLOESEN" in content
    assert "CHAOS123" not in content

    # Check if storage was updated
    assert dummy_storage_client.storage.get("voucher") == {
        "demand": {"alice": 0},
        "queue": ["alice"],
        "voucher": [
            {
                "index": 0,
                "voucher": "CHAOS123",
                "owner": None,
                "offered_to": [
                    {"username": "alice", "offered_at": expected_offered_at.isoformat()}
                ],
                "message_id": None,
                "history": [],
            }
        ],
        "voucher_topics": {"40C3": 999},
    }
