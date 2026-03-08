"""SQLite 기반 영속 체크포인트 저장소."""
import os
from langgraph.checkpoint.sqlite import SqliteSaver


def create_checkpointer():
    """체크포인터를 생성합니다.

    SENTINEL_CHECKPOINT_DIR 환경변수로 저장 위치 지정 (기본: .sentinel/checkpoints)
    SENTINEL_CHECKPOINT_BACKEND 환경변수로 백엔드 선택 (기본: sqlite, memory도 가능)
    """
    backend = os.environ.get("SENTINEL_CHECKPOINT_BACKEND", "sqlite")

    if backend == "memory":
        from langgraph.checkpoint.memory import InMemorySaver
        return InMemorySaver()

    # SQLite
    checkpoint_dir = os.environ.get("SENTINEL_CHECKPOINT_DIR", ".sentinel/checkpoints")
    os.makedirs(checkpoint_dir, exist_ok=True)
    db_path = os.path.join(checkpoint_dir, "sentinel.db")
    return SqliteSaver.from_conn_string(db_path)
