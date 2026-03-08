"""config 모듈 lazy 초기화 테스트."""

import importlib
from unittest.mock import patch, MagicMock


class TestConfigLazyInit:
    """config.py import 시 외부 서비스에 연결하지 않음을 검증."""

    def test_import_does_not_create_model(self):
        """import sentinel.config 시 _create_model()이 호출되지 않아야 함."""
        import sentinel.config as cfg
        # _model은 None이어야 함 (lazy)
        assert cfg._model is None

    def test_import_does_not_create_langfuse(self):
        """import sentinel.config 시 Langfuse()가 호출되지 않아야 함."""
        import sentinel.config as cfg
        assert cfg._lf_client is None

    def test_get_model_creates_on_first_call(self):
        """get_model() 호출 시 모델이 생성됨."""
        import sentinel.config as cfg
        # 테스트 후 원복을 위해 저장
        original = cfg._model
        try:
            cfg._model = None
            mock_model = MagicMock()
            with patch.object(cfg, "_create_model", return_value=mock_model):
                result = cfg.get_model()
                assert result is mock_model
                # 두 번째 호출은 캐시된 값 반환
                result2 = cfg.get_model()
                assert result2 is mock_model
        finally:
            cfg._model = original

    def test_module_getattr_backward_compat(self):
        """from sentinel.config import model 하위 호환."""
        import sentinel.config as cfg
        original = cfg._model
        try:
            cfg._model = None
            mock_model = MagicMock()
            with patch.object(cfg, "_create_model", return_value=mock_model):
                # __getattr__을 통한 접근
                assert cfg.model is mock_model
        finally:
            cfg._model = original
