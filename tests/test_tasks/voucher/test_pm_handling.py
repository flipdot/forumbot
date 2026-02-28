from tasks.voucher import handle_private_message_bedarf, private_message_handler
from datetime import datetime
import pytz
from freezegun import freeze_time
from tasks.voucher import process_voucher_distribution


def test_handle_private_message_bedarf_success(dummy_storage_client, mocker):
    mocker.patch.object(dummy_storage_client, "create_post")

    topic = {"id": 123, "title": "voucher-bedarf"}
    posts = {"post_stream": {"posts": [{"username": "alice"}]}}

    handle_private_message_bedarf(
        dummy_storage_client, topic, posts, "VOUCHER-BEDARF 2"
    )

    data = dummy_storage_client.storage.get("voucher")
    assert data["demand"] == {"alice": 2}

    dummy_storage_client.create_post.assert_called_with(
        "Alles klar! Ich habe dich für 2 Voucher vorgemerkt. Falls du es dir anders überlegst, "
        'schreibe mir "VOUCHER-BEDARF 0" und ich entferne dich aus der Warteschlange.',
        topic_id=123,
    )


def test_handle_bedarf_zero_removes_user(dummy_storage_client, mocker):
    mocker.patch.object(dummy_storage_client, "create_post")
    dummy_storage_client.storage.put(
        "voucher", {"demand": {"alice": 2}, "queue": ["alice", "bob"]}
    )

    topic = {"id": 123, "title": "voucher-bedarf"}
    posts = {"post_stream": {"posts": [{"username": "alice"}]}}

    handle_private_message_bedarf(
        dummy_storage_client, topic, posts, "VOUCHER-BEDARF 0"
    )

    data = dummy_storage_client.storage.get("voucher")
    assert "alice" not in data["demand"]
    assert "alice" not in data["queue"]
    assert "bob" in data["queue"]

    dummy_storage_client.create_post.assert_called_with(
        "0 Voucher also? Okay, ich habe dich aus der Warteschlange entfernt.",
        topic_id=123,
    )


def test_handle_returned_voucher(dummy_storage_client, mocker):
    """
    If a user returns a voucher via PN, the bot should accept it, update the storage, and send a confirmation message.
    """
    mocker.patch.object(dummy_storage_client, "create_post")
    mock_client_posts = mocker.patch.object(dummy_storage_client, "posts")

    # Setup initial state: a voucher assigned to a user
    initial_voucher_data = {
        "voucher": [
            {
                "index": 0,
                "voucher": "CHAOSABC",
                "owner": "test_user",
                "message_id": 999,
                "persons": 1,
                "received_at": "2024-01-01T09:00:00+01:00",
                "history": [
                    {
                        "username": "test_user",
                        "received_at": "2024-01-01T09:00:00+01:00",
                    }
                ],
                "old_owner": None,
            }
        ],
        "queue": [],
        "demand": {},
    }
    dummy_storage_client.storage.put("voucher", initial_voucher_data)

    # Simulate user returning a voucher in the PM thread
    mock_client_posts.return_value = {
        "post_stream": {
            "posts": [
                {
                    "username": "bot_username",  # Bot's initial message
                    "cooked": "Here is your voucher CHAOSABC",
                },
                {
                    "username": "test_user",  # User returning the voucher
                    "cooked": "I'm returning CHAOSXYZ",
                },
            ]
        }
    }

    # Mock the bot's username from constants
    mocker.patch.dict(
        "constants.DISCOURSE_CREDENTIALS", {"api_username": "bot_username"}
    )

    with freeze_time("2024-01-01 10:00:00+01:00"):
        process_voucher_distribution(dummy_storage_client)
        expected_returned_at_dt = datetime.now(pytz.timezone("Europe/Berlin"))

    # Assert storage was updated
    updated_voucher_data = dummy_storage_client.storage.get("voucher")
    assert updated_voucher_data == {
        "voucher": [
            {
                "index": 0,
                "voucher": "CHAOSXYZ",
                "owner": None,
                "message_id": None,
                "persons": 1,
                "received_at": expected_returned_at_dt,
                "history": [
                    {
                        "username": "test_user",
                        "received_at": "2024-01-01T09:00:00+01:00",
                        "returned_at": expected_returned_at_dt.isoformat(),
                    },
                ],
                "old_owner": "test_user",
            }
        ],
        "queue": [],
        "demand": {},
    }

    # Assert confirmation message was sent
    dummy_storage_client.create_post.assert_called_with(
        'Prima, vielen Dank für "CHAOSXYZ"!',
        topic_id=999,
    )


def test_only_first_queue_entry_removed_on_acceptance(dummy_storage_client, mocker):
    # Mock network calls in tasks/voucher.py that would fail
    mocker.patch("tasks.voucher.send_voucher_to_user")
    mocker.patch("tasks.voucher.update_history_image")
    dummy_storage_client.create_post = mocker.Mock()

    # Setup: User 'alice' is in the queue twice.
    # She has an offer for voucher 'V1'.
    data = {
        "voucher": [
            {"voucher": "V1", "offered_to": [{"username": "alice", "message_id": 123}]}
        ],
        "queue": ["alice", "bob", "alice", "charlie"],
    }
    dummy_storage_client.storage.put("voucher", data)

    # Mock the topic and posts for acceptance
    topic = {"id": 123}
    posts = {
        "post_stream": {
            "posts": [{"username": "alice", "cooked": "VOUCHER_JETZT_EINLOESEN"}]
        }
    }

    # Execute
    res = private_message_handler(dummy_storage_client, topic, posts)

    # Verify
    assert res is True
    updated_data = dummy_storage_client.storage.get("voucher")

    # Alice should still be in the queue once (the second 'alice')
    assert updated_data["queue"] == ["bob", "alice", "charlie"]
    # And she should own the voucher
    assert updated_data["voucher"][0]["owner"] == "alice"


def test_offered_to_cleared_on_acceptance(dummy_storage_client, mocker):
    mocker.patch("tasks.voucher.send_voucher_to_user")
    mocker.patch("tasks.voucher.update_history_image")
    dummy_storage_client.create_post = mocker.Mock()

    data = {
        "voucher": [
            {
                "voucher": "V1",
                "offered_to": [
                    {"username": "alice", "message_id": 123},
                    {"username": "bob", "message_id": 456},
                ],
            }
        ],
        "queue": ["alice", "bob"],
    }
    dummy_storage_client.storage.put("voucher", data)

    topic = {"id": 123}
    posts = {
        "post_stream": {
            "posts": [{"username": "alice", "cooked": "VOUCHER_JETZT_EINLOESEN"}]
        }
    }

    res = private_message_handler(dummy_storage_client, topic, posts)

    assert res is True
    updated_data = dummy_storage_client.storage.get("voucher")
    # offered_to should be cleared
    assert updated_data["voucher"][0]["offered_to"] == []
    assert updated_data["voucher"][0]["owner"] == "alice"
