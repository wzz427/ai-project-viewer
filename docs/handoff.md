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

主线 = **Phase 9 Watcher(spec-009,V1.5 §183+§76–§85)**:文件变化实时监听——树自动更新 /
正在看的文件被外部(AI/别的程序)改了自动重读+轻 toast"✓ x updated" / Git 自动刷新 / 删除与改名的
页签·置顶收藏同步(§83–§85,可靠识别 1:1 才算 rename) / 防抖 300–500ms(§81) / **只盯激活项目**(§77)
/ 忽略目录 11 种(.git…target,§80)——**与树可见性是两份清单**(§28,树默认显示 dist/build/target 但 watcher 不盯)。
**发版 0.7.0 起**(owner 2026-10-11 指令"版本升到0.7";0.7.x 固定递增不跳段,版本三处已升)。
**开工前规矩(2026-10-10 owner 立规):写代码前先跟 owner 说人话对齐本 Phase 范围与关键默认**(workflow §五 A2)。
**未结大案:内容区冻结 bug**(owner 报"切换任何页签内容都不变",本机三路复刻未现;0.6.12 起诊断已装)——
复现时 Settings → Export Diagnostics,文件在 %APPDATA%\com.aiprojectviewer.app.exp\diagnostics\aiv-diagnostics-<ts>.txt,
同机直读定位;修复随 0.7.x 发。Phase 9 的"自动重读"恰好动同一片区,若其根因在查看器换装链路上,本期测试可能先撞见。
协作习惯:高频验收、编号反馈、返工轮是常态;测试零打扰红线(testing.md §1.2);e2e 一律 aivlaunch(PID 限定)。

## 一、现在在哪(最新在上)

### 2026-10-11 · spec-008(Phase 8 RUN/Trust)收口 Done;主线移交 Phase 9

> **新会话从这接** —— 读 AGENTS.md 开机三步 → 本页 → 与 owner 对齐 Phase 9 范围(若未对齐,见 〇 的规矩)
> → 立 spec-009(specs/SPEC-template.md)→ 免审开工。**发版 0.7.0 起。**

- owner 验收原话"这期收口,进下一个需求,版本升到0.7"→ spec-008 Done(0.6.9 首发+0.6.10–0.6.13 四轮返修,
  全程在 spec-008 §六+specs/INDEX 行;教训 L29–L32 在档)。**历史各轮(建仓→Phase 8)已整批蒸馏进
  docs/history/progress/progress-2026-10.md**(history/INDEX 已登记);e2e 残留诊断文件已清。
- **冻结 bug 未结转 §三挂账**:诊断已装等 owner 触发导出;phase3 58/58+git 32/32+其余全档绿佐证主线无恙。
- 版本三处(package.json / src-tauri/tauri.conf.json / src-tauri/Cargo.toml)已升 0.7.0;**0.6.13 仍为体验渠道当前版**
  (Phase 9 首个交付轮才发 0.7.0)。
- 遗留披露:owner 记事本里 README.md 标签仍留(手动关);⚠️ docs/AI-Project-Guide/ 的未提交改动归另一会话,
  勿动勿提交勿还原。

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
