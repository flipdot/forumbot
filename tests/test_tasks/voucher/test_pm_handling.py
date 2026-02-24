from tasks.voucher import handle_private_message_bedarf


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
