"""Sentinel LLMOps 에이전트 — CLI 엔트리포인트.

사용법:
    # 대화형 모드
    python main.py

    # 단일 질의
    python main.py --query "최근 3일간 트레이스를 분석해주세요"

    # 보고서 생성
    python main.py --query "주간 LLMOps 보고서를 생성해서 저장해주세요"

    # 세션 재개
    python main.py --thread-id my-session

    # JSON 출력 (비대화형)
    python main.py --query "..." --json

    # 결과 파일 저장
    python main.py --query "..." --output result.md
"""

import argparse
import json as json_mod
import os
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


def interactive(agent, thread_id: str | None = None):
    """대화형 모드로 실행합니다."""
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
    parser = argparse.ArgumentParser(
        description="Sentinel — Langfuse LLMOps Agent"
    )
    parser.add_argument(
        "--query", "-q", type=str, default=None, help="단일 질의 (비대화형)"
    )
    parser.add_argument(
        "--thread-id", "-t", type=str, default=None,
        help="세션 스레드 ID (재개 또는 지정)"
    )
    parser.add_argument(
        "--json", action="store_true", default=False,
        help="JSON 형식으로 결과 출력"
    )
    parser.add_argument(
        "--output", "-o", type=str, default=None,
        help="결과를 파일로 저장"
    )
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

        if args.json:
            output = json_mod.dumps(
                {"query": args.query, "result": result},
                ensure_ascii=False, indent=2,
            )
        else:
            output = result

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
