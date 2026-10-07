# human-vs-ai

人写的中文，和模型生成的中文，读起来差在哪？能不能量化？能不能改回去？

这个仓库给出一套实测校准过的答案：**de-ai-writing** —— 中文 AI 痕迹评分器 + 去味改写规则（以 agent skill 形式交付，可用于 Claude Code / ZCode 等）。

## 快速开始

```bash
# 评一个文件（0=纯人味，100=重AI味）
py de-ai-writing/scripts/score_ai_flavor.py 你的文档.md

# 评权利要求/专利文本（长句阈值放宽，见下文"为什么需要文体参数"）
py de-ai-writing/scripts/score_ai_flavor.py --genre patent 权利要求.txt

# 机器可读输出
py de-ai-writing/scripts/score_ai_flavor.py --json 你的文档.md

# 跑回归测试（12 项断言）
py tests/eval_scores.py
```

## 分数怎么看

| 区间 | 判定 |
|---|---|
| < 30 | 人味 |
| 30-45 | 合格改写稿 |
| > 55 | 典型 AI 初稿 |

五个维度加权：长句率 25 / 节奏波动 20 / 修辞模式 25 / AI 高频词 20 / 抽象堆砌 10。

## 校准数据

| 文本 | 得分 | 说明 |
|---|---|---|
| 合成重 AI 营销腔 | 71 | "值得注意的是/赋能/核心竞争力" |
| 未经去味的 AI 技术稿 | 35 | AI 起草、未人工修写 |
| **真人写的授权专利 ×4** | **31-48** | CN121166358A / CN119917319B / CN120338035B / CN121724138A |
| 人写的技术交底书 | 20 | 作为人味基准 |
| 去味改写后的技术稿 | 19 | 比真人写的还素 |

两个反直觉发现：

1. **真人写的专利，AI 痕迹分反而偏高**——扣分几乎全在长句维度。权利要求的法定句式（"其特征在于……包括：……；……"）天然是 76 字均值的长复合句。同一份权利要求文本，general 模式打 47，patent 模式打 24，所以评分器加了 `--genre` 参数。
2. **真人专利的修辞/套话维度接近零**——专业代理人不写"值得注意的是"，不写排比金句。反过来说：AI 稿的问题恰好是修辞维度爆表 + 长句双杀，两个维度分开了。

## 去味改写规则（SKILL.md 精华）

模式按强度分级（源自 humanizer 的分级制）：

- **A级**（出现一处改一处）：超长复合句 / 三词金句（"可计算、可审计"）/ 对仗虚词（"不虚高也不被排除"）/ 总结腔收尾 / 强行三连排比
- **B级**（段内多处才改）：AI 高频词 / 翻译腔被动 / 抽象名词堆砌 / 铺垫式开场
- **C级**（叠加才动）："的"字连串 / 括号过密 / 均匀句长

以及最重要的——**防过洗五红线**（开源社区实测教训："洗到最后文章确实没 AI 味了，也没人的味了"）：

1. 术语不动（"委派深度"是精确性，不是 AI 味）
2. 行业格式套话不动（专利三段式、引证句式）
3. 不引入口水话（目标是平实，不是贫嘴）
4. 数据/公式/列举不动（那是信息密度）
5. 改完必须复评 + 抽读三段

## 双评估流程（推荐用法）

脚本评分抓固定模式，LLM 盲评抓宏观模板，能力不重叠。实测中 LLM 盲评抓到了评分器测不到的问题：五段引证全部用"不涉及X，也不涉及Y"同一节拍收尾，"五段连读就露出同一支笔"。流程：

```
脚本评分 → 按 SKILL.md 模式表改写 → 复评（分数必须降）
        → 独立 LLM 盲评（不带脚本分数，避免锚定）→ 修其指出残留 → 再复评
        → 分数低于人味基准即停（防过洗）
```

实测一轮完整流程：AI 初稿 35 → 改写 19（脚本）/ 48 → 18（LLM 盲评）。

## 目录结构

```
de-ai-writing/
├── SKILL.md                    # 检测-改写-评分完整规则（skill 本体）
└── scripts/
    └── score_ai_flavor.py      # 评分器（--genre general|patent, --json）
tests/
├── eval_scores.py              # 12 项回归断言
└── fixtures/                   # 合成测试样本（AI腔/权利要求体/干净技术文）
```

## 致谢与来源

规则整合自开源社区的去 AI 味工作，按本仓库实测数据重新校准：

- [humanizer](https://github.com/blader/humanizer) —— 26 模式分级制（源自 Wikipedia "Signs of AI writing"）
- [humanizer-zh](https://skills.rest) —— 中文模板句/总结腔/翻译腔/大厂黑话
- [stop-slop](https://skills.rest) —— 直接性/节奏/信任读者/删金句

## 局限

- 评分器不做 AI 检测（不以骗过检测器为目标；humanizer 同样立场）
- 修辞/高频词维度的词典是中文互联网向的，其他语言无效
- 技术文本的"节奏"维度普遍低区分度（技术文本本来就句长均匀），区分力主要来自修辞+高频词+长句率
- 校准锚点基于技术文档与专利文体，评散文/小说需重新定标

## SkillsBench 评测（阿里魔搭 EvalScope）

本仓库的 `skillsbench-tasks/de-ai-writing/` 是一个标准的 [SkillsBench](https://evalscope.readthedocs.io/zh-cn/latest/third_party/skillsbench.html) 任务包，可用 [EvalScope](https://github.com/modelscope/evalscope) 框架评测 skill 的真实增益：

```bash
pip install "evalscope[sandbox]"   # 需本地 Docker

# oracle 冒烟（验证任务包与 verifier 契约，已实测 100%）
py -c "from evalscope import TaskConfig, run_task; run_task(TaskConfig( \
    model='dummy', datasets=['skillsbench'], limit=1, \
    dataset_args={'skillsbench': {'extra_params': { \
        'tasks_dir': 'skillsbench-tasks', 'task_ids': ['de-ai-writing'], \
        'runner': 'oracle', 'skill_mode': 'no-skill'}}}}))"

# 真实 agent 对比（测 skill 的 lift：分别跑 no-skill 与 with-skill 再比分数）
#   把 skill_mode 分别设为 'no-skill' / 'with-skill'，agent_config 配置你的 agent
```

任务设计：agent 拿到一份 AI 痕迹分 76 的技术文档（`environment/workspace/input.txt`），须改写到 22 分以下，同时保留全部术语与信息量。verifier 打分构成：

- 40% 输出完整（长度 0.7-1.1 倍 + 相似度 ≤0.85，防止原文照抄骗分）
- 30% AI 痕迹分 < 22（由本仓库评分器独立副本判定）
- 30% 术语保留 ≥ 8/10（防止过洗丢术语）

三组 sanity 实测：oracle 参考改写 = 1.00；原文照抄 = 0.00（反作弊拦截）；未改写直交 = 0.00。

### 多文体任务集（v2）

去 AI 味不是技术文档的专利。任务集扩展到四种文体，AI 味形态各不相同：

| 任务 | 文体 | 输入基准分 | 典型病灶 | oracle 人味分 |
|---|---|---|---|---|
| de-ai-writing | 技术文档 | 76 | 长句堆叠+金句排比 | 18 |
| blog-ci-speedup | 技术博客 | 63 | 铺垫开场+每段总结收尾 | 1 |
| product-copy | 产品文案 | 57 | 赋能体+口号排比 | 16 |
| weekly-report | 工作周报 | 39 | 公文腔+模糊量化 | 4 |

评分器词典据此扩充了两类：营销腔（"保驾护航、重新定义、划时代、无缝衔接"等）与公文腔（"丰硕成果、攻坚克难、再创佳绩、注入动力"等），另加"选择X就是选择Y"式口号排比检测。锚点回归 12/12 不漂移（技术文不含这些词，互不干扰）。

verifier 同步修复：各维度独立判分（旧版长度比差 1% 即全盘归零，实测一轮博客改写 0.69 比率被误杀）。

### 真实 agent 评测结果（deepseek-v4.1-flash，阈值 22）

四文体 × 双模式完整结果（deepseek-v4.1-flash）：

| 任务 | 文体 | no-skill | with-skill | lift |
|---|---|---|---|---|
| de-ai-writing | 技术文档 | 0.70（n=3） | **0.85**（n=2） | +0.15 |
| blog-ci-speedup | 技术博客 | 0.30 | **1.00** | **+0.70** |
| product-copy | 产品文案 | 0.30 | **1.00** | **+0.70** |
| weekly-report | 工作周报 | 1.00 | 1.00（首轮 0 为执行故障，重跑 1.00） | 0（双顶格） |
| oracle 参照 | 四任务全 | — | 1.00 | — |

三条结论：

1. **AI 味越重的文体，skill 增益越大**。博客与营销文案的 no-skill 只有 0.30（连改写门槛都没过——长度/防抄维度失守），with-skill 用评分器自测迭代直接满分，lift +0.70。
2. **轻度 AI 味文体双模式顶格**（周报基准分仅 39）：裸模型就能改好，skill 无害亦无增益。
3. **执行稳定性是 flash 级模型的水位线**：with-skill 周报首轮因 agent 陷入反复分析（trace 显示 23 次 python3 -c 分析句长、耗尽 15 步预算未写文件）判 0，重跑满分——评测报告如实记录，不掩盖。

两条经验：

1. **任务难度必须校准到模型能力边界**。阈值 35 时两种模式双满分（天花板效应，lift=0）；收到 22 后区分度才出现。22 的依据：人写技术交底书基准约 20，人工多轮改写稿约 19。
2. **本任务里 skill 的核心价值是"可自测的量化工具"**。SKILL.md 的规则清单 agent 只能参考，但评分器让 agent 从"盲改"变成"带反馈的迭代逼近"——这是 no-skill 与 with-skill 的本质差别。剩余波动（23 vs 19）来自 flash 级模型的执行稳定性，更大模型或更多轮次会收敛。
