"""
批量评估流水线 — 基于 asyncio 的高并发题目生成

用法:
    # 生成 100 道题（随机 topic + difficulty）
    python batch_eval.py --count 100 --concurrency 5

    # 生成 1000 道题，断点续传
    python batch_eval.py --count 1000 --concurrency 8 --resume

    # 自定义输出路径
    python batch_eval.py --count 500 --output dataset/math_bank.jsonl
"""

import asyncio
import json
import random
import time
import argparse
from pathlib import Path

from async_agent import AsyncHigherAlgebraProfessorAgent

TOPICS = [
    "矩阵的初等变换与秩",
    "实对称矩阵的对角化",
    "二次型及其标准形",
    "线性空间的基与维数",
    "线性变换的特征值与特征向量",
]


def _load_completed_indices(output_path: Path) -> set:
    """从已有 JSONL 文件中读取已完成的索引，支持断点续传"""
    if not output_path.exists():
        return set()
    completed = set()
    with open(output_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
                meta = record.get("_meta", {})
                if "index" in meta:
                    completed.add(meta["index"])
            except json.JSONDecodeError:
                continue
    return completed


def _save_one(output_path: Path, result: dict):
    """追加一条结果到 JSONL 文件（线程安全由 asyncio 事件循环保证）"""
    with open(output_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(result, ensure_ascii=False) + "\n")


async def batch_generate(
    tasks_spec: list[tuple[int, str, int]],
    concurrency: int = 5,
    output_path: str = "batch_results.jsonl",
    resume: bool = False,
):
    """
    异步批量生成题目。

    Args:
        tasks_spec: [(index, topic, difficulty), ...] 任务规格列表
        concurrency: 最大并发数
        output_path: JSONL 输出路径
        resume: 是否跳过已完成的 index
    """
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    completed = _load_completed_indices(out_path) if resume else set()
    pending = [(i, t, d) for i, t, d in tasks_spec if i not in completed]

    if completed:
        print(f"[Resume] 跳过已完成的 {len(completed)} 题，剩余 {len(pending)} 题")

    if not pending:
        print("所有任务已完成，无需继续。")
        return

    agent = AsyncHigherAlgebraProfessorAgent()
    semaphore = asyncio.Semaphore(concurrency)

    success_count = 0
    fail_count = 0
    done_count = len(completed)
    total = len(tasks_spec)
    start_time = time.time()

    async def generate_one(index: int, topic: str, difficulty: int):
        nonlocal success_count, fail_count, done_count

        async with semaphore:
            try:
                data = await agent.generate_verified_problem(topic, difficulty)
                if data:
                    data["_meta"] = {
                        "index": index,
                        "topic": topic,
                        "difficulty": difficulty,
                    }
                    _save_one(out_path, data)
                    success_count += 1
                else:
                    fail_count += 1
                    _save_one(
                        out_path,
                        {
                            "_meta": {
                                "index": index,
                                "topic": topic,
                                "difficulty": difficulty,
                                "status": "failed",
                            }
                        },
                    )
            except Exception as e:
                fail_count += 1
                _save_one(
                    out_path,
                    {
                        "_meta": {
                            "index": index,
                            "topic": topic,
                            "difficulty": difficulty,
                            "status": "error",
                            "error": str(e),
                        }
                    },
                )

            done_count += 1
            elapsed = time.time() - start_time
            rate = done_count / elapsed if elapsed > 0 else 0
            print(
                f"[进度] {done_count}/{total} | "
                f"成功 {success_count} 失败 {fail_count} | "
                f"速率 {rate:.2f} 题/秒 | "
                f"已耗时 {elapsed:.0f}s"
            )

    tasks = [generate_one(i, t, d) for i, t, d in pending]
    await asyncio.gather(*tasks, return_exceptions=True)

    elapsed = time.time() - start_time
    print(f"\n{'='*60}")
    print(f"批量评估完成")
    print(f"  总计: {total} | 成功: {success_count} | 失败: {fail_count}")
    print(f"  总耗时: {elapsed:.0f}s | 平均: {elapsed/total:.1f}s/题")
    print(f"  输出: {out_path.resolve()}")


def main():
    parser = argparse.ArgumentParser(description="MathGen-Agent 批量评估流水线")
    parser.add_argument(
        "--count", type=int, default=100, help="生成题目总数（默认 100）"
    )
    parser.add_argument(
        "--concurrency", type=int, default=5, help="最大并发数（默认 5）"
    )
    parser.add_argument(
        "--output", type=str, default="batch_results.jsonl", help="JSONL 输出路径"
    )
    parser.add_argument(
        "--resume", action="store_true", help="断点续传：跳过输出文件中已完成的 index"
    )
    parser.add_argument(
        "--seed", type=int, default=None, help="随机种子（用于复现）"
    )
    args = parser.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    # 构建任务规格：随机分配 topic 和 difficulty
    tasks_spec = [
        (i, random.choice(TOPICS), random.randint(1, 5))
        for i in range(args.count)
    ]

    print(f"批量生成配置:")
    print(f"  题目数: {args.count}")
    print(f"  并发度: {args.concurrency}")
    print(f"  输出: {args.output}")
    print(f"  续传: {'是' if args.resume else '否'}")
    print(f"  Topics: {TOPICS}")
    print()

    asyncio.run(
        batch_generate(
            tasks_spec=tasks_spec,
            concurrency=args.concurrency,
            output_path=args.output,
            resume=args.resume,
        )
    )


if __name__ == "__main__":
    main()
