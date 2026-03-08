"""Sentinel LLMOps 에이전트 — CLI 엔트리포인트.

사용법:
    uv run python -m sentinel.cli
    uv run python -m sentinel.cli --query "최근 트레이스 분석해줘"
"""

import argparse
import json as json_mod
import sys
import uuid

from sentinel.agent import create_sentinel_agent
from sentinel.config import lf_config


def run_query(agent, query: str, thread_id: str | None = None):
    tid = thread_id or str(uuid.uuid4())[:8]
    config = {"configurable": {"thread_id": f"sentinel-{tid}"}, **lf_config}
    response = agent.invoke(
        {"messages": [{"role": "user", "content": query}]},
        config=config,
    )
    return response["messages"][-1].content


def interactive(agent, thread_id: str | None = None):
    print("=" * 60)
    print("  Sentinel — Langfuse LLMOps Agent")
    print("  명령어: quit/exit (종료), clear (대화 초기화)")
    print("=" * 60)

    tid = thread_id or str(uuid.uuid4())[:8]

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
            tid = str(uuid.uuid4())[:8]
            print("대화를 초기화했습니다.")
            continue

        try:
            result = run_query(agent, query, tid)
            print(f"\n[Sentinel]\n{result}")
        except KeyboardInterrupt:
            print("\n질의가 취소되었습니다.")
        except Exception as e:
            print(f"\n[오류] 질의 실행 실패: {e}")
            print("다시 시도하거나 clear로 대화를 초기화하세요.")


def main():
    parser = argparse.ArgumentParser(description="Sentinel — Langfuse LLMOps Agent")
    parser.add_argument("--query", "-q", type=str, default=None, help="단일 질의 (비대화형)")
    parser.add_argument("--thread-id", "-t", type=str, default=None, help="세션 스레드 ID")
    parser.add_argument("--json", action="store_true", default=False, help="JSON 출력")
    parser.add_argument("--output", "-o", type=str, default=None, help="결과 파일 저장")
    args = parser.parse_args()

    print("Sentinel 에이전트를 초기화하는 중...", file=sys.stderr)
    try:
        agent = create_sentinel_agent()
    except Exception as e:
        print(f"에이전트 초기화 실패: {e}", file=sys.stderr)
        sys.exit(1)
    print("초기화 완료.\n", file=sys.stderr)

    if args.query:
        try:
            result = run_query(agent, args.query, args.thread_id)
        except Exception as e:
            print(f"질의 실행 실패: {e}", file=sys.stderr)
            sys.exit(1)

        output = (
            json_mod.dumps({"query": args.query, "result": result}, ensure_ascii=False, indent=2)
            if args.json else result
        )

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output)
            print(f"결과 저장: {args.output}", file=sys.stderr)
        else:
            print(output)
    else:
        interactive(agent, args.thread_id)


if __name__ == "__main__":
    main()
