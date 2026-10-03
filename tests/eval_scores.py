# -*- coding: utf-8 -*-
"""de-ai-writing skill 能力回归测试。
用法：py tests/eval_scores.py
断言锚点来自真实校准（详见 README 校准表）：
  重AI营销腔 > 55 | 干净技术短句 < 30 | 专利文体 patent 模式应显著低于 general 模式
另测：JSON 输出可解析、短文本不崩溃、未知文体报错退出。
"""
import json
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
FIX = os.path.join(HERE, 'fixtures')
SCORER = os.path.join(HERE, '..', 'de-ai-writing', 'scripts', 'score_ai_flavor.py')
PY = sys.executable

PASS, FAIL = [], []


def run(args):
    r = subprocess.run([PY, SCORER] + args, capture_output=True, text=True, encoding='utf-8')
    return r


def run_json(path, genre='general'):
    r = run(['--genre', genre, '--json', path])
    assert r.returncode == 0, f'scorer exited {r.returncode}: {r.stderr[:200]}'
    out = json.loads(r.stdout)
    assert isinstance(out, list) and len(out) == 1
    return out[0]


def check(name, cond, detail=''):
    (PASS if cond else FAIL).append(name)
    print(('PASS ' if cond else 'FAIL ') + name + (f'  [{detail}]' if detail else ''))


# ---- 1. 锚点区间 ----
slop = run_json(os.path.join(FIX, 'ai_slop.txt'))
check('重AI营销腔 > 55', slop['score'] > 55, f"score={slop['score']}")

clean = run_json(os.path.join(FIX, 'tech_clean.txt'))
check('干净技术短句 < 30', clean['score'] < 30, f"score={clean['score']}")

# ---- 2. 专利文体豁免 ----
claims_g = run_json(os.path.join(FIX, 'patent_claims.txt'), 'general')
claims_p = run_json(os.path.join(FIX, 'patent_claims.txt'), 'patent')
check('专利文体 patent 模式比 general 至少低 8 分',
      claims_p['score'] <= claims_g['score'] - 8,
      f"general={claims_g['score']} patent={claims_p['score']}")
check('专利文体 patent 模式落人味/合格区间（<45）',
      claims_p['score'] < 45, f"patent={claims_p['score']}")
def rate_num(res):
    return float(res['long_sentences']['rate'].rstrip('%'))

check('patent 模式长句阈值生效（阈值=90）',
      rate_num(claims_p) < rate_num(claims_g),
      f"g_rate={claims_g['long_sentences']['rate']} p_rate={claims_p['long_sentences']['rate']}")

# ---- 3. 维度方向性 ----
check('AI腔的高频词维度≥15/20', slop['freq_words']['points'] >= 15,
      f"points={slop['freq_words']['points']}")
check('AI腔的修辞维度≥10/25', slop['rhetoric']['points'] >= 10,
      f"points={slop['rhetoric']['points']}")
check('干净文本修辞维度=0', clean['rhetoric']['points'] == 0,
      f"points={clean['rhetoric']['points']}")
check('干净文本高频词维度=0', clean['freq_words']['points'] == 0,
      f"points={clean['freq_words']['points']}")

# ---- 4. 健壮性 ----
with tempfile.NamedTemporaryFile('w', suffix='.txt', delete=False, encoding='utf-8') as f:
    f.write('只有一句话。')
    tiny = f.name
r = run_json(tiny)
check('超短文本不崩溃且有 error', 'error' in r, str(r.get('error')))
os.unlink(tiny)

r = run(['--genre', 'unknown', os.path.join(FIX, 'ai_slop.txt')])
check('未知文体报错退出（exit!=0）', r.returncode != 0)

r = run([])
check('无参数打印用法并退出', r.returncode == 1 and '用法' in r.stdout)

# ---- 汇总 ----
print(f'\n{"="*40}\n{len(PASS)} passed, {len(FAIL)} failed')
if FAIL:
    print('FAILED:', '; '.join(FAIL))
    sys.exit(1)
