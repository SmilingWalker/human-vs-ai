# -*- coding: utf-8 -*-
"""中文文本 AI 痕迹评分器（de-ai-writing skill 附带）。
用法：py score_ai_flavor.py [--genre general|patent] [--json] 文件.md [文件2 ...]

输出：0-100 AI 痕迹分（0=纯人味，100=重 AI 味）+ 五维度明细。
锚点（--genre general）：<30 人写；30-45 合格改写稿；>55 典型 AI 初稿。

文体参数（--genre）：
  general  通用中文（默认）
  patent   专利/权利要求文体——长句阈值放宽到 90 字（"其特征在于…包括：…；…"
           式法定长句是文体属性不是 AI 味；四篇真人授权专利实测 general 模式
           打 31-48 分，全部偏高在长句维度）
"""
import io
import json
import re
import sys
import statistics

# ---------- 维度1：长句率（随文体调整） ----------
GENRES = {
    'general': {'long': 60, 'long_base': 0.05, 'long_cap': 0.30},
    'patent':  {'long': 90, 'long_base': 0.05, 'long_cap': 0.50},
}

# ---------- 维度2：节奏 ----------
CV_HUMAN = 0.60    # 变异系数达到此值视为人味节奏
CV_AI = 0.40       # 低于此值节奏死板

# ---------- 维度3：修辞模式 ----------
PATTERNS = [
    ('三词金句(可X、可Y)', re.compile(r'可[^，。；、]{2,4}、可[^，。；、]{2,4}(、可[^，。；、]{2,4})?')),
    ('对仗虚词(不X不Y)', re.compile(r'不[^，。；、]{1,6}[，且]?不[^，。；、]{1,6}(?:地|的|而|且|也)')),
    ('总结腔(由此实现了)', re.compile(r'(由此|从而|进而)[^。；]{0,12}(实现|达成|确保|做到)')),
    ('总结腔(这正是)', re.compile(r'(这正是|这就是|可谓是)[^。；]{2,20}')),
    ('强三连排比(更X更Y更Z)', re.compile(r'更[^，。；、]{1,6}、更[^，。；、]{1,6}、更[^，。；、]{1,6}')),
    ('不仅…而且/更是', re.compile(r'不仅[^。；]{2,30}(而且|更是|还是)')),
]

# ---------- 维度4：AI 高频词 ----------
FREQ_WORDS = [
    '值得注意的是', '值得关注的', '综上', '总的来说', '总而言之', '换句话说',
    '旨在', '赋能', '助力', '深耕', '抓手', '闭环', '组合拳', '方法论',
    '显著提升', '大幅提升', '全面提升', '极大地', '深入探讨', '深入理解',
    '让我们', '首先需要', '不可否认', '毋庸置疑', '众所周知', '在当今',
    '日益', '愈发',
]

# ---------- 维度5：抽象堆砌（只抓营销腔伪抽象；技术名词不算） ----------
ABSTRACT_PHRASES = [
    '重要意义', '重要价值', '重要作用', '关键作用', '深远影响', '巨大潜力',
    '强大能力', '强大优势', '显著优势', '核心竞争力', '不可或缺', '无可替代',
    '卓越性能', '优异表现', '良好体验', '极致', '颠覆性',
]
ABSTRACT = re.compile(r'[一-龥]{1,3}感(?![一-龥])')


def sentences(text):
    paras = [p.strip() for p in text.split('\n')]
    paras = [p for p in paras if p and not p.startswith('|') and not p.startswith('　')
             and '｜' not in p and not p.startswith('#') and not p.startswith('!')]
    out = []
    for p in paras:
        for s in re.split(r'(?<=[。！？；])', p):
            s = s.strip()
            if len(s) > 3:
                out.append(s)
    return out


def clamp(x, lo=0.0, hi=1.0):
    return max(lo, min(hi, x))


def score(path, genre='general', as_json=False):
    g = GENRES[genre]
    raw = io.open(path, encoding='utf-8', newline='').read().replace('\r\n', '\n')
    sents = sentences(raw)
    n = len(sents)
    if n < 10:
        msg = f'句子太少（{n}），不评分'
        if as_json:
            return {'file': path, 'error': msg}
        print(f'{path}: {msg}')
        return None
    lens = [len(s) for s in sents]
    chars = len(re.sub(r'\s', '', re.sub(r'[|#*\-]{3,}', '', raw)))

    # 1 长句率
    longs = [s for s in sents if len(s) > g['long']]
    long_rate = len(longs) / n
    s1 = clamp((long_rate - g['long_base']) / (g['long_cap'] - g['long_base'])) * 25

    # 2 节奏
    cv = statistics.stdev(lens) / statistics.mean(lens) if n > 1 else 0
    s2 = clamp((CV_HUMAN - cv) / (CV_HUMAN - CV_AI)) * 20

    # 3 修辞
    pat_hits = [(name, m.group(0)[:24]) for name, pat in PATTERNS for m in pat.finditer(raw)]
    tri = 0
    for s in sents:
        if '=' in s or re.fullmatch(r'[（(【\d.,，/＋＋\-×·^]+', s):
            continue
        commas = len(re.findall(r'、', s))
        if 3 <= commas < 5 and re.search(r'[^，。；、]{3,10}、[^，。；、]{3,10}、[^，。；、]{3,10}、?', s):
            tri += 1
    s3 = clamp((len(pat_hits) + tri) / 8) * 25

    # 4 高频词
    fw_hits = [(w, raw[max(0, m.start()-10):m.end()+10].replace('\n', ' ')[:36])
               for w in FREQ_WORDS for m in re.finditer(w, raw)]
    density = len(fw_hits) / (chars / 1000)
    s4 = clamp(density / 3) * 20

    # 5 抽象
    ab_hits = [m.group(0) for m in ABSTRACT.finditer(raw)]
    ab_hits += [w for w in ABSTRACT_PHRASES if w in raw]
    s5 = clamp((len(ab_hits) / (chars / 1000)) / 5) * 10

    total = s1 + s2 + s3 + s4 + s5
    verdict = '人味' if total < 30 else ('合格' if total < 45 else ('偏AI' if total < 55 else '重AI'))

    result = {
        'file': path, 'genre': genre, 'score': round(total), 'verdict': verdict,
        'long_sentences': {'points': round(s1, 1), 'of': 25, 'rate': f'{long_rate*100:.1f}%',
                           'detail': f'{len(longs)}/{n} 句超{g["long"]}字'},
        'rhythm': {'points': round(s2, 1), 'of': 20, 'cv': round(cv, 2)},
        'rhetoric': {'points': round(s3, 1), 'of': 25, 'patterns': len(pat_hits), 'triples': tri,
                     'hits': [f'{a}: {b}' for a, b in pat_hits[:6]]},
        'freq_words': {'points': round(s4, 1), 'of': 20, 'count': len(fw_hits),
                       'per_1k': round(density, 2), 'hits': [f'{a}: …{b}…' for a, b in fw_hits[:6]]},
        'abstract': {'points': round(s5, 1), 'of': 10, 'hits': ab_hits[:8]},
        'stats': {'sentences': n, 'mean_len': round(statistics.mean(lens)),
                  'max_len': max(lens), 'chars': chars},
    }
    if as_json:
        return result

    print(f'==== {path}')
    print(f'AI 痕迹分: {total:.0f}/100 ({verdict})  [genre={genre}]')
    print(f'  长句率[{s1:5.1f}/25]  {long_rate*100:.1f}%（{len(longs)}/{n} 句超{g["long"]}字）')
    print(f'  节奏  [{s2:5.1f}/20]  变异系数 {cv:.2f}（人味≥{CV_HUMAN}）')
    print(f'  修辞  [{s3:5.1f}/25]  模式{len(pat_hits)}处 + 三连{tri}处')
    for name, frag in pat_hits[:6]:
        print(f'         - {name}: {frag}')
    print(f'  高频词[{s4:5.1f}/20]  {len(fw_hits)}处 / {chars}字 = {density:.2f}处每千字')
    for w, ctx in fw_hits[:6]:
        print(f'         - {w}: …{ctx}…')
    print(f'  抽象  [{s5:5.1f}/10]  {len(ab_hits)}处: {ab_hits[:8]}')
    print(f'  统计: {n}句 均值{statistics.mean(lens):.0f}字 最长{max(lens)}字 全文{chars}字')
    print()
    return result


def main():
    args = sys.argv[1:]
    genre, as_json, files = 'general', False, []
    i = 0
    while i < len(args):
        if args[i] == '--genre':
            i += 1
            genre = args[i] if i < len(args) else 'general'
        elif args[i] == '--json':
            as_json = True
        else:
            files.append(args[i])
        i += 1
    if not files:
        print(__doc__)
        sys.exit(1)
    if genre not in GENRES:
        print(f'未知文体: {genre}，可选 {list(GENRES)}')
        sys.exit(1)
    results = [r for r in (score(f, genre, as_json) for f in files)]
    if as_json:
        print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
