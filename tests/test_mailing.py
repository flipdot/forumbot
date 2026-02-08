import email.message
import pytest
from mailing import read_emails


@pytest.fixture
def mock_imap(mocker):
    mock_imap_class = mocker.patch("mailing.imaplib.IMAP4_SSL")
    mock_instance = mock_imap_class.return_value
    return mock_instance


@pytest.mark.parametrize(
    "delivered_to, expected_task_function, expected_param",
    [
        (
            "bot+voucheringress-testparam@flipdot.org",
            "mailing.process_email_voucheringress",
            "testparam",
        ),
        (
            "bot+voucheringress@flipdot.org",
            "mailing.process_email_voucheringress",
            None,
        ),
        ("bot@flipdot.org", None, None),
        ("someone@example.com", None, None),
        ("bot+unknown-task@flipdot.org", None, None),
        (
            '"Flipbot" <bot+voucheringress-displayname@flipdot.org>',
            "mailing.process_email_voucheringress",
            "displayname",
        ),
    ],
)
def test_read_emails_dispatch(
    mocker,
    mock_imap,
    dummy_storage_client,
    delivered_to,
    expected_task_function,
    expected_param,
):
    # Setup mock IMAP search and fetch
    mock_imap.search.return_value = ("OK", [b"1"])

    msg = email.message.Message()
    msg["Delivered-To"] = delivered_to
    mock_imap.fetch.return_value = ("OK", [(None, msg.as_bytes())])

    if expected_task_function:
        task_function = mocker.patch(expected_task_function)
    else:
        task_function = None

    read_emails(dummy_storage_client)

    if task_function:
        task_function.assert_called_once()
        args, _ = task_function.call_args
        assert args[0] == dummy_storage_client
        assert args[1] == expected_param
        assert args[2]["Delivered-To"] == delivered_to
        assert len(args) == 3


def test_read_emails_imap_interaction(mock_imap, dummy_storage_client):
    mock_imap.search.return_value = ("OK", [b""])

    read_emails(dummy_storage_client)

    mock_imap.login.assert_called_once()
    mock_imap.select.assert_called_with("inbox")
    mock_imap.search.assert_called_once()
