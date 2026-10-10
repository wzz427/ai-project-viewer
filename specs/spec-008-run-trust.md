# SPEC-008-RunTrust —— 运行脚本/程序与项目信任:可见控制台,先信任后执行

> Phase 8(V1.5 §182)。前置:Phase 7 已 Done。发版 0.6.9 起。
> HTML/URL → Browser 的菜单与命令 Phase 6 已交付;本轮补它的 §115 安全白名单接线。

## 〇、值不值得做

§182 明列 Phase 8;§142 行为总表把 Run/Info 定为权威规格;§143 把 Run 列入
必须路径验证的动作。**不做的代价**:右键里永远没有 Run,用户去资源管理器双击
——本应用"检视+轻执行"的闭环缺一环;且 Phase 6 遗留的 .url 协议白名单未接线
(§115 违规,安全隐患)需要本轮一并销。

## 一、Pre-Draft 结论

- 现状盘点:菜单骨架 Phase 6 已预留挂点(handoffMenu 注释"Run Script entries
  are Phase 8");`trustedForExecution` 字段 Phase 4 已入持久化形状(现恒写
  false);`browser_url_allowed` 已定义已测但 `open_in_browser` 未调用(真漏洞)。
- **§118 实验已完成**(2026-10-10,四组对照,%TEMP%\aiv-p8-console):
  A `cmd /K x.bat`→脚本体完成后宿主 3s 仍存活(可读)✓;B `powershell -NoExit
  -File x.ps1`→同 ✓(本机策略 RemoteSigned;Restricted 机器上策略报错将留在
  持久窗口里可见=诚实失败);C 直启 bat(对照)→体完即关,**读不到**✓(证实
  §118 担忧,宿主是必需的);D 为实验脚本自身引号 bug,与结论无关(exe 直启
  行为同 C 机制,§117 只约束脚本,exe 不要求驻留)。
- 疑问需确认项:无(策略已由 §118 授权实验定)。

## 二、需求正文(R 编号;指针化 workflow §五 A5)

| R# | 需求(指针) |
|---|---|
| R1 | Trust 默认与门(§128):新项目默认 Untrusted;首次运行 .ps1/.cmd/.bat/.exe 前弹确认框(原文文案,[Trust and Run]/[Cancel]);Cancel=不运行不落 trust |
| R2 | Trust 持久化/可撤销/不跨项目(§129):随 AppState 每项目字段;项目菜单 Trust Project for Execution / Untrust Project(§141) |
| R3 | 脚本运行(§116/§137):.ps1/.cmd/.bat 右键 Run Script;左键=Code Viewer,绝不因单击/双击执行 |
| R4 | 可见控制台(§117/§118):独立可见外部 Console、stdout/stderr 可见、快速结束结果仍可读;进程创建策略=§一 实验结论(cmd /K / powershell -NoExit 宿主 + CREATE_NEW_CONSOLE) |
| R5 | PowerShell 遵守系统 ExecutionPolicy,禁止 -ExecutionPolicy Bypass(§120) |
| R6 | 脚本 cwd=Project Root(§121);Run from Script Directory=P1 不做 |
| R7 | Toast(§119 原文):✓ <name> launched / Failed to launch <name>;Toast 不替代 Console |
| R8 | EXE(§122/§123/§124/§139):左键=Executable Info(name/Windows Executable/Size/Modified/Path/This file cannot be previewed.);右键 Run=绝对路径直启、禁 cmd /c 拼接、cwd=EXE 父目录;.msi 无 Run(§126) |
| R9 | 前端无通用执行能力(§133):语义命令 run_project_script/run_project_executable;路径 Rust 侧 canonicalize 校验(§143/§144);运行扩展名白名单住 Rust |
| R10 | Python/JS/SH 不提供 Run(§127) |
| R11 | 项目菜单补齐 §141 全项:Refresh Project + Trust/Untrust(三项 handoff 已在) |
| R12 | .url Open in Browser 接上 §115 白名单(http/https only;修 Phase 6 未接线) |

## 三、验证标准(V 编号)

| V# | 标准 |
|---|---|
| V1 | Trust 门:e2e——untrusted 项目点 Run Script 无 launch toast/无 trust 落地(test 模式自动 Cancel);点 Trust Project for Execution 后 state 文件里 trustedForExecution=true;Untrust 还原 false |
| V2 | 控制台策略:cargo 无窗测试——/K 与 -NoExit 宿主在脚本体完成后仍存活(CREATE_NO_WINDOW 变体验证宿主语义);真机抽检一轮补可见性 |
| V3 | 无 -ExecutionPolicy:cargo 断言 ps1 argv(纯函数) |
| V4 | Toast 文案:e2e——失败路径(不可运行目标)出 "Failed to launch …" |
| V5 | Executable Info:e2e——左键 demo.exe 出 Info 卡(Windows Executable/Size/Modified/Path/cannot be previewed) |
| V6 | 菜单矩阵(§142):ps1/cmd/bat=Run Script+Notepad/VS Code;exe=Run、无 Notepad/VS Code;msi=System Default、无 Run;py/js=无 Run |
| V7 | 项目菜单:Refresh Project 存在且可点;Trust/Untrust 互斥出现 |
| V8 | .url 白名单:cargo——javascript:/powershell:/file: 拒,http/https 过(接线后走 open_in_browser 的实际分支) |
| V9 | cwd:cargo argv/启动参数断言(脚本=项目根,exe=父目录) |

## 四、技术实现方案

Rust 新模块 `run.rs`:两语义命令。脚本:`cmd.exe /K <abs>`(bat/cmd)或
`powershell.exe -NoExit -File <abs>`(ps1),CREATE_NEW_CONSOLE,cwd=项目根;
EXE:`Command::new(<abs>)` 直启,cwd=父目录,CREATE_NEW_CONSOLE。扩展名白名单+
resolve_target(复用 handoff.rs 的 canonicalize 围栏)都在 Rust。argv 由纯函数
`script_argv`/`exe_launch` 构造(可测)。FileInspection 增 `modified: u64`(ms),
Executable Info 复用。`open_in_browser` 的 .url 分支接线 browser_url_allowed。

前端:ProjectTab 增 trustedForExecution(恢复/持久化接线,buildAppState 读活值);
handoffMenu 增 script/exe 菜单分型与 Run Script/Run 条目;run 前过 trust 门
(ask 确认框,原文文案;test_mode_active=自动 Cancel);viewerType 增
"executable" 路由+ExecutableInfoViewer(纯 stat 卡);ProjectContextMenu 增
Refresh Project/Trust/Untrust(§141 顺序);toast 照 §119 文案。

| D# | 决策 | 依据 | 备选 | 排除理由 |
|---|---|---|---|---|
| D1 | 控制台策略=持久宿主:bat/cmd→`cmd /K`,ps1→`powershell -NoExit -File`,均 CREATE_NEW_CONSOLE | §118 授权实验定;C 组对照证实直启读不到;宿主存留=快结束可读 | 包装 pause 的 /C 变体 | pause 需按键语义混乱;/K 是"终端跑完留着"的 VS Code 惯例 |
| D2 | Trust 住前端 projectState,Rust 不知 trust | trust 是 UX 门;真安全边界=扩展名白名单+路径围栏(Rust);与 vsCodeNewWindow 同构 | Rust 管 trust | 多一状态源必漂,门在点击处 |
| D3 | 确认框复用 ask()(同 5–20MB 先例);test 模式自动 Cancel | e2e 零打扰无法驱动原生 TaskDialog(lessons L7);Cancel 是无副作用分支 | 自绘 HTML 对话框 | 又一套 UI;原生已有先例 |
| D4 | .exe 左键=新 viewerType "executable";.msi 维持 unsupported | §142 权威表;msi 明文 Unsupported(§126) | 都归 unsupported | §122 要求 EXE 有 Info 卡 |
| D5 | 无参数、无 stdin、spawn 后即忘(不 wait 不 kill) | 菜单不传参;子进程归用户;内存最小(零驻留) | 传参/管理子进程 | §118 安全审查项 Script Arguments;V1 无场景 |
| D6 | FileInspection 增 modified(ms) | §122 要 Modified;stat 顺手,无额外 IO | 独立命令 | 一次 IO 拆两次 |
| D7 | Toast 文案照 §119 原文,info/error 两 kind | 字面 | 自拟 | owner 验收对原文 |
| D8 | .url 白名单在 shortcut_url 之后、open_url 之前接线 | 修 Phase 6 未接线;javascript:/powershell: 经 ShellExecuteW 可执行代码 | 维持现状 | §115 明文禁止;安全审查在列 |
| D9 | e2e 永不真 launch(零打扰红线);真机抽检一轮由 agent 跑后关闭 | 可见控制台=抢前台;红线.testing.md §1.2 | e2e 真跑 | 违红线 |
| D10 | cmd /K 传参用 Command::arg 引号包裹,不做字符串拼接 | §123 精神;路径含空格/CJK 实证过(A 组) | 拼命令行字符串 | 注入面 |
| D11 | 版本 0.6.9(三处) | 0.6.x 固定递增不跳段(owner 2026-10-10 立规) | 0.7.0 | 明令不跳段 |
| D12 | Refresh Project 菜单项复用 App 的 refreshAll 通路(树+git) | §141 字面;与 ↻ 同源防两套刷新 | 只刷树 | 两套状态走岔 |

**内存账**:trust=每项目一个布尔(入既有持久化形状,零新增驻留);运行=spawn
后 Child 即弃(不 wait/不 kill/不收集,零驻留);ExecutableInfoViewer=纯 stat
卡(无内容缓冲,关页签即释放);Toast 既有单槽。无新增定时器/轮询。

## 五、测试覆盖矩阵(Draft→Ready 硬产物)

| R# | V# | 测法 | 所需夹具 | 状态 |
|---|---|---|---|---|
| R9 | V6 部分 | vitest:menuKindOf 分型(script/exe/msi/非脚本) | 无 | ✓ |
| R9/R3/R8 | V3/V9 | cargo:script_argv 纯函数(ps1 无 -ExecutionPolicy;cwd 断言)+扩展名白名单拒绝+越界拒绝 | cargo 临时目录 | ✓ |
| R4 | V2 | cargo:宿主存活性(CREATE_NO_WINDOW 变体,marker+3s 存活) | 同上 | ✓ |
| R12 | V8 | cargo:.url 白名单接线(javascript: 拒/http 过) | 同上 | ✓ |
| R1/R2 | V1 | e2e:untrusted 点 Run 无事发生;Trust 菜单翻转+state 落盘 | AIV-TestProject 增 hello.ps1/hello.bat/sample.msi(demo.exe 已在) | ✓ |
| R7 | V4 | e2e:失败 toast 文案 | 同上 | ✓ |
| R8 | V5 | e2e:左键 demo.exe 出 Info 卡字段 | demo.exe | ✓ |
| R3/R8/R10 | V6 | e2e:菜单矩阵(ps1/cmd/bat/exe/msi/py) | 同上 | ✓ |
| R11 | V7 | e2e:Refresh Project/Trust/Untrust 项 | 同上 | ✓ |
| R4 可见性 | V2 补 | 真机抽检:agent 手跑一轮(窗口出现/输出可读/手动关),记档 | %TEMP% 脚本 | ✓ |

## 六、变更与验收记录

| 日期 | 跃迁/变更 | 产物 |
|---|---|---|
| 2026-10-10 | 立项 Draft→Ready(R/V 与 V1.5 §115–§129/§136–§144/§182 逐条对上;§118 策略实验已完成见 §一) | 测试覆盖矩阵 10 行 |
| 2026-10-10 | **开工前需求对齐**(owner 抓偏后立规,workflow §五 A2 当日收紧):方向确认=就做这套;控制台=跑完留窗手动关(D1 与 owner 选择一致);已写的 Rust 层在确认前完成,未提交——确认后继续 | owner 原话:"phase8 是干什么的?你在开工前一定先跟我对接一下需求,别自己就这么开干了"+当轮两答 |
| 2026-10-10 | InDev→InTest(0.6.9 已发体验渠道,等 owner 复验) | cargo **86/86**(run.rs 新 8:argv 无 -ExecutionPolicy/宿主存活性 stdin 持管法/白名单/越界;handoff +1 .url 禁协议接线——Phase 6 遗留漏洞销账);vitest **39/39**(menuKind 5 新+trust 往返);check 0/0;phase3 **54/54**(+10:菜单矩阵/info 卡/未信任自动取消[零打扰红线:runWithTrust 在 test_mode_active 下自动 Cancel]/项目菜单 Trust 翻转/失败 toast);git-suite 31/31+r3 8/8+pdf 19/19;**run-live-check 真机 PASS**(信任菜单→Run Script→WindowsTerminal 控制台出现+marker+2.5s 驻留;Win11 终端宿主归因法=L30);两新教训 L29(release 构建法)/L30(终端宿主+stdin EOF);内存账:trust=每项目一布尔入既有形状,运行 spawn 后即忘,info 卡纯 stat 无内容缓冲,零新增定时器 |
| 2026-10-10 | **返修一轮(0.6.10)**:owner 指令"新菜单项加了以后,底部右键出来的列表还是一定能够全部显示"——实证五种菜单(script/exe/msi/textLike/project)底部右键均自适应落位(clampMenu 量实际高度,产品代码零改动);守卫加码:phase3 +3 断言(script/exe/project 每按钮均在视口内),56/56 | 守卫是本轮唯一交付物(防未来回归会红) |
