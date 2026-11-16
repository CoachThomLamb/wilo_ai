"""Split the eval (ml/toolcall_eval.jsonl) into a held-out test set and seeds for generating training data.

    python ml/split.py      # → ml/test.jsonl (~50), ml/seeds.jsonl (~45)

Stratified by expected tool with a fixed seed: every tool gets at least one test item, then about half of each
tool goes to test. Tools with one item (list_todos, coaching_method) land only in test. Never train on test.jsonl.
Split is per item, not per conversation (15 conversations is too few), so test and seed items can share context.
"""
import json
import random
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SEED = 42


def main():
    items = [json.loads(l) for l in open(HERE / 'toolcall_eval.jsonl')]
    by_tool = defaultdict(list)
    for item in items:
        by_tool[item['expected']['tool'] or 'none'].append(item)

    rng = random.Random(SEED)
    test, seeds = [], []
    for tool in sorted(by_tool):
        group = by_tool[tool]
        rng.shuffle(group)
        k = max(1, (len(group) + 1) // 2)
        test += group[:k]
        seeds += group[k:]

    for name, rows in (('test.jsonl', test), ('seeds.jsonl', seeds)):
        with open(HERE / name, 'w') as f:
            for row in sorted(rows, key=lambda r: r['id']):
                f.write(json.dumps(row, ensure_ascii=False) + '\n')
    print(f'test {len(test)}, seeds {len(seeds)}')
    for tool in sorted(by_tool, key=lambda t: -len(by_tool[t])):
        n_test = sum((r['expected']['tool'] or 'none') == tool for r in test)
        print(f'  {tool:18} test {n_test}  seeds {len(by_tool[tool]) - n_test}')


if __name__ == '__main__':
    main()
