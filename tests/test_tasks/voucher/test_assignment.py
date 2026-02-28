import freezegun
from datetime import datetime, timedelta

import pytz

from tasks.voucher import process_voucher_distribution, private_message_handler


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


def test_voucher_offer_escalation_in_queue(mocker, dummy_storage_client):
    mocker.patch.object(
        dummy_storage_client, "create_post", return_value={"topic_id": 456}
    )

    dummy_storage_client.storage.put(
        "voucher",
        {
            "demand": {},
            "queue": ["alice", "charlie", "bob"],
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

    # First call at T=0
    with freezegun.freeze_time("2026-10-15T12:00:00+00:00"):
        process_voucher_distribution(dummy_storage_client)
        t0_offered_at = datetime.now(pytz.timezone("Europe/Berlin"))

    assert len(dummy_storage_client.create_post.call_args_list) == 1
    assert (
        dummy_storage_client.create_post.call_args_list[0].kwargs["target_recipients"]
        == "alice"
    )

    storage = dummy_storage_client.storage.get("voucher")
    assert storage["voucher"][0]["offered_to"] == [
        {"username": "alice", "offered_at": t0_offered_at.isoformat()}
    ]
    assert storage["queue"] == ["alice", "charlie", "bob"]

    # Second call at T + 1 minute (no change)
    with freezegun.freeze_time("2026-10-15T12:01:00+00:00"):
        process_voucher_distribution(dummy_storage_client)

    assert len(dummy_storage_client.create_post.call_args_list) == 1
    assert dummy_storage_client.storage.get("voucher") == storage, (
        "Storage should not change on second call within offer window"
    )

    # Third call at T + 3 hours + 1 minute (escalation to charlie)
    with freezegun.freeze_time("2026-10-15T15:01:00+00:00"):
        process_voucher_distribution(dummy_storage_client)
        t1_offered_at = datetime.now(pytz.timezone("Europe/Berlin"))

    assert len(dummy_storage_client.create_post.call_args_list) == 2
    assert (
        dummy_storage_client.create_post.call_args_list[1].kwargs["target_recipients"]
        == "charlie"
    )

    final_storage = dummy_storage_client.storage.get("voucher")
    assert final_storage["voucher"][0]["offered_to"] == [
        {"username": "alice", "offered_at": t0_offered_at.isoformat()},
        {"username": "charlie", "offered_at": t1_offered_at.isoformat()},
    ]
    assert final_storage["queue"] == ["alice", "charlie", "bob"]


def test_voucher_acceptance(mocker, dummy_storage_client):
    mocker.patch.object(dummy_storage_client, "create_post")

    now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=pytz.timezone("Europe/Berlin"))

    dummy_storage_client.storage.put(
        "voucher",
        {
            "demand": {},
            "queue": ["alice", "bob", "charlie"],
            "voucher": [
                {
                    "index": 0,
                    "voucher": "CHAOS123",
                    "owner": None,
                    "offered_to": [
                        {
                            "username": "alice",
                            "offered_at": now.isoformat(),
                            "message_id": 101,
                        },
                        {
                            "username": "bob",
                            "offered_at": (now + timedelta(hours=3)).isoformat(),
                            "message_id": 102,
                        },
                    ],
                    "message_id": None,
                    "history": [],
                }
            ],
            "voucher_topics": {"40C3": 999},
        },
    )

    # Alice accepts
    topic = {"id": 101, "title": "Dein 40C3 Voucher"}
    posts = {
        "post_stream": {
            "posts": [{"username": "alice", "cooked": "VOUCHER_JETZT_EINLOESEN"}]
        }
    }

    with freezegun.freeze_time("2026-10-15T15:00:00+00:00"):
        accepted = private_message_handler(dummy_storage_client, topic, posts)
        expected_received_at = datetime.now(pytz.timezone("Europe/Berlin"))

    assert accepted is True

    # Check messages sent
    # 1. Voucher to Alice
    # 2. Expired notification to Bob
    assert len(dummy_storage_client.create_post.call_args_list) >= 2

    # Check Alice's message (she should get the voucher code)
    alice_call = [
        c
        for c in dummy_storage_client.create_post.call_args_list
        if c.kwargs.get("topic_id") == 101
    ][0]
    assert "CHAOS123" in alice_call.args[0]
    assert "http://tickets.events.ccc.de/" in alice_call.args[0]

    # Check Bob's message (he should get the expired message)
    bob_call = [
        c
        for c in dummy_storage_client.create_post.call_args_list
        if c.kwargs.get("topic_id") == 102
    ][0]
    assert (
        "Dein Voucher ist ausgelaufen. Du erhältst eine Nachricht, wenn wieder ein Voucher verfügbar ist"
        in bob_call.args[0]
    )

    # Check storage state
    final_storage = dummy_storage_client.storage.get("voucher")
    assert final_storage["voucher"][0]["owner"] == "alice"
    assert final_storage["voucher"][0]["received_at"] == expected_received_at
    assert final_storage["queue"] == ["bob", "charlie"]


def test_voucher_acceptance_race_condition(mocker, dummy_storage_client):
    mocker.patch.object(dummy_storage_client, "create_post")

    now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=pytz.timezone("Europe/Berlin"))

    dummy_storage_client.storage.put(
        "voucher",
        {
            "demand": {},
            "queue": ["alice", "bob"],
            "voucher": [
                {
                    "index": 0,
                    "voucher": "CHAOS123",
                    "owner": None,
                    "offered_to": [
                        {
                            "username": "alice",
                            "offered_at": now.isoformat(),
                            "message_id": 101,
                        },
                        {
                            "username": "bob",
                            "offered_at": (now + timedelta(hours=3)).isoformat(),
                            "message_id": 102,
                        },
                    ],
                    "message_id": None,
                    "history": [],
                }
            ],
            "voucher_topics": {"40C3": 999},
        },
    )

    # Alice accepts first
    topic_alice = {"id": 101, "title": "Dein 40C3 Voucher"}
    posts_alice = {
        "post_stream": {
            "posts": [{"username": "alice", "cooked": "VOUCHER_JETZT_EINLOESEN"}]
        }
    }

    # Bob accepts at the "same" time (next handler call)
    topic_bob = {"id": 102, "title": "Dein 40C3 Voucher"}
    posts_bob = {
        "post_stream": {
            "posts": [{"username": "bob", "cooked": "VOUCHER_JETZT_EINLOESEN"}]
        }
    }

    with freezegun.freeze_time("2026-10-15T15:00:00+00:00"):
        accepted_alice = private_message_handler(
            dummy_storage_client, topic_alice, posts_alice
        )
        accepted_bob = private_message_handler(
            dummy_storage_client, topic_bob, posts_bob
        )

    # Only one should have been successful in awarding the voucher
    # (The handler might return True for both if it handles the message, but only one gets the voucher in storage)
    assert (accepted_alice is True) or (accepted_bob is True)

    final_storage = dummy_storage_client.storage.get("voucher")
    # Assert exactly one owner
    assert final_storage["voucher"][0]["owner"] in ["alice", "bob"]
    # And the queue should have the other person
    assert len(final_storage["queue"]) == 1


def test_voucher_acceptance_only_if_offered(mocker, dummy_storage_client):
    mocker.patch.object(dummy_storage_client, "create_post")

    now = datetime(2026, 10, 15, 12, 0, 0, tzinfo=pytz.timezone("Europe/Berlin"))

    dummy_storage_client.storage.put(
        "voucher",
        {
            "demand": {},
            "queue": ["alice", "bob"],
            "voucher": [
                {
                    "index": 0,
                    "voucher": "CHAOS123",
                    "owner": None,
                    "offered_to": [
                        {
                            "username": "alice",
                            "offered_at": now.isoformat(),
                            "message_id": 101,
                        }
                    ],
                    "message_id": None,
                    "history": [],
                }
            ],
            "voucher_topics": {"40C3": 999},
        },
    )

    # Bob is in queue, but NO offer was made to him.
    # He tries to accept anyway via PM
    topic_bob = {"id": 102, "title": "Some other PM"}
    posts_bob = {
        "post_stream": {
            "posts": [{"username": "bob", "cooked": "VOUCHER_JETZT_EINLOESEN"}]
        }
    }

    accepted = private_message_handler(dummy_storage_client, topic_bob, posts_bob)

    # It should not be handled/accepted
    assert accepted is False

    # Storage remains unchanged
    final_storage = dummy_storage_client.storage.get("voucher")
    assert final_storage["voucher"][0]["owner"] is None
    assert final_storage["queue"] == ["alice", "bob"]
    assert len(dummy_storage_client.create_post.call_args_list) == 0
