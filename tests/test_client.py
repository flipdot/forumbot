import pytest
import yaml
from urllib.parse import quote_plus

from client import DiscourseStorageClient, DiscourseStorageError

HOST = "https://discourse.example.com"
API_USERNAME = "testuser"
API_KEY = "secret-key"
JSON_CONTENT_TYPE = "application/json; charset=utf-8"


@pytest.fixture
def client(responses):
    """
    Creates a DiscourseStorageClient with a mocked initialization.
    By default, this sets up an empty storage (no existing STORAGE_ topics).
    """
    # Mock the first page of private messages (Empty)
    responses.add(
        responses.GET,
        f"{HOST}/topics/private-messages-sent/{API_USERNAME}.json",
        json={"topic_list": {"topics": []}},
        status=200,
        content_type=JSON_CONTENT_TYPE,
        match_querystring=False,
    )

    return DiscourseStorageClient(host=HOST, api_username=API_USERNAME, api_key=API_KEY)


def test_private_messages_sent(client, responses):
    """Test the custom PN method added to DiscourseStorageClient."""
    url = f"{HOST}/topics/private-messages-sent/{API_USERNAME}.json"

    # Re-mock to return actual data
    responses.add(
        responses.GET,
        url,
        json={"topic_list": {"topics": [{"id": 1}]}},
        status=200,
        content_type=JSON_CONTENT_TYPE,
    )

    res = client.private_messages_sent()
    assert res["topic_list"]["topics"][0]["id"] == 1


def test_storage_init_scans_existing_topics(responses):
    """
    Verify that initializing the client correctly parses existing storage topics.
    """
    # Mock Page 0: Contains mix of valid and invalid topics
    responses.add(
        responses.GET,
        f"{HOST}/topics/private-messages-sent/{API_USERNAME}.json",
        json={
            "topic_list": {
                "topics": [
                    # Valid Storage
                    {"id": 101, "title": "STORAGE_app_config", "participants": []},
                    # Invalid: Has participants
                    {
                        "id": 102,
                        "title": "STORAGE_shared_data",
                        "participants": [{"username": "other"}],
                    },
                    # Invalid: Wrong Prefix
                    {"id": 103, "title": "Just a message", "participants": []},
                ]
            }
        },
        match_querystring=False,
        content_type=JSON_CONTENT_TYPE,
    )

    # Mock Page 1: Empty (stops the while loop)
    responses.add(
        responses.GET,
        f"{HOST}/topics/private-messages-sent/{API_USERNAME}.json?page=1",
        json={"topic_list": {"topics": []}},
        match_querystring=True,
        content_type=JSON_CONTENT_TYPE,
    )

    client = DiscourseStorageClient(
        host=HOST, api_username=API_USERNAME, api_key=API_KEY
    )

    ids = client.storage._storage_ids

    assert "app_config" in ids
    assert ids["app_config"] == (101, None)
    assert "shared_data" not in ids
    assert "Just a message" not in ids


def test_storage_get_lazy_load_success(responses):
    """
    Test flow: Init -> get('settings') -> fetch topic -> fetch post -> return content.
    """
    # 1. Setup Init (Found Topic 200)
    responses.add(
        responses.GET,
        f"{HOST}/topics/private-messages-sent/{API_USERNAME}.json",
        json={
            "topic_list": {
                "topics": [{"id": 200, "title": "STORAGE_settings", "participants": []}]
            }
        },
        content_type=JSON_CONTENT_TYPE,
    )
    # Page 1 empty
    responses.add(
        responses.GET,
        f"{HOST}/topics/private-messages-sent/{API_USERNAME}.json?page=1",
        json={"topic_list": {"topics": []}},
        content_type=JSON_CONTENT_TYPE,
    )

    # 2. Mock 'client.posts(topic_id)' call to find the post ID
    responses.add(
        responses.GET,
        f"{HOST}/t/200/posts.json",
        json={"post_stream": {"posts": [{"id": 555}]}},
        content_type=JSON_CONTENT_TYPE,
    )

    # 3. Mock 'client.single_post(post_id)' to get content
    data_payload = {"theme": "dark", "notifications": True}
    responses.add(
        responses.GET,
        f"{HOST}/posts/555.json",
        json={"yours": True, "raw": yaml.safe_dump(data_payload)},
        content_type=JSON_CONTENT_TYPE,
    )

    client = DiscourseStorageClient(
        host=HOST, api_username=API_USERNAME, api_key=API_KEY
    )

    result = client.storage.get("settings")

    assert result == data_payload
    assert client.storage._storage_ids["settings"] == (200, 555)


def test_storage_get_not_found(client):
    """Test get() returns default when key doesn't exist."""
    assert client.storage.get("non_existent") == {}
    assert client.storage.get("non_existent", default="foo") == "foo"


def test_storage_get_security_check(responses):
    """Ensure we don't read data if the post is not marked as 'yours'."""
    # Init finding a topic
    responses.add(
        responses.GET,
        f"{HOST}/topics/private-messages-sent/{API_USERNAME}.json",
        json={
            "topic_list": {
                "topics": [{"id": 300, "title": "STORAGE_hacked", "participants": []}]
            }
        },
        content_type=JSON_CONTENT_TYPE,
    )
    responses.add(
        responses.GET,
        f"{HOST}/topics/private-messages-sent/{API_USERNAME}.json?page=1",
        json={"topic_list": {"topics": []}},
        content_type=JSON_CONTENT_TYPE,
    )

    # Topic lookup
    responses.add(
        responses.GET,
        f"{HOST}/t/300/posts.json",
        json={"post_stream": {"posts": [{"id": 777}]}},
        content_type=JSON_CONTENT_TYPE,
    )

    # Post lookup (Not yours)
    responses.add(
        responses.GET,
        f"{HOST}/posts/777.json",
        json={
            "yours": False,
            "raw": "dangerous: data",
        },
        content_type=JSON_CONTENT_TYPE,
    )

    client = DiscourseStorageClient(
        host=HOST, api_username=API_USERNAME, api_key=API_KEY
    )

    with pytest.raises(DiscourseStorageError, match="was not created by ourself"):
        client.storage.get("hacked")


def test_storage_put_new_key(client, responses):
    """Test creating a new storage item (POST)."""

    data_to_store = {"new": "value"}

    # Mock the Create Post call
    responses.add(
        responses.POST,
        f"{HOST}/posts",
        json={"topic_id": 400, "id": 888},
        status=200,
        content_type=JSON_CONTENT_TYPE,
    )

    client.storage.put("new_key", data_to_store)

    # Check that internal state was updated
    assert client.storage._storage_ids["new_key"] == (400, 888)

    # Verify request body
    post_call = [c for c in responses.calls if c.request.method == "POST"][0]
    req_body = post_call.request.body
    assert "title=STORAGE_new_key" in req_body
    assert "archetype=private_message" in req_body
    assert quote_plus("new: value") in req_body


def test_storage_put_existing_key(responses):
    """Test updating an existing storage item (PUT)."""

    # 1. Init with existing key
    responses.add(
        responses.GET,
        f"{HOST}/topics/private-messages-sent/{API_USERNAME}.json",
        json={
            "topic_list": {
                "topics": [{"id": 500, "title": "STORAGE_existing", "participants": []}]
            }
        },
        content_type=JSON_CONTENT_TYPE,
    )
    responses.add(
        responses.GET,
        f"{HOST}/topics/private-messages-sent/{API_USERNAME}.json?page=1",
        json={"topic_list": {"topics": []}},
        content_type=JSON_CONTENT_TYPE,
    )

    # 2. Logic to fetch post_id is triggered inside put if it's missing
    responses.add(
        responses.GET,
        f"{HOST}/t/500/posts.json",
        json={"post_stream": {"posts": [{"id": 999}]}},
        content_type=JSON_CONTENT_TYPE,
    )

    # 3. Mock the Update Post call (PUT)
    responses.add(
        responses.PUT,
        f"{HOST}/posts/999",
        json={"id": 999},
        status=200,
        content_type=JSON_CONTENT_TYPE,
    )

    client = DiscourseStorageClient(
        host=HOST, api_username=API_USERNAME, api_key=API_KEY
    )

    new_data = {"updated": "content"}
    client.storage.put("existing", new_data)

    # Verify PUT called
    put_call = [c for c in responses.calls if c.request.method == "PUT"][0]

    expected_yaml = yaml.safe_dump(new_data).strip()
    body_str = (
        put_call.request.body
        if isinstance(put_call.request.body, str)
        else put_call.request.body.decode()
    )

    assert quote_plus(expected_yaml) in body_str
