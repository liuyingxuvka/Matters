# Matters

[![Release](https://img.shields.io/github/v/release/liuyingxuvka/Matters?display_name=tag)](https://github.com/liuyingxuvka/Matters/releases/latest)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB)](https://www.python.org/)
[![Windows desktop](https://img.shields.io/badge/Windows-desktop-0078D4)](https://github.com/liuyingxuvka/Matters/releases/latest)
[![License](https://img.shields.io/badge/license-source--available-8A2BE2)](./LICENSE)

[English](#english) · [简体中文](#简体中文)

<!-- README HERO START -->
<p align="center">
  <img src="./docs/assets/readme-hero/hero.png" alt="Matters turns authorized local sources into traceable matters while keeping private data on the user's computer" width="100%" />
</p>

<p align="center">
  <strong>Turn scattered personal information into traceable, living matters—locally, bilingually, and with explicit evidence.</strong>
</p>
<!-- README HERO END -->

## English

Matters is a local-first personal intelligence application. It registers
explicitly authorized files and read-only Gmail information in place, builds a
traceable model of people, events, timelines, sub-matters, relationships, open
loops, and outcomes, and presents the result in a desktop object browser.

The original files and messages stay where they already live. Matters stores
only its registry, derived understanding, indexes, and UI projections under a
separate private `MATTERS_HOME`. The public repository and release artifacts
contain no user mailbox, local-file inventory, private model, or real-data
screenshot.

### Why Matters

Ordinary search finds documents. Task managers wait for manual entry. Matters
is designed to reconstruct the larger situation around both:

- group related evidence into human-scale Matters rather than one card per file;
- keep large Matters, material stages, events, and source records distinct;
- infer missing historical steps conservatively and label them as revisable AI inference;
- keep future obligations planned instead of predicting that they already happened;
- update summaries and ordering when newer evidence arrives;
- preserve every source pointer, correction, prediction comparison, and model miss.

### From sources to the object browser

```text
Explicit authorization
        ↓
Metadata-first inventory and hard exclusions
        ↓
Read-only source registry and freshness tracking
        ↓
Evidence, people, time, hierarchy, state, and outcome owners
        ↓
Matter graph, timeline, files, images, and AI supplemental context
        ↓
English / 简体中文 desktop object browser
```

Every discovered object receives a durable disposition. A coverage ledger can
show whether it is registered, excluded, blocked, stale, waiting for analysis,
modeled, localized, illustrated, and reachable in the UI. “Scanned” is never
used as a substitute for “understood and visible.”

### What v0.3.0 ships

- A Windows desktop application that wraps the packaged local Web UI in a real
  desktop window; the browser development surface is not the product shell.
- Standard and Compact Matter cards, automatic root-level hero images,
  start-date and status filters, newest-evidence-first ordering, and bilingual
  projection.
- Matter detail pages for overview, sub-matter/stage graph, timeline, people,
  related Matters, files and information, images, and AI supplemental context.
- Read-only local-file and Gmail source contracts, source-in-place registration,
  change detection, freshness invalidation, and append-only corrections.
- A model-agnostic AI operation boundary: inexpensive workers may perform
  bounded annotation while stronger reasoning handles hierarchy and modeling.
- Exactly eleven immutable app-local Matters maintenance skills.
- One public Codex plugin and `matters-mcp` AI gateway for model-map discovery,
  bounded situation context, history, observations, corrections, prediction
  feedback, model-miss reporting, and the shared maintenance path.
- Executable FlowGuard models, ModelMesh/TestMesh evidence, synthetic fixtures,
  privacy checks, clean-install checks, and reproducible Windows packaging.

### Desktop download

Download `Matters-0.3.0-windows-x64.zip` from the
[v0.3.0 release](https://github.com/liuyingxuvka/Matters/releases/tag/v0.3.0),
extract the archive, and run `Matters/Matters.exe`.

The application starts a loopback-only local service and opens the packaged UI
inside the desktop shell. It does not require a Jira or Atlassian account. A
Windows code-signing certificate is not included in v0.3.0, so Windows may show
its normal warning for an unsigned downloaded application.

Release assets also include:

- `matters-0.3.0-py3-none-any.whl`
- `matters-0.3.0.tar.gz`
- `SHA256SUMS.txt`

### Install from source

Requirements: Python 3.11 or later; Windows is required for the packaged
desktop executable.

```powershell
git clone https://github.com/liuyingxuvka/Matters.git
cd Matters
python -m pip install .
matters version
matters capabilities
matters locales
matters-desktop
```

For private operation, set a runtime root outside the checkout:

```powershell
$env:MATTERS_HOME = "D:\Private\MattersData"
matters-desktop
```

Without `MATTERS_HOME`, package inspection and synthetic verification remain
available in a non-writing capability mode. Matters never silently creates a
private data root inside the repository.

### AI and Codex entrypoint

The standard plugin lives at [`plugins/matters`](./plugins/matters). Its
`.mcp.json` starts the installed `matters-mcp` process. The gateway delegates to
the same `MatterService` used by the CLI, HTTP UI, and desktop application; it
is not a second database or an alternate truth owner.

The eleven internal `matters-*` skills remain bundled with the application and
are not installed globally. ResearchGuard and every Guard-family project remain
independent external dependencies. Research-dependent output is visibly
blocked when a current ResearchGuard receipt is unavailable; Matters does not
fall back to separate SourceGuard, TraceGuard, or LogicGuard runtime routes.

### Privacy and public-repository boundary

```text
repository/          generic source and synthetic evidence only
MATTERS_HOME/        private live user data and derived models
MATTERS_EVAL_VAULT/  explicitly selected private evaluation material
```

Never commit real messages, subjects, addresses, paths, excerpts, content
hashes, screenshots, receipts, embeddings, or private model output. Gmail
access is read-only. Mailbox mutation, file deletion or execution, outbound
messaging, remote-model disclosure, and public publication are separate
permissions.

The release gate scans the workspace, Git views, a clean clone, the wheel,
source distribution, and Windows archive independently. See
[`docs/security/public-boundary.md`](./docs/security/public-boundary.md) and
[`docs/security/data-classification.md`](./docs/security/data-classification.md).

### Development and verification

```powershell
python -m pytest -q
openspec validate build-matters-model-driven-core --strict
python scripts/check_public_boundary.py --root .
```

Release-only checks are deliberately separated from ordinary development and
run against one frozen source identity. The models and receipts document the
checked candidate; they do not guarantee arbitrary future AI output.

### Repository map

| Path | Purpose |
| --- | --- |
| `src/matters/` | Domain, application, providers, persistence, CLI, MCP, HTTP, and desktop runtime |
| `ui/` | Packaged bilingual object browser |
| `plugins/matters/` | Public Codex plugin and AI gateway contract |
| `flowguard_models/` | Executable product, skill-runtime, and delivery models |
| `openspec/` | Product requirements, design, and implementation tasks |
| `synthetic_fixtures/` | Public-safe known-good and known-bad cases |
| `scripts/` | Installation, packaging, privacy, and release tooling |
| `tests/` | Unit, integration, TestMesh, privacy, install, and release checks |

### Current boundaries

- Matters is local-first and does not provide a hosted synchronization service.
- Jira/Rovo are not required and the generic Jira adapter remains disabled.
- Daily maintenance is not enabled by default; scheduling is an explicit user
  opt-in over the same bounded maintenance path.
- A generic release does not claim that any particular user's private first run
  or semantic coverage is complete.

### License and security

The repository is public and source-available, but it is not an OSI-approved
open-source release. Personal, non-commercial use is permitted under the
[`Matters Public Source License`](./LICENSE). See [`SECURITY.md`](./SECURITY.md)
before reporting a vulnerability, and never include private data in an issue.

---

## 简体中文

Matters 是一个本地优先的个人信息理解软件。它会登记用户明确授权的本机文件和
只读 Gmail 信息，在不移动原文件的情况下，建立可追溯的人物、事件、时间线、
子事项、关系、待处理问题和结果模型，并通过桌面“事项对象浏览器”呈现出来。

原始文件与邮件仍然保留在原来的位置。Matters 只把登记信息、派生理解、索引和
UI 投影保存在独立的私有 `MATTERS_HOME` 中。公开仓库与发布安装包不会包含用户
邮箱、本机文件清单、私人模型或真实数据截图。

### 为什么需要 Matters

普通搜索只能找到文件，任务管理软件通常需要人手动录入。Matters 希望理解文件
背后的完整事情：

- 把相关证据合并成人类能理解的大事项，而不是每个文件生成一张卡片；
- 明确区分大事项、关键阶段、具体事件和来源记录；
- 谨慎补齐过去缺失的环节，并明确标记为可修正的 AI 推断；
- 未来尚未发生的义务保持“计划中”，不会推断为已经完成；
- 新线索出现后自动更新摘要，并把最近有进展的事项排到前面；
- 保留来源位置、纠正记录、预测与现实比较以及 Model Miss。

### 从来源到对象浏览器

```text
用户明确授权
      ↓
元数据优先登记与硬排除
      ↓
只读来源目录和新鲜度跟踪
      ↓
证据、人物、时间、层级、状态和结果建模
      ↓
事项关系图、时间线、文件、图片与 AI 补充信息
      ↓
English / 简体中文桌面对象浏览器
```

每个发现的对象都会留下明确状态。覆盖账本能够说明它是否已经登记、排除、阻塞、
过期、等待分析、完成建模、完成双语、拥有图片以及到达 UI。“扫描过”不等于
“已经理解并在 UI 中显示”。

### v0.3.0 包含什么

- 真正的 Windows 桌面应用外壳：把打包后的本地 Web UI 放进桌面窗口，而不是
  仅提供一个浏览器快捷方式。
- 标准与紧凑卡片、根事项自动首页图片、开始时间与状态筛选、按最新线索排序和
  双语显示。
- 事项详情的八个顶层区域：概览、子事项/阶段图、时间线、人物、关联事项、
  文件与信息、图片以及 AI 补充信息。
- 本机文件与 Gmail 的只读来源合同、原位登记、变化检测、新鲜度失效和追加式纠正。
- 不绑定具体模型的 AI 任务边界：低成本模型可做受限标注，更强模型负责层级与建模。
- 恰好十一项不可变的应用内 Matters 维护技能。
- 一个公开 Codex 插件与 `matters-mcp` AI 入口，可读取模型地图、受限当前情况、
  历史，追加用户观察与纠正，比较预测和现实，报告 Model Miss，并调用同一维护路径。
- 可执行 FlowGuard 模型、ModelMesh/TestMesh 证据、合成测试、隐私检查、干净安装
  检查和可复现的 Windows 打包流程。

### 下载桌面版

从 [v0.3.0 Release](https://github.com/liuyingxuvka/Matters/releases/tag/v0.3.0)
下载 `Matters-0.3.0-windows-x64.zip`，解压后运行 `Matters/Matters.exe`。

桌面程序会启动一个只监听本机回环地址的服务，并在 APP 外壳中打开打包 UI。
它不需要 Jira 或 Atlassian 账户。v0.3.0 暂未包含 Windows 代码签名证书，因此
Windows 可能会对下载的未签名应用显示正常的安全提示。

Release 还包含 Python wheel、源码包和 `SHA256SUMS.txt` 校验值。

### 从源码安装

需要 Python 3.11 或更高版本；打包后的桌面可执行文件仅面向 Windows。

```powershell
git clone https://github.com/liuyingxuvka/Matters.git
cd Matters
python -m pip install .
matters version
matters capabilities
matters locales
matters-desktop
```

正式使用时，请把私有数据目录设在仓库外：

```powershell
$env:MATTERS_HOME = "D:\Private\MattersData"
matters-desktop
```

没有 `MATTERS_HOME` 时，软件仍可执行包健康检查与合成验证，但保持不写入状态；
它不会偷偷在 Git 仓库里创建私人数据目录。

### AI 与 Codex 入口

标准插件位于 [`plugins/matters`](./plugins/matters)，其中 `.mcp.json` 会启动已安装的
`matters-mcp`。这个入口与 CLI、HTTP UI 和桌面应用共同使用同一个
`MatterService`，不会建立第二套数据库或第二个事实来源。

十一项内部 `matters-*` 技能随 APP 打包，不会默认安装为全局技能。ResearchGuard
以及其他 Guard 项目保持外部独立。当 ResearchGuard 当前回执不可用时，只阻塞
依赖研究的结果；Matters 不会退回到 SourceGuard、TraceGuard 或 LogicGuard 的
并行运行入口。

### 隐私与公开仓库边界

```text
repository/          只放通用源码和合成证据
MATTERS_HOME/        私有真实数据和派生模型
MATTERS_EVAL_VAULT/  用户明确选择的私有评估材料
```

真实邮件、主题、地址、路径、摘录、内容哈希、截图、回执、嵌入和私人模型输出都
不能进入 Git。Gmail 访问是只读的。修改邮箱、删除或执行文件、向外发送消息、
向远程模型披露数据以及公开发布，始终是互相独立的权限。

发布检查会分别扫描工作目录、Git 视图、干净克隆、wheel、源码包和 Windows ZIP。
详细规则见 [`docs/security/public-boundary.md`](./docs/security/public-boundary.md)
和 [`docs/security/data-classification.md`](./docs/security/data-classification.md)。

### 开发与验证

```powershell
python -m pytest -q
openspec validate build-matters-model-driven-core --strict
python scripts/check_public_boundary.py --root .
```

Release 专用检查会在同一个冻结源码身份上单独运行。模型与回执只能证明被检查的
候选版本，不能保证未来任意 AI 输出永远正确。

### 当前边界

- Matters 是本地优先软件，不提供托管式云同步服务。
- 不需要 Jira/Rovo；通用 Jira 适配器仍处于禁用状态。
- 默认不启用每日定时维护；定时任务是用户明确选择后，对同一维护路径的调用。
- 通用软件发布不代表任何特定用户的首次私人运行或全部语义覆盖已经完成。

### 许可证与安全

本仓库公开且源码可见，但并非 OSI 认可的开源项目。个人、非商业使用受
[`Matters Public Source License`](./LICENSE) 许可。报告漏洞前请阅读
[`SECURITY.md`](./SECURITY.md)，不要在公开 Issue 中放入任何私人数据。
