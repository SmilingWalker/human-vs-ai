# -*- coding: utf-8 -*-
"""de-ai-writing 任务 verifier 判分逻辑（容器内由 test.sh 调用）。
reward 协议：把 0-1 分数写入 /logs/verifier/reward.txt（SkillsBench 契约）。
构成：输出完整性 0.4 + AI痕迹分<35 0.3 + 术语保留率 0.3。"""
import difflib
import io
import json
import os
import re
import subprocess
import sys

WS = os.environ.get('DEAI_WS', '/workspace')
REWARD_PATH = os.environ.get('DEAI_REWARD', '/logs/verifier/reward.txt')
OUT = os.path.join(WS, 'output.md')
INP = os.path.join(WS, 'input.txt')
SCORER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'scorer.py')

TERMS = ['状态机', '23 种', '91%', '幂等键', '0.8%', '0.05%', 'P95', '380', '复合索引', '消息队列']


def main():
    reward = 0.0
    notes = []

    # 1) 输出完整性 0.4：存在 + 长度比 + 发生过实质改写（防原文照抄骗分）
    ok = False
    out = inp = ''
    if os.path.isfile(OUT):
        out = io.open(OUT, encoding='utf-8').read()
        inp = io.open(INP, encoding='utf-8').read()
        n_out = len(re.sub(r'\s', '', out))
        n_in = len(re.sub(r'\s', '', inp))
        sim = difflib.SequenceMatcher(None, inp, out).ratio()
        if n_out > 0 and 0.7 <= n_out / n_in <= 1.1:
            if sim <= 0.85:
                ok = True
                notes.append(f'length {n_out}/{n_in}, similarity {sim:.2f} (rewritten)')
            else:
                notes.append(f'similarity {sim:.2f} too close to input (copy?)')
        else:
            notes.append(f'length ratio {n_out/n_in:.2f} out of [0.7,1.1]')
    else:
        notes.append('output.md missing')
    if ok:
        reward += 0.4

    # 2) AI 痕迹分 < 35 → 0.3
    if ok:
        r = subprocess.run([sys.executable, SCORER, '--json', OUT],
                           capture_output=True, text=True, encoding='utf-8')
        try:
            res = json.loads(r.stdout)[0]
            score = res.get('score')
            if score is not None and score < 22:
                reward += 0.3
                notes.append(f'ai-flavor score {score} < 22')
            else:
                notes.append(f'ai-flavor score {score} not < 22')
        except Exception as e:
            notes.append(f'scorer error: {e}')

    # 3) 术语保留 ≥ 8/10 → 0.3（独立判分）
    if os.path.isfile(OUT):
        hits = sum(1 for t in TERMS if t in out)
        if hits >= 8:
            reward += 0.3
        notes.append(f'terms kept {hits}/10')

    print('; '.join(notes) if notes else 'no notes')
    os.makedirs(os.path.dirname(REWARD_PATH), exist_ok=True)
    with io.open(REWARD_PATH, 'w', encoding='utf-8') as f:
        f.write(f'{reward:.2f}\n')
    print(f'reward = {reward:.2f}')


if __name__ == '__main__':
    main()
