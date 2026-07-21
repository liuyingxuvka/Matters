# Matters

[![Release](https://img.shields.io/github/v/release/liuyingxuvka/Matters?display_name=tag)](https://github.com/liuyingxuvka/Matters/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)](https://www.python.org/)
[![Windows desktop](https://img.shields.io/badge/Windows-desktop-0078D4)](https://github.com/liuyingxuvka/Matters/releases/latest)
[![License](https://img.shields.io/badge/license-MIT-8A2BE2)](./LICENSE)

[English](#english) · [简体中文](#简体中文)

<!-- README HERO START -->
<p align="center">
  <img src="./docs/assets/readme-hero/hero.png" alt="Matters turns information from user-authorized sources into traceable Matter and event models" width="100%" />
</p>

<p align="center">
  <strong>Turn authorized information into auditable Matter models for people and AI.</strong>
</p>
<!-- README HERO END -->

## English

### What Matters is

Matters is a local-first application that turns clues from user-authorized
information sources into explicit **Matter and event models**. Instead of
leaving related records scattered across files, messages, projects, and
connected services, it reconstructs the larger situation: its people, time,
stages, sub-matters, relationships, open loops, outcomes, and supporting
sources.

The result is not a black-box summary. Important conclusions remain connected
to their source location, time basis, uncertainty, inference status, correction
history, and current freshness. They can be audited, traced, inspected, and
re-evaluated when new clues arrive.

### How information becomes a Matter

1. **Authorize** — the user explicitly chooses file-reading,
   information-reading, and connected-source scopes.
2. **Register in place** — Matters inventories source objects without moving,
   rewriting, or copying every original into the application.
3. **Qualify** — deterministic rules exclude program files, caches, system
   material, and other content that should not enter semantic analysis.
4. **Model** — related clues become human-scale Matters, child Matters,
   events, people, timelines, relationships, plans, results, and unresolved
   questions.
5. **Present** — the same model is projected into a bilingual object browser
   and a bounded AI interface.
6. **Maintain** — changes invalidate stale understanding, refresh summaries,
   compare predictions with outcomes, and preserve corrections instead of
   silently replacing history.

    explicit authorization
            ↓
    source-in-place registry and qualification
            ↓
    evidence, identity, time, hierarchy, state, and outcome modeling
            ↓
    auditable Matter graph
            ↓
    desktop object browser + AI gateway

“Discovered” therefore does not mean “understood,” and “scanned” does not mean
“visible in the UI.” Matters keeps those stages separate so coverage can show
where an object is and what remains to be done.

### One model, two entrypoints

| Reader | Entrypoint | What it provides |
| --- | --- | --- |
| **People** | Bilingual Windows desktop object browser | Matter cards, hierarchy, timeline, people, relations, files and information, images, and supplemental context |
| **AI and Codex** | [Matters plugin](./plugins/matters) through <code>matters-mcp</code> | Model-map discovery, bounded situation context, history, observations, corrections, prediction feedback, and Model Miss reporting |

Both entrypoints delegate to the same <code>MatterService</code> and canonical
model. The AI gateway does not create a second hidden database. AI observations
and corrections enter the same traceable maintenance path with their
provenance and status intact.

AI inference is deliberately revisable. A supported historical gap may be
filled as an explicit inference; a future obligation remains planned rather
than being presented as already completed. Forecasts may be retained for later
comparison with reality, but they are not silently promoted to facts.

### What you can explore

- A root-level catalog of meaningful Matters, ordered by the newest material
  clue rather than by file name.
- Standard and Compact cards with bilingual titles, status, start date, and a
  representative generated image.
- A bounded hierarchy graph for Matter stages and child Matters, with a quick
  view instead of recursively nesting full detail pages.
- Deduplicated timelines, people, related Matters, files and information,
  real-image galleries, and clearly labeled AI supplemental information.
- Coverage and freshness states that show whether registered information is
  excluded, blocked, waiting, stale, modeled, localized, illustrated, and
  reachable in the UI.

### Get started

#### Windows desktop

Download the Windows archive from the
[latest GitHub Release](https://github.com/liuyingxuvka/Matters/releases/latest),
extract it, and run <code>Matters/Matters.exe</code>. The executable starts a
loopback-only local service and opens the packaged Web UI inside a desktop
window.

The release page also provides the Python wheel, source archive, and
<code>SHA256SUMS.txt</code>. Current Windows packages are unsigned, so Windows
may show its normal warning for a downloaded application.

#### Install from source

Requirements: Python 3.11 or later. The packaged desktop executable targets
Windows.

    git clone https://github.com/liuyingxuvka/Matters.git
    cd Matters
    python -m pip install .
    matters version
    matters capabilities
    matters-desktop

For private operation, keep the runtime root outside the checkout:

    $env:MATTERS_HOME = "D:\MattersData"
    matters-desktop

Without <code>MATTERS_HOME</code>, package inspection and synthetic
verification remain available in a non-writing capability mode. Matters does
not silently create a private runtime inside the public repository.

#### Connect Codex or another MCP client

The public plugin is in [<code>plugins/matters</code>](./plugins/matters). Its
<code>.mcp.json</code> launches the installed <code>matters-mcp</code> command.
The MCP gateway uses the same service as the desktop app, HTTP UI, and CLI.

### Skills and Guard ecosystem

Matters uses a small number of clearly separated skill and Guard boundaries.
These roles are intentionally different:

| Project or skill set | Role in Matters | Installation boundary |
| --- | --- | --- |
| [Bundled Matters skills](./src/matters/bundled_skills) | Eleven app-owned workflows for source governance, inventory, freshness, semantic depth, correction, model misses, skill runtime, research orchestration, autonomous maintenance, and visual generation | Shipped inside Matters; not installed globally by default |
| [ResearchGuard](https://github.com/liuyingxuvka/ResearchGuard) | Sole external advisory research provider for source discovery, evidence tracing, and logical analysis | Needed only for research-dependent enrichment; basic inventory and browsing remain available without it |
| [FlowGuard](https://github.com/liuyingxuvka/FlowGuard) | Executable behavior, UI-flow, TestMesh, and release-process modeling used to develop and verify Matters | Development and release dependency; not required merely to open the desktop app |
| [SkillGuard](https://github.com/liuyingxuvka/SkillGuard) | Author-side maintenance and validation of independently released skill sources | Maintainer tool; not a Matters runtime controller |
| [WorldGuard](https://github.com/liuyingxuvka/worldguard) | Optional world-claim and what-if modeling in the wider Guard ecosystem | Independent project, not embedded in Matters |
| [PhysicsGuard](https://github.com/liuyingxuvka/PhysicsGuard) | Optional evidence-oriented audit of physical simulation results | Independent project, not embedded in Matters |

The former separate SourceGuard, TraceGuard, and LogicGuard research routes are
not parallel Matters fallbacks. Their source-discovery, temporal-trace, and
argument-analysis capabilities are unified behind ResearchGuard’s public
interface. Each Guard keeps its own repository, release, validation, and
maintenance authority.

### Privacy and trust

Original source material stays where its provider or operating system already
stores it. Matters keeps stable locators, fingerprints, indexes, derived
understanding, and UI projections in a separate private runtime:

    repository/          public source and synthetic evidence
    MATTERS_HOME/        private registry, indexes, and derived models
    MATTERS_EVAL_VAULT/  explicitly selected private evaluation material

Permission to read a source never implies permission to modify it, delete it,
execute it, send messages, disclose it to a remote model, or publish it. Those
are separate authorities. Real records, local inventories, private model
output, personal paths, and real-data screenshots are excluded from this public
repository and its release packages.

See [Security](./SECURITY.md),
[public-boundary rules](./docs/security/public-boundary.md), and
[data classification](./docs/security/data-classification.md).

### For developers

| Path | Responsibility |
| --- | --- |
| <code>src/matters/</code> | Domain, application, persistence, source boundaries, CLI, MCP, HTTP, and desktop runtime |
| <code>ui/</code> | Packaged bilingual object browser |
| <code>plugins/matters/</code> | Public Codex skill and MCP configuration |
| <code>flowguard_models/</code> | Executable product, AI-operation, skill-runtime, and delivery models |
| <code>openspec/</code> | Requirements, design decisions, and implementation tasks |
| <code>synthetic_fixtures/</code> | Public-safe known-good and known-bad cases |
| <code>tests/</code> | Unit, integration, TestMesh, privacy, install, and release checks |

    python -m pytest -q
    openspec validate build-matters-model-driven-core --strict
    python scripts/check_public_boundary.py --root .

Validation evidence describes the exact candidate that was checked. It does
not prove that every future AI interpretation will be correct. Matters is
local-first, provides no hosted synchronization service, and does not enable
daily maintenance unless the user explicitly opts in.

### License

Matters is open source under the [MIT License](./LICENSE). The license governs
the software; it does not authorize publishing another person’s private data.
Please read [SECURITY.md](./SECURITY.md) before reporting a vulnerability, and
never include private information in a public issue.

---

## 简体中文

### Matters 是什么

Matters 是一款本地优先的软件。它把用户明确授权的信息来源中的零散线索，整理成
清楚的**事项模型与事件模型**。它不会让相关记录继续散落在文件、消息、项目和已连接
服务里，而是重建背后的完整情况：相关人物、时间、阶段、子事项、关系、待解决问题、
结果以及支持这些判断的来源。

它的结果不是一个看不见过程的黑盒摘要。重要结论仍然连接着原始位置、时间依据、
不确定性、推断状态、纠正历史和当前新鲜度，因此可以审计、追踪、检查，并在新线索
出现后重新判断。

### 信息怎样变成一个事项

1. **明确授权**——用户选择允许读取的文件范围、信息范围和已连接来源。
2. **原位登记**——Matters 登记来源对象，但不会移动、改写或把全部原件复制进软件。
3. **先做资格判断**——确定性规则会先挡住程序文件、缓存、系统材料以及不应该进入
   语义分析的内容。
4. **建立模型**——相关线索会形成大事项、子事项、事件、人物、时间线、关系、计划、
   结果和待解决问题。
5. **统一呈现**——同一个模型同时提供给双语对象浏览器和受限的 AI 接口。
6. **持续维护**——来源变化会让旧理解失效，触发摘要更新、预测与结果比较，并保留
   纠正历史，而不是静默覆盖过去。

    用户明确授权
          ↓
    原位登记、硬排除与来源资格判断
          ↓
    证据、身份、时间、层级、状态和结果建模
          ↓
    可审计的事项关系图
          ↓
    桌面对象浏览器 + AI 入口

所以，“已经发现”不等于“已经理解”，“已经扫描”也不等于“已经显示在 UI”。Matters
会把这些阶段分开记录，让覆盖状态明确说明每个对象走到了哪里、还缺什么。

### 一个模型，两个入口

| 使用者 | 入口 | 能看到或完成什么 |
| --- | --- | --- |
| **人类** | 中英双语 Windows 桌面对象浏览器 | 事项卡片、层级、时间线、人物、关系、文件与信息、图片和补充背景 |
| **AI 与 Codex** | [Matters 插件](./plugins/matters)与 <code>matters-mcp</code> | 读取模型地图和受限上下文，查看历史，提交观察与纠正，反馈预测结果和 Model Miss |

两个入口都使用同一个 <code>MatterService</code> 和同一套规范模型。AI 入口不会建立
第二个隐藏数据库；AI 的观察与纠正会带着来源和状态进入同一条可追踪维护路径。

AI 推断始终可以被修改。有证据支持时，它可以明确标记并补齐过去缺失的环节；未来
尚未发生的义务仍然保持“计划中”，不会被写成已经完成。系统可以保留预测，等待以后
与现实比较，但不会把预测偷偷变成事实。

### 可以浏览什么

- 只显示有意义根事项的卡片目录，并按最近一条重要线索排序，而不是按文件名排序。
- 带有双语标题、状态、开始时间和代表图片的标准与紧凑卡片。
- 表达事项阶段与子事项的有界关系图；点击后使用快速预览，不再递归套入完整详情页。
- 去重后的时间线、人物、关联事项、文件与信息、真实图片库，以及明确标注的 AI
  补充信息。
- 覆盖与新鲜度状态，说明登记对象是否被排除、阻塞、等待处理、已经过期、完成建模、
  完成双语、拥有图片并已经到达 UI。

### 开始使用

#### Windows 桌面版

从 [GitHub 最新 Release](https://github.com/liuyingxuvka/Matters/releases/latest)
下载 Windows 压缩包，解压后运行 <code>Matters/Matters.exe</code>。程序会启动一个
只监听本机回环地址的服务，并在桌面窗口里打开已经打包的 Web UI。

Release 页面同时提供 Python wheel、源码包和 <code>SHA256SUMS.txt</code>。当前
Windows 安装包没有代码签名，因此 Windows 可能对下载的应用显示正常安全提示。

#### 从源码安装

需要 Python 3.11 或更高版本；打包桌面可执行文件面向 Windows。

    git clone https://github.com/liuyingxuvka/Matters.git
    cd Matters
    python -m pip install .
    matters version
    matters capabilities
    matters-desktop

正式使用时，请把私有运行目录放在仓库之外：

    $env:MATTERS_HOME = "D:\MattersData"
    matters-desktop

没有 <code>MATTERS_HOME</code> 时，软件仍可检查安装包和运行合成测试，但会保持
不写入状态；它不会偷偷在公开仓库里建立私有运行目录。

#### 连接 Codex 或其他 MCP 客户端

公开插件位于 [<code>plugins/matters</code>](./plugins/matters)，其中的
<code>.mcp.json</code> 会启动已经安装的 <code>matters-mcp</code>。MCP 入口与桌面
程序、HTTP UI 和 CLI 使用同一个服务。

### 技能与 Guard 生态

Matters 使用了若干职责明确、彼此分开的技能和 Guard。它们不是同一种依赖：

| 项目或技能组 | 在 Matters 中的职责 | 安装边界 |
| --- | --- | --- |
| [Matters 内置技能](./src/matters/bundled_skills) | 11 项软件自有流程，负责来源治理、清单、新鲜度、语义深度、纠正、Model Miss、技能运行、研究编排、自动维护和视觉生成 | 随 Matters 打包；默认不全局安装 |
| [ResearchGuard](https://github.com/liuyingxuvka/ResearchGuard) | 唯一外部研究能力入口，负责来源发现、证据追踪与逻辑分析 | 只有依赖研究的补充理解需要它；基础登记和浏览不依赖它 |
| [FlowGuard](https://github.com/liuyingxuvka/FlowGuard) | 在开发和发布中对行为、UI 流程、TestMesh 与交付流程进行可执行建模和验证 | 开发与发布依赖；仅打开桌面软件并不需要安装它 |
| [SkillGuard](https://github.com/liuyingxuvka/SkillGuard) | 在作者侧维护和验证独立发布的技能源码 | 维护工具，不是 Matters 的运行时控制器 |
| [WorldGuard](https://github.com/liuyingxuvka/worldguard) | Guard 生态中可选的世界主张与假设分析能力 | 独立项目，不内嵌到 Matters |
| [PhysicsGuard](https://github.com/liuyingxuvka/PhysicsGuard) | 可选的物理仿真结果证据审计能力 | 独立项目，不内嵌到 Matters |

以前分开的 SourceGuard、TraceGuard 和 LogicGuard 研究入口不会在 Matters 中成为
三条并行备用路线。它们的来源发现、时间证据追踪和论证分析能力，统一通过
ResearchGuard 的公开接口提供。每一个 Guard 仍然保留自己的仓库、发布、验证和
维护权限。

### 隐私与可信边界

原始来源材料仍然留在原服务或操作系统原位置。Matters 只把稳定定位信息、指纹、
索引、派生理解和 UI 投影保存在独立的私有运行目录：

    repository/          公开源码与合成证据
    MATTERS_HOME/        私有登记、索引与派生模型
    MATTERS_EVAL_VAULT/  用户明确选择的私有评估材料

允许读取不代表允许修改、删除、执行、发送消息、向远程模型披露或公开发布；这些是
彼此独立的权限。真实记录、本机文件清单、私人模型输出、个人路径和真实数据截图都
不能进入这个公开仓库和发布安装包。

详细规则见 [安全说明](./SECURITY.md)、
[公开边界](./docs/security/public-boundary.md)和
[数据分类](./docs/security/data-classification.md)。

### 面向开发者

| 路径 | 职责 |
| --- | --- |
| <code>src/matters/</code> | 领域、应用、持久化、来源边界、CLI、MCP、HTTP 与桌面运行时 |
| <code>ui/</code> | 打包后的双语对象浏览器 |
| <code>plugins/matters/</code> | 公开 Codex 技能与 MCP 配置 |
| <code>flowguard_models/</code> | 产品、AI 操作、技能运行与交付流程的可执行模型 |
| <code>openspec/</code> | 需求、设计决定和实现任务 |
| <code>synthetic_fixtures/</code> | 可公开的已知正确与已知错误测试材料 |
| <code>tests/</code> | 单元、集成、TestMesh、隐私、安装与发布检查 |

    python -m pytest -q
    openspec validate build-matters-model-driven-core --strict
    python scripts/check_public_boundary.py --root .

验证证据只能说明被检查的那个确定版本，不能保证未来每一次 AI 理解都永远正确。
Matters 是本地优先软件，不提供托管式云同步；每日维护也不会默认开启，必须由用户
明确选择。

### 许可证

Matters 采用 [MIT License](./LICENSE) 开源。许可证约束软件本身，但不授权公开
他人的私人数据。报告漏洞前请阅读 [SECURITY.md](./SECURITY.md)，不要在公开 Issue
中放入任何私人信息。
