"""통합 알림 서비스 테스트."""

from unittest.mock import patch, MagicMock

from sentinel.services.notify import (
    Level,
    LEVEL_EMOJI,
    send_telegram_message,
    send_email_message,
    send_notification,
)


class TestLevel:
    """Level 열거형 및 이모지 매핑."""

    def test_level_values(self):
        assert Level.info == "info"
        assert Level.warning == "warning"
        assert Level.critical == "critical"

    def test_level_emoji_mapping(self):
        assert LEVEL_EMOJI[Level.info] == "ℹ️"
        assert LEVEL_EMOJI[Level.warning] == "⚠️"
        assert LEVEL_EMOJI[Level.critical] == "🚨"


class TestTelegramMessage:
    """Telegram 범용 메시지 전송."""

    def test_returns_false_without_env(self):
        with patch.dict("os.environ", {}, clear=True):
            assert send_telegram_message("test", "msg") is False

    @patch("sentinel.services.notify.httpx.post")
    def test_sends_message(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"ok": True}
        mock_post.return_value = mock_resp

        env = {
            "SENTINEL_TELEGRAM_BOT_TOKEN": "tok",
            "SENTINEL_TELEGRAM_CHAT_ID": "123",
        }
        with patch.dict("os.environ", env, clear=False):
            result = send_telegram_message("Title", "Body", Level.warning, "src")
        assert result is True
        mock_post.assert_called_once()
        call_json = mock_post.call_args.kwargs.get("json") or mock_post.call_args[1]["json"]
        assert "Title" in call_json["text"]


class TestEmailMessage:
    """Email 범용 메시지 전송."""

    def test_returns_false_without_env(self):
        with patch.dict("os.environ", {}, clear=True):
            assert send_email_message("test", "msg") is False

    @patch("sentinel.services.notify.smtplib.SMTP")
    def test_sends_email(self, mock_smtp_cls):
        mock_server = MagicMock()
        mock_smtp_cls.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp_cls.return_value.__exit__ = MagicMock(return_value=False)

        env = {
            "SENTINEL_SMTP_HOST": "smtp.test.com",
            "SENTINEL_SMTP_PORT": "587",
            "SENTINEL_SMTP_USER": "user",
            "SENTINEL_SMTP_PASS": "pass",
            "SENTINEL_EMAIL_TO": "to@test.com",
        }
        with patch.dict("os.environ", env, clear=False):
            result = send_email_message("Title", "Body")
        assert result is True
        mock_server.send_message.assert_called_once()


class TestSendNotification:
    """send_notification 통합 디스패치."""

    @patch("sentinel.services.notify.send_email_message", return_value=True)
    @patch("sentinel.services.notify.send_telegram_message", return_value=True)
    def test_all_channels(self, mock_tg, mock_email):
        results = send_notification("t", "m", channel="all")
        assert results["telegram"] is True
        assert results["email"] is True

    @patch("sentinel.services.notify.send_telegram_message", return_value=True)
    def test_single_channel(self, mock_tg):
        results = send_notification("t", "m", channel="telegram")
        assert results["telegram"] is True
        assert "email" not in results

    @patch("sentinel.services.notify.send_telegram_message", side_effect=Exception("fail"))
    def test_error_handling(self, mock_tg):
        results = send_notification("t", "m", channel="telegram")
        assert results["telegram"] is False
