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

主线 = **spec-012 已 Done(2026-10-12 owner 验收原话"spec012可以done"),下一步=T3 全量性能基准**
(A–I 档+Phase 1 Baseline,口径=V1.5 §162–§173+testing.md §4.9;owner 已预告授权,
**开跑前按红线再确认一次**)→ spec-011 复验转 Done → NSIS 实际打包届时点头
(含 webviewInstallMode 三选一,D7/R21)。评审报告已归 history/code-reviews/(快照轴)。
**版本段 0.7.x 固定递增不跳段**;tsconfig 收紧记档待清(60 处/8 文件,去处=下一前端专项批次,spec-012 D12)。
挂账两件见 §三(冻结 bug 取证 / 异地备份 remote)。
Phase 10 全程蒸馏在 history/progress/progress-2026-10.md(Grep spec-011/0.7.6/0.7.7/L39/L40);
审计证据表住 specs/spec-011-performance-security-release.md §四。
**未结大案:内容区冻结 bug**(owner 报"切换任何页签内容都不变",本机三路复刻未现;0.6.12 起诊断已装)——
复现时 Settings → Export Diagnostics,文件在 %APPDATA%\com.aiprojectviewer.app.exp\diagnostics\
aiv-diagnostics-<ts>.txt,同机直读定位;修复随 0.7.x 发。
协作习惯:高频验收、编号反馈、返工轮是常态;测试零打扰红线(testing.md §1.2);e2e 一律 aivlaunch(PID 限定)+
**park_offscreen(L34)**。

## 一、现在在哪(最新在上)

### 2026-10-12 · spec-012 验收 Done,主线交棒 T3 全量基准

- owner 原话"spec012可以done"落 spec-012 §六(InTest→Done 硬门过);INDEX 同步两行
  (spec-012→Done 冷却待搬;spec-011 去处切"下一动作=T3,开跑前按红线再确认");
  评审报告 git mv → history/code-reviews/(INDEX 快照轴登记;断链修指四处:spec-012 头引/INDEX
  两行/progress 时间轴)。
- 下一步 = **T3 全量基准:开跑前找 owner 再确认一次**(红线"全量测试批准";预告授权留痕在
  INDEX spec-011 行)→ 跑完 spec-011 复验 → NSIS 打包届时点头(webviewInstallMode 三选一)。
- 遗留仅 L-c6 记档:tsconfig noUncheckedIndexedAccess 实测 60 处/8 文件,超 D6 止损线 20 未在本批清,
  去处=下一前端专项批次(2026-10-12 owner 问询过是什么,已在对话中解释)。

### 2026-10-12 · 本段收口:code review→修复批 0.7.8→高亮返修 0.7.9,主线交棒新对话

> **新会话从这接** —— 读 AGENTS.md 开机三步 → 本页 → specs/spec-012-code-review-fixes.md(§六)+lessons L41。
> 本段全程:全面 code review(报告 44 条)→ owner"开工,完成spec012" → 43 条一批修完(42 落地+L-c6 止损)
> → 全档回归全绿 → 0.7.8 发体验渠道 → InTest 报障(右键动作后树高亮)当日返修 0.7.9 再发。
> 全程蒸馏在 history/progress/progress-2026-10.md(Grep spec-012/0.7.8/0.7.9/L41)。

- 交接要点:①体验渠道当前版 **0.7.9**,spec-012 验收已过(见上条)——评审报告已归
  history/code-reviews/ 快照轴;②T3 全量基准=V1.5 §162–§173+testing.md
  §4.9 口径,owner 已预告授权(原话留痕在前段收口条,蒸馏件可 Grep "T3 排期授权");③NSIS 打包须届时点头
  (webviewInstallMode 三选一,spec-012 D7);④新报障第一动作=Settings→Export Diagnostics 同机直读;
  ⑤动 watcher 链发版前必跑 freeze-guard;⑥tsconfig 收紧记档待清(60 处,去处=下一前端专项批次)。
- 挂账不变:冻结 bug(取证路径见 §〇)/异地备份 remote(V1 验收后 owner 亲手)。
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
