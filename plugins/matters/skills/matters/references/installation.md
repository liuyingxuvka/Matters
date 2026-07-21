# Matters AI installation contract

This guide is for the AI agent that receives a request such as “install and
use Matters.” The AI owns the complete setup. The user should not have to wire
the MCP gateway, copy skills, create a scheduled task, or run the first
maintenance cycle manually.

## Truth and authority boundaries

- Installing the software authorizes software setup; it does not authorize
  reading any file, mailbox, service, or project that the user has not placed
  in scope.
- The source scope is supplied by the user to the installing AI during setup.
  It is not hard-coded into Matters, inferred from the computer, or bundled in
  a release artifact.
- Original sources stay in their existing locations. Matters stores locators,
  fingerprints, indexes, derived models, and projections under an external
  private `MATTERS_HOME`; it does not copy the whole source collection.
- Matters uses the host AI and its background agents. It does not require or
  request an application-owned OpenAI API key and it must not add a direct API
  fallback.
- `Matters.exe` is a desktop view over the selected private model store. A
  healthy but empty view before the first AI run is honest, not evidence that
  the user's information was already modeled.

## Required installation flow

The installing AI must complete these steps in order:

1. Select one current Matters release and verify that the package, plugin, and
   reported version agree.
2. Install the Python package and/or Windows desktop archive. Keep
   `MATTERS_HOME` outside the source checkout and public build directories.
3. Verify `matters version`, `matters capabilities`, the `matters-mcp` launcher,
   MCP initialization, and the public `matters` plugin/skill contract.
4. Verify that the release contains exactly eleven immutable app-local Matters
   maintenance skills. Do not globally install or overlay those internal
   skills.
5. Treat ResearchGuard as the only external real-research provider. FlowGuard,
   SkillGuard, WorldGuard, PhysicsGuard, and all other Guard-family projects
   remain independently installed and maintained; do not vendor or silently
   replace them during Matters setup.
6. Ask the user which folders, mailboxes, and other information sources are in
   scope, or reuse an existing explicit grant. Record the grant only in the
   private runtime. Never widen it as a consequence of installation or
   scheduling.
7. Create or repair exactly one host-owned daily Matters maintenance schedule.
   Use a low-activity local time supported by available user context; if no
   better signal exists, use 21:00 local. The schedule must call the public
   Matters skill and the shared A2 `run_planned_maintenance` path, resume
   durable checkpoints, and remain model-agnostic.
8. Run one initial bounded maintenance cycle immediately so authorized sources
   can be registered, triaged, modeled, localized, illustrated, and projected.
9. Open the installed desktop UI and report the real coverage state, including
   pending, stale, excluded, or blocked stages.

## Schedule contract

The installing AI—not the human user—creates and maintains the schedule. It
may use the strongest compatible reasoning profile as orchestrator and may
delegate bounded low-cost annotation work to replaceable cheaper background
profiles. Product behavior must never bind to a named model.

The schedule:

- reads only currently authorized scopes and performs no mailbox/source
  mutation;
- uses the same MatterService/MCP maintenance path as interactive work;
- records no-delta, pending, blocked, interrupted, and resumed outcomes
  honestly;
- never owns final FlowGuard/model verification, full regression, package or
  install currentness, Git commit, tag, or GitHub Release publication.

If the AI host cannot create or inspect scheduled automations, setup is
`blocked: automation_capability_unavailable`. The AI must report that exact
gap and must not claim successful setup, silently omit recurrence, or ask the
user to build the task by hand.

## Completion report

Setup is complete only when the AI can report the installed version, MCP
status, private-root status, plugin/skill status, exactly one daily schedule,
initial-maintenance result, and desktop launch result. Every partial or blocked
stage remains visible.

## 中文简要说明

安装过程中，用户需要把允许读取的文件夹、邮箱或其他信息来源范围告诉安装 AI；这个
范围不会预先写在软件或发布包里。安装许可不等于来源读取许可，AI 也不能自行扩大范围。

用户只需要告诉 AI“安装并使用 Matters”。安装 AI 负责安装软件、连接 MCP 和公开
技能、检查 11 项内置技能、建立唯一一条每日维护计划、立即执行第一次有边界维护，
然后打开桌面界面。用户不用手工创建计划任务。安装许可不等于来源读取许可；AI 只能
读取用户明确授权的范围。没有计划任务能力时，AI 必须明确报告安装被阻塞，不能假装
已经完成。
