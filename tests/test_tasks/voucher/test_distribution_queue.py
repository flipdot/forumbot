import random

from tasks.voucher import (
    process_voucher_distribution,
    render_post_content,
)


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
        "queue": ["charlie", "bob", "dan", "alice"],
        "voucher": [
            {
                "index": 0,
                "voucher": "CHAOS1",
                "owner": None,
                "message_id": None,
                "history": [],
                "offered_to": [
                    {
                        "username": "charlie",
                        "offered_at": mocker.ANY,
                        "message_id": 123,
                    }
                ],
            },
            {
                "index": 1,
                "voucher": "CHAOS2",
                "owner": None,
                "message_id": None,
                "history": [],
                "offered_to": [
                    {
                        "username": "bob",
                        "offered_at": mocker.ANY,
                        "message_id": 123,
                    }
                ],
            },
            {
                "index": 2,
                "voucher": "CHAOS3",
                "owner": None,
                "message_id": None,
                "history": [],
                "offered_to": [
                    {
                        "username": "dan",
                        "offered_at": mocker.ANY,
                        "message_id": 123,
                    }
                ],
            },
        ],
    }


def test_render_post_content_logic(mocker):
    data = {
        "demand": {"alice": 2, "bob": 1, "charlie": 0},
        "queue": ["dan"],
        "voucher": [],
        "total_persons_reported": 5,
    }

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
