from tasks.voucher import create_voucher_topic


def test_create_voucher_topic_copies_global_penalty(mocker, dummy_storage_client):
    mocker.patch.object(
        dummy_storage_client, "create_post", return_value={"topic_id": 123}
    )
    mocker.patch("tasks.voucher.render_post_content", return_value="content")

    data = {"global_penalty": {"alice": 2, "bob": 1}}

    create_voucher_topic(dummy_storage_client, data, "Voucher 40C3", "40C3")

    assert data["penalty"] == {"alice": 2, "bob": 1}
    # Ensure it's a copy
    data["global_penalty"]["alice"] = 3
    assert data["penalty"]["alice"] == 2
