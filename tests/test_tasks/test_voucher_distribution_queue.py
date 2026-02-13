import random

from tasks.voucher import (
    process_voucher_distribution,
    render_post_content,
)
import constants


def test_voucher_demand_and_queue_generation(dummy_storage_client, mocker):
    mocker.patch.object(
        dummy_storage_client, "create_post", return_value={"topic_id": 123}
    )
    mocker.patch("tasks.voucher.check_for_returned_voucher", return_value=None)

    dummy_storage_client.storage.put(
        "voucher",
        {
            "demand": {"alice": 4, "bob": 3, "charlie": 2, "dan": 1},
            "queue": [],
            "voucher": [
                {
                    "index": 0,
                    "voucher": "CHAOS1",
                    "owner": None,
                    "message_id": None,
                    "history": [],
                },
                {
                    "index": 1,
                    "voucher": "CHAOS2",
                    "owner": None,
                    "message_id": None,
                    "history": [],
                },
                {
                    "index": 2,
                    "voucher": "CHAOS3",
                    "owner": None,
                    "message_id": None,
                    "history": [],
                },
            ],
        },
    )

    # Fixed seed for deterministic shuffle
    random.seed(42)

    process_voucher_distribution(dummy_storage_client)

    assert dummy_storage_client.storage.get("voucher") == {
        "demand": {"alice": 3, "bob": 2, "charlie": 1, "dan": 0},
        "queue": ["alice"],
        "voucher": [
            {
                "index": 0,
                "voucher": "CHAOS1",
                "owner": "charlie",
                "message_id": 123,
                "history": [{"received_at": mocker.ANY, "username": "charlie"}],
                "received_at": mocker.ANY,
                "retry_counter": mocker.ANY,
            },
            {
                "index": 1,
                "voucher": "CHAOS2",
                "owner": "bob",
                "message_id": 123,
                "history": [{"received_at": mocker.ANY, "username": "bob"}],
                "received_at": mocker.ANY,
                "retry_counter": mocker.ANY,
            },
            {
                "index": 2,
                "voucher": "CHAOS3",
                "owner": "dan",
                "message_id": 123,
                "history": [{"received_at": mocker.ANY, "username": "dan"}],
                "received_at": mocker.ANY,
                "retry_counter": mocker.ANY,
            },
        ],
    }


def test_render_post_content_logic(mocker):
    # Mock format_date to avoid locale issues in tests
    mocker.patch("tasks.voucher.format_date", return_value="some date")

    data = {
        "demand": {"alice": 2, "bob": 1, "charlie": 0},
        "queue": ["dan"],
        "voucher": [],
        "total_persons_reported": 5,
    }

    # We need to mock constants for DISCOURSE_CREDENTIALS
    mocker.patch.dict(constants.DISCOURSE_CREDENTIALS, {"api_username": "bot"})

    # Mock render to see what's passed
    mock_render = mocker.patch("tasks.voucher.render")

    render_post_content(data)

    args, kwargs = mock_render.call_args
    assert kwargs["demand_list"] == [
        {"name": "alice", "count": 2},
        {"name": "bob", "count": 1},
    ]
    assert kwargs["queue"] == ["dan"]
    assert kwargs["total_persons_in_queue"] == 4  # 2+1 from demand + 1 from queue
