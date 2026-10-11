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

主线 = **spec-009 InTest:Phase 9 Watcher 已发 0.7.0,等 owner 复验**(复验清单见 §一 首条);
过了 → **Phase 10(性能/安全/发版准备,§184,spec-010)——本阶段禁新增产品功能**(九类泄漏
审查+安全审查+V1 收口)。**版本段 0.7.x**(owner 2026-10-11 指令"版本升到0.7";固定递增不跳段)。
**未结大案:内容区冻结 bug**(owner 报"切换任何页签内容都不变",本机三路复刻未现;0.6.12 起诊断
已装)——复现时 Settings → Export Diagnostics,文件在 %APPDATA%\com.aiprojectviewer.app.exp\
diagnostics\aiv-diagnostics-<ts>.txt,同机直读定位;修复随 0.7.x 发。注意:Phase 9 的自动重读
({#key}=rel+contentRev 重挂载)恰好重写了查看器换装链路——若冻结 bug 根因在那一段,owner 复验
0.7.0 时可能直接消失或变形,留意复验反馈。
协作习惯:高频验收、编号反馈、返工轮是常态;测试零打扰红线(testing.md §1.2);e2e 一律
aivlaunch(PID 限定)+**park_offscreen(L34)**。

## 一、现在在哪(最新在上)

### 2026-10-11 · 0.7.2 返修二轮:启动卡死的第二层根因(0.7.1 仍冻,owner"升级都点不了"→我代换装)

> **下一步从哪接** —— owner 客户端已由我换装 0.7.2 并当场验证健康(真实状态启动 0/75 无响应,
> CPU 0.4s)。owner 复验:开着他真实的项目组合正常用,确认不再卡死+监听功能本身;过 → spec-009
> Done → Phase 10。

- **根因(lessons L36,与 0.7.1 修的 L35 是两层独立问题)**:notify-debouncer-full 在 Windows 默认
  启用 `FileIdMap`,其 `add_path` 在 `watch()` 里对项目根**全树 WalkDir(follow_links)+逐文件开
  句柄**——真实仓库(node_modules/构建目录/符号链接)分钟级;我的 start_project_watch 是同步
  命令=主线程 → 一启动监听就冻死。e2e 小夹具(330 文件)毫秒级完成所以全绿放行。
- 修:`new_debouncer_opt+NoCache`(改名配对用路径 From/To,L33,文件 ID 缓存纯属白付)+
  start/stop_project_watch 全转异步+spawn_blocking(监听生命周期永不进主线程)。
- 取证链:真实状态副本 100% 复现(75/75)→"禁用监听"构建二分一锤定音(0/50)→渲染层安静+
  原生 CPU 满 → 直奔 Rust 源码闭环。教训附:**复现用的状态副本会被应用回写,每次必须重新拷**
  (旧副本被写成空壳曾造成"健康"假象);**夹具必须含真实规模目录**(本仓库即最佳夹具)。
- 全档:cargo 95/95+vitest 50/50+check 0/0+phase3 63/63+git 33/33+r3 8/8+pdf 19/19+
  freeze-guard 0/83;真实状态副本修后 0/75 无响应。

### 2026-10-11 · 0.7.1 返修:启动即卡死(owner 报"一打开就卡死,点击全是 ⌛️")

> **下一步从哪接** —— owner 点 Update(0.7.1)复验:启动不再卡死(可开着你常用的、正在被
> AI 写文件的项目试);连同 0.7.0 的监听清单(§一 下一条)一起过 → spec-009 Done → Phase 10。

- 根因(lessons **L35**):Tauri 2 **同步命令跑在原生主线程**,`git_snapshot`(每次起 git.exe,
  真仓库 0.1–2s)被监听放大成每事件批次触发——AI 会话持续写盘时主线程被占死不泵消息=⌛️。
  小夹具 e2e 全绿没拦住(单批只占几十 ms);**渲染进程健康≠窗口没冻**(CDP evaluate 测的是
  渲染侧),测原生必须 SendMessageTimeout(WM_NULL)。
- 修:git_snapshot → async 命令+spawn_blocking(离主线程;聚焦/手动刷新的隐性卡顿一并消除)+
  watcherStore 单 lane 串行+忙时合并批次(防堆积,无 setTimeout——L34)。
- 新常驻守卫 **watcher-freeze-guard.py**(凡动 watcher 链发版前必跑):修前原生窗口 40 采样
  29 无响应,修后 **0/83 PASS**;全档 phase3 63/63+git 33/33+r3 8/8+pdf 19/19+vitest 50/50+
  cargo 95/95+check 0/0。

### 2026-10-11 · spec-009(Phase 9 Watcher)交付:0.7.0 已发体验渠道,等 owner 复验

> **下一步从哪接** —— owner 点 Update(0.7.0)验,全程零手势(不用点 ↻):①开着的项目里
> 外部加/删文件,左侧树半秒内自己跟;②正开着的文件被外部改→内容自动换新+右下角
> "✓ 文件名 updated"(滚动位置保留);③删掉开着的文件→页签显示"This file has been
> deleted."+Close Tab;④外部改名→页签标题跟着改(置顶也跟);⑤Git 项目徽标数字自动变。
> 过 → spec-009 Done → Phase 10(性能/安全/发版准备,§184,本阶段禁新增产品功能)。

- 开工前对齐完成:owner 要求行业对照(VS Code/Zed/Sublime/JetBrains 均"树自动+干净静默
  重载")后拍板照建议方案(§183 全集+自动重读+提示保留),spec-009 §一/§六留痕。
- 交付:Rust `watcher.rs`(notify-debouncer-full 400ms 单槽+§32 忽略清单 Rust 侧过滤+
  相邻配对 rename+storm 上限 200 折叠)+ 前端 watcherStore 编排(改名应用→树重列→开着的
  页签 reloadFile→refreshGitNow→激活页签 toast §82)+contentRev 重挂载换装(顺带修 Ctrl+R
  对代码页签不刷新的旧账)。App effect 驱动激活项目 start/stop(§77 只盯一个)。
- 测试:cargo **95/95**(+9 含真监听冒烟)、vitest **50/50**(watcherApply 11 新)、check 0/0、
  phase3 **63/63**(+5 watcher)、git-suite **33/33**(+1 徽标自动往返)、r3 8/8、pdf 19/19。
- 两教训入档:**L33**(Windows notify 的 rename=单事件 `Name(Both)` 带 [from,to],按
  From/To 两事件的心智模型必漏)/ **L34**(隐藏 WebView2 冻的是定时器队列不是页面——fs
  事件照常送达,链路里挂 setTimeout 防抖会死;watcher→git 用 refreshGitNow 直取,e2e 一律
  park_offscreen)。内存账:激活项目一个 watcher(切走即 drop),前端零新增定时器。

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
