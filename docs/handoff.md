# handoff —— 现在在哪 + 上一段为什么这么改

> 给下一个会话(或新人)的交接:**读完就知道"现在在哪、接着干啥"**,刻意短。
> 它不是日记,**更不是待办清单**——"还剩几件"住 debts.md(没有债务表的小项目,
> 待办住台账的"去处"列),这一页只装"发生了什么、为什么"。
>
> **怎么防胖 —— 整批回收,不是逐行削**:① 平时该加就加,别管行数;
> ② 发一版(或页面翻不动了,目测 300 行往上)把这批已完结的**整批蒸馏**进 history/progress/;
> **🚫 绝不"为了加一条删一条"——那样删掉的永远是最好删的那条。行数不设硬顶。**
> **写法**:每条只留"结论 + 下一步 + 去哪看全文";推导、实测原文留在它自己的 SPEC/报告里。

## 〇、现在主线是什么(最先读)

主线 = **spec-011 Phase 10 上线前体检(§184,禁新增产品功能):性能九类泄漏+安全十一类风险
逐项审计(证据表住 SPEC §四)+发版三决定落地(NSIS/不签名/不自动更新,owner 2026-10-11 "开工"拍板)**。
2026-10-11 本会话完成 A2 对齐(说人话范围表→owner 原话"开工")并立项 InDev。
红线闸不代跑:T3 全量 Benchmark、NSIS 实际打包——发版前请示 owner。版本 0.7.6 起。
上段(spec-009 Watcher + spec-010 Open Recent + 0.7.4/0.7.5 两轮返修)已全部 Done——2026-10-11
owner 收口原话"我换新对话做下一个需求",全程蒸馏在 history/progress/progress-2026-10.md。
**未结大案:内容区冻结 bug**(owner 报"切换任何页签内容都不变",本机三路复刻未现;0.6.12 起诊断已装)——
复现时 Settings → Export Diagnostics,文件在 %APPDATA%\com.aiprojectviewer.app.exp\diagnostics\
aiv-diagnostics-<ts>.txt,同机直读定位;修复随 0.7.x 发。
协作习惯:高频验收、编号反馈、返工轮是常态;测试零打扰红线(testing.md §1.2);e2e 一律 aivlaunch(PID 限定)+
**park_offscreen(L34)**。

## 一、现在在哪(最新在上)

### 2026-10-11 · spec-011 Phase 10 立项开工(本会话)

> **新会话从这接** —— 读 AGENTS.md 开机三步 → 本页 → 续 spec-011 审计(性能九+安全十一,证据表
> 住 specs/spec-011-performance-security-release.md §四)。

- A2 对齐:说人话范围(体检三件事+三决定建议表)→ owner 原话**"开工"**;三决定=NSIS/不签名/不自动更新。
- 审法:每类列产生点/入口全清单→逐点判→file:line 证据进 SPEC §四审计表;漏即修+回归;零新功能零 UI。
- 闸:T3 全量 Benchmark+NSIS 打包必须 owner 点头(AGENTS.md 红线),交付汇报时一并请示。

### 2026-10-11 · 本段收口:Watcher+Open Recent 全 Done(0.7.0–0.7.5 五版),主线交棒新对话

> **新会话从这接** —— 读 AGENTS.md 开机三步 → 本页 → 听 owner 下一个需求;若 owner 指规划内 →
> Phase 10(spec-011,§184,禁新增产品功能),开工前 A2 对齐;立 SPEC 按 docs/workflow.md 状态机。

- 收口凭据:owner"我换新对话做下一个需求";两笔 Done 台账见 specs/INDEX;全程蒸馏 history/progress/
  progress-2026-10.md(Grep spec-009/spec-010/0.7.x/L33–L38)。发版链 0.7.5 为体验渠道当前版。
- 交接要点:①体验渠道发版 = scripts/publish-experience.ps1 -Note(独立 target-exp,发版后全文件扫三二进制
  标识——L37);②e2e 新增检查先进 phase3/recent-suite 别另起炉灶;③凡动 watcher 链发版前必跑
  watcher-freeze-guard;④冻结 bug 取证路径见 〇;⑤客户端冻到点不了更新时用 scripts/swap-experience-client.py
  (默认预览,--yes 执行)。
- ⚠️ docs/AI-Project-Guide/ 的未提交改动归另一会话,勿动勿提交勿还原。

## 二、为什么这么改(当批关键取舍;只在"后人容易被顺手的改法改回去"处留一句)

- **~~不另建 spec.md / roadmap.md / specs/~~**(2026-10-01 改口,出处:owner"每一段开发都要专门写一个 Spec 文档再开发";
  同日二次收紧:specs 按指南落仓库根目录、spec-NNN 编号、INDEX 台账、workflow 状态机):
  现规矩 = **每个 Phase 开工前按 docs/workflow.md 状态机立 SPEC(根目录 `specs/spec-NNN`,编号与 Phase 对齐)**。
  spec-002 起执行,spec-001 追溯建档。原取舍(V1.5 兼任 spec/roadmap、待痛点出现再建)低估了"动代码前要有可审的实现方案与状态台账"这一痛点;
  V1.5 仍兼任产品规格与 roadmap(需求真值),specs/ 装实现方案与状态,两层用指针互指不抄正文。
- **需求变更走增量修订 + 变更审计(V1.5 §193),禁止整篇重写**:V1.2→V1.3→V1.4 三次整篇重写
  每次都丢过已确认规格,V1.5 起改为"只改明确条目+审计清单"后未再发生回归。
- **版本段 0.7.x(2026-10-11 起)**:owner 明令"版本升到0.7"——D7 规则(0.6.x 固定递增不跳段)的逃逸条款
  "直到 owner 另有指令"首次使用;递增纪律不变,只是换段。

## 三、挂账区:等 owner 的事 + 非 SPEC 零散待办(一行一件,带去处)

> 债务表(debts.md)未建的阶段,这里就是**全部待办的家**;待办散落/约超 10 条 → 该建 debts.md。

| 事 | 去处(归谁·什么时候) | 提出日期 |
|---|---|---|
| 建异地备份 remote(私有库,SSH 认证),建好当天首推+核 0;建立之前仓库只有本地一份 | owner 亲手(方法:仓内 docs/AI-Project-Guide/07-backup-secrets.md)·**V1 全部完成后、owner 验收时**(2026-10-01 owner 拍板改期,不着急) | 2026-10-01 |
| **内容区冻结 bug**:owner 客户端切任何页签,页签条/树高亮都变但主区内容停在旧文件(2026-10-11 报障);本机三路复刻未现,phase3 全绿 | owner 复现时点 Settings → Export Diagnostics → 同机直读 %APPDATA%\com.aiprojectviewer.app.exp\diagnostics\aiv-diagnostics-<ts>.txt(live-check 行+带时间戳日志)→ 定位修复随 0.7.x 发 | 2026-10-11 |
