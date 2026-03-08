"""SQLite 기반 영속 체크포인트 저장소."""
import atexit
import os

from langgraph.checkpoint.sqlite import SqliteSaver

_active_checkpointer = None


def create_checkpointer():
    """체크포인터를 생성합니다.

    SENTINEL_CHECKPOINT_DIR 환경변수로 저장 위치 지정 (기본: .sentinel/checkpoints)
    SENTINEL_CHECKPOINT_BACKEND 환경변수로 백엔드 선택 (기본: sqlite, memory도 가능)
    """
    global _active_checkpointer
    backend = os.environ.get("SENTINEL_CHECKPOINT_BACKEND", "sqlite")

    if backend == "memory":
        from langgraph.checkpoint.memory import InMemorySaver
        return InMemorySaver()

    # SQLite
    checkpoint_dir = os.environ.get("SENTINEL_CHECKPOINT_DIR", ".sentinel/checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)
    db_path = os.path.join(checkpoint_dir, "sentinel.db")
    saver = SqliteSaver.from_conn_string(db_path)
    _active_checkpointer = saver
    return saver


def close_checkpointer():
    """활성 체크포인터 커넥션을 명시적으로 닫습니다."""
    global _active_checkpointer
    if _active_checkpointer is not None:
        try:
            if hasattr(_active_checkpointer, "conn") and _active_checkpointer.conn:
                _active_checkpointer.conn.close()
        except Exception:
            pass
        _active_checkpointer = None


atexit.register(close_checkpointer)
