"""Sentinel LLMOps 에이전트 — CLI 엔트리포인트.

사용법:
    # 대화형 모드
    python main.py

    # 단일 질의
    python main.py --query "최근 3일간 트레이스를 분석해주세요"

    # 보고서 생성
    python main.py --query "주간 LLMOps 보고서를 생성해서 저장해주세요"
"""

import argparse
import sys
import uuid

from sentinel.agent import create_sentinel_agent
from sentinel.config import lf_config


def run_query(agent, query: str, thread_id: str | None = None):
    """단일 질의를 실행하고 결과를 출력합니다."""
    tid = thread_id or str(uuid.uuid4())[:8]
    config = {"configurable": {"thread_id": f"sentinel-{tid}"}, **lf_config}
    response = agent.invoke(
        {"messages": [{"role": "user", "content": query}]},
        config=config,
    )
    return response["messages"][-1].content


def interactive(agent):
    """대화형 모드로 실행합니다."""
    print("=" * 60)
    print("  Sentinel — Langfuse LLMOps Agent")
    print("  명령어: quit/exit (종료), clear (대화 초기화)")
    print("=" * 60)

    thread_id = str(uuid.uuid4())[:8]

    while True:
        try:
            query = input("\n[You] ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n종료합니다.")
            break

        if not query:
            continue
        if query.lower() in ("quit", "exit"):
            print("종료합니다.")
            break
        if query.lower() == "clear":
            thread_id = str(uuid.uuid4())[:8]
            print("대화를 초기화했습니다.")
            continue

        result = run_query(agent, query, thread_id)
        print(f"\n[Sentinel]\n{result}")


def main():
    parser = argparse.ArgumentParser(
        description="Sentinel — Langfuse LLMOps Agent"
    )
    parser.add_argument(
        "--query", "-q", type=str, default=None, help="단일 질의 (비대화형)"
    )
    args = parser.parse_args()

    print("Sentinel 에이전트를 초기화하는 중...")
    agent = create_sentinel_agent()
    print("초기화 완료.\n")

    if args.query:
        result = run_query(agent, args.query)
        print(result)
    else:
        interactive(agent)


if __name__ == "__main__":
    main()
