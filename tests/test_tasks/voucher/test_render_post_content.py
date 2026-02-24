from unittest.mock import MagicMock

from src.tasks.voucher import render_post_content


def test_update_voucher_topic_initial_state():
    """
    Given: No vouchers, no demand, no queue
    When: The voucher topic is updated
    Then: The post contains the "Bedarfsermittlung" text
    """
    storage = {}
    post_content = render_post_content(storage)
    assert "Bedarfsermittlung" in post_content
    assert "Interessenten" in post_content


def test_update_voucher_topic_with_demand():
    """
    Given: Some user demands
    When: The voucher topic is updated
    Then: The post contains an alphabetically sorted list of users and their demand
    """
    storage = {
        "demand": {
            "user_c": 1,
            "user_a": 2,
            "user_b": 3,
        }
    }
    post_content = render_post_content(storage)
    assert "Bedarfsermittlung" in post_content
    assert "Interessenten" in post_content
    assert "- @user_a: Insgesamt 2 Voucher" in post_content
    assert "- @user_b: Insgesamt 3 Voucher" in post_content
    assert "- @user_c: Insgesamt 1 Voucher" in post_content
    assert (
        post_content.find("user_a")
        < post_content.find("user_b")
        < post_content.find("user_c")
    )


def test_update_voucher_topic_with_vouchers_and_queue():
    """
    Given: Vouchers and a queue of users
    When: The voucher topic is updated
    Then: The post contains a list of users waiting for a voucher
    """
    storage = {
        "voucher": [
            {"voucher": "VOUCHER1", "owner": None, "received_at": MagicMock()},
        ],
        "queue": ["user_b", "user_a"],
        "demand": {"user_c": 1},
    }
    post_content = render_post_content(storage)
    assert "Warteliste" in post_content
    assert "Aktuelle Warteschlange" in post_content
    assert "- @user_a" in post_content
    assert "- @user_b" in post_content
    assert "Bedarfsliste (alphabetisch sortiert)" in post_content
    assert "- @user_c: noch 1 Voucher" in post_content
    assert (
        post_content.find("Aktuelle Warteschlange")
        < post_content.find("@user_b")
        < post_content.find("@user_a")
        < post_content.find("Bedarfsliste")
    )


def test_update_voucher_topic_with_possessors():
    """
    Given: Vouchers assigned to users
    When: The voucher topic is updated
    Then: The post contains a list of users who currently possess a voucher
    """
    storage = {
        "voucher": [
            {"voucher": "VOUCHER1", "owner": "user_a", "received_at": MagicMock()},
            {"voucher": "VOUCHER2", "owner": "user_b", "received_at": MagicMock()},
        ],
        "queue": [],
        "demand": {},
    }
    post_content = render_post_content(storage)
    assert "#1 | @user_a " in post_content
    assert "#2 | @user_b " in post_content


def test_update_voucher_topic_no_distribution_yet():
    """
    Given: No vouchers have been distributed yet
    When: The voucher topic is updated
    Then: The post has a description for "Bedarfsermittlung"
    """
    storage = {
        "demand": {
            "user_a": 1,
        }
    }
    post_content = render_post_content(storage)
    assert "Bedarfsermittlung" in post_content
    assert "Schreib mir eine PN" in post_content
