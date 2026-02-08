import pytest
import yaml
from urllib.parse import quote_plus

from client import DiscourseStorageClient, DiscourseStorageError

HOST = "https://discourse.example.com"
API_USERNAME = "testuser"
API_KEY = "secret-key"
JSON_CONTENT_TYPE = "application/json; charset=utf-8"


@pytest.fixture
def client():
    """
    Creates a DiscourseStorageClient.
    By default, this sets up an empty storage (no existing STORAGE_ topics).
    """
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


def test_storage_get_lazy_load_success(client, responses):
    """
    Test flow: Init -> get('settings') -> search for topic -> fetch post -> return content.
    """
    # 1. Mock SEARCH call
    query = quote_plus(f"STORAGE_settings @{API_USERNAME} in:title in:messages")
    responses.add(
        responses.GET,
        f"{HOST}/search.json?q={query}",
        json={"topics": [{"id": 200, "title": "STORAGE_settings"}]},
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

    result = client.storage.get("settings")

    assert result == data_payload
    assert client.storage._storage_ids["settings"] == (200, 555)


def test_storage_get_not_found(client, responses):
    """Test get() returns default when key doesn't exist (search returns empty)."""
    query = quote_plus(f"STORAGE_non_existent @{API_USERNAME} in:title in:messages")
    responses.add(
        responses.GET,
        f"{HOST}/search.json?q={query}",
        json={"topics": []},
        content_type=JSON_CONTENT_TYPE,
    )

    assert client.storage.get("non_existent") == {}
    assert client.storage.get("non_existent", default="foo") == "foo"


def test_storage_get_security_check(client, responses):
    """Ensure we don't read data if the post is not marked as 'yours'."""
    # SEARCH finding a topic
    query = quote_plus(f"STORAGE_hacked @{API_USERNAME} in:title in:messages")
    responses.add(
        responses.GET,
        f"{HOST}/search.json?q={query}",
        json={"topics": [{"id": 300, "title": "STORAGE_hacked"}]},
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

    with pytest.raises(DiscourseStorageError, match="was not created by ourself"):
        client.storage.get("hacked")


def test_storage_put_new_key(client, responses):
    """Test creating a new storage item when search returns nothing."""
    query = quote_plus(f"STORAGE_new_key @{API_USERNAME} in:title in:messages")
    responses.add(
        responses.GET,
        f"{HOST}/search.json?q={query}",
        json={"topics": []},
        content_type=JSON_CONTENT_TYPE,
    )

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


def test_storage_put_existing_key(client, responses):
    """Test updating an existing storage item found via search."""

    # 1. Search finding existing key
    query = quote_plus(f"STORAGE_existing @{API_USERNAME} in:title in:messages")
    responses.add(
        responses.GET,
        f"{HOST}/search.json?q={query}",
        json={"topics": [{"id": 500, "title": "STORAGE_existing"}]},
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

    new_data = {"updated": "content"}
    client.storage.put("existing", new_data)

    # Verify PUT called
    put_call = [c for c in responses.calls if c.request.method == "PUT"][0]

    expected_yaml = yaml.safe_dump(new_data).strip()

    assert quote_plus(expected_yaml) in put_call.request.body


def test_storage_custom_storage_cls(dummy_storage_client):
    client = dummy_storage_client

    client.storage.put("alpha", {"value": 1})
    assert client.storage.get("alpha") == {"value": 1}
