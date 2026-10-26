# SPEC-011 —— Phase 10 上线前体检:性能泄漏审查 + 安全审查 + 发版准备

> Phase 10(V1.5 §184,规划内最后开发阶段,之后进 V1 验收)。前置:spec-010 已 Done。
> **本阶段禁新增产品功能**(§184 首行明文)。发版 0.7.6 起(0.7.x 递增不跳段)。
> 性能九项+安全十一项逐项过秤,审计证据表住本 SPEC §四;发版三决定 owner 已拍(§一)。

## 〇、值不值得做

§184 明列 Phase 10;九类泄漏/十一类风险虽按"内存最小化"立规逐 Phase 自律,但从无一次
**全量对账**——每类"当时以为干净"≠"今天逐调用点核过"。收益:V1 收口前最后一道系统性
体检,查出一个就赚(0.7.1/0.7.2 两层冻结根因证明"以为干净"会漏);发版三决定不定,
V1 打包无从谈起。代价:审计工时;修复可能碰任何文件(风险=审计动作本身不改行为,
只有确认的缺陷才动代码)。判:值→做。

## 一、Pre-Draft 结论

- **开工前对齐(2026-10-11,A2)**:本会话向 owner 说人话写了范围(性能体检九类/
  安全体检十一类/发版三决定+建议表),owner 原话**"开工"**=范围照 §184 全集+
  三决定按建议拍板(NSIS 安装包/不签名/不自动更新)。
- 界面:N/A——本阶段禁新增产品功能,预期零 UI 改动(修复若触及 UI 只许恢复正确行为)。
- 现状盘点:内存纪律已有基建(查看器懒加载/非激活卸载 §160.5/PDF 关页签引擎归零/
  watcher 单槽/git 防抖);安全围栏已有基建(canonicalize+根内校验/Args Array/
  git 安全旗标/opener scope)。本阶段是对账,不是从零建。

## 二、需求正文(R 编号;指针化 workflow §五 A5)

### 性能九项(§184 Performance Review;R 通式=「该类资源在所有产生点都有明确释放路径,审计留证,发现泄漏即修+回归」)

| R# | 类别 | 审什么(产生点) |
|---|---|---|
| R1 | Event Listener Leak | 前端全部 addEventListener / Tauri listen() 调用点:随组件销毁或应用级一次性 |
| R2 | CodeMirror Leak | 编辑器实例:关页签/换字号重挂载/切走后旧实例真 destroy |
| R3 | PDF Worker Leak | pdfjs worker/引擎:关最后 PDF 页签归零(lessons L15 既有),destroy 链完整 |
| R4 | Canvas Leak | pdfjs 渲染 canvas:翻页/缩放/关闭后旧画布释放,无无界累积 |
| R5 | Page Cache Leak | 页签内容缓存:关页签/删文件/改名后缓存条目清键 |
| R6 | Watcher Leak | 监听单槽:切项目/删项目停旧,无双监听;进程退出即亡 |
| R7 | DOM Leak | 长会话开关页签/查看器后 DOM 节点数不无界增长(非激活卸载 §160.5) |
| R8 | Git Process Leak | git.exe 全部命令:超时+CREATE_NO_WINDOW,结束即退,无僵尸 |
| R9 | Child Process Leak | run.rs spawn 后即忘;**持久控制台宿主=§117/§118 有意特性非泄漏**(判定口径:程序退出后无孤儿进程存活) |

### 安全十一项(§184 Security Review;R 通式=「该攻击面所有入口都有围栏,审计留证,发现缺口即修+回归」)

| R# | 类别 | 审什么(攻击面) |
|---|---|---|
| R10 | Path Traversal | 一切文件通道(read/inspect/media/binary/tree/diff/commit):canonicalize+Project Root 内校验(§143/§144)无绕行入口 |
| R11 | URL Scheme | .url 打开/浏览器移交:http/https 白名单,无 file:/javascript: 等协议逃逸(§142) |
| R12 | SVG | 图片渲染路径不执行 SVG 内脚本(onload/script/外链);无 innerHTML 注入路径 |
| R13 | Markdown Script | markdown-it 渲染链 Raw HTML 默认禁(D4/§86–§88)未被任何后加入的特性旁路 |
| R14 | Git External Diff | 全部 git 命令带 --no-ext-diff(§70),防仓库配置触发外部程序 |
| R15 | Git Textconv | 全部 git 命令带 --no-textconv(§70),同上 |
| R16 | Command Injection | 全部 spawn 调用点 Executable+Args Array(§145),无 shell 字符串拼接 |
| R17 | Project Trust | 信任门(§126–§131):未信任时 Run/EXE 全拒,Rust 围栏与前端 UX 门双层都在 |
| R18 | EXE Launch | exe/msi 仅白名单扩展+信任后可启(§122–§124),cwd 受控 |
| R19 | Script Arguments | 脚本运行=固定路径无参数面;无 -ExecutionPolicy(§120);脚本内容不经 shell 解释 |
| R20 | Frontend Shell Permission | 前端无任意执行命令面:capabilities 最小集、CSP、invoke 清单、opener scope 全核 |

### 发版准备(§184 Release Preparation;决定已拍,动作有闸)

| R# | 决定 | 拍板 |
|---|---|---|
| R21 | Windows Installer Format = NSIS Setup EXE | owner 2026-10-11"开工"(采纳 §184 初始建议) |
| R22 | Code Sign = V1 不签 | 同上 |
| R23 | Auto Update = V1 关(体验渠道更新机制不受影响,属开发基建) | 同上 |

**反例规则**:不新增任何产品功能/UI;不为审计常驻任何监控探针(一次性 e2e 探针用完即弃);
审计动作本身不改行为——**只有确认的缺陷才动代码**;全量 Benchmark(T3)与 NSIS 实际打包
是红线闸,**不代跑**(AGENTS.md 红线"发版打包、全量 Benchmark 前 owner 点头")。

## 三、验证标准(V 编号;审计型 V=证据表+测试双轨)

| V# | 对应 R | 什么样算对 | 自动/人工 |
|---|---|---|---|
| V1 | R1–R9(逐类) | §四审计表每类一行:产生点全清单(file:line)+释放路径判定+结论(净/漏已修);漏的修法带回归测试编号 | 自动(证据表+既有/新增测试) |
| V2 | R10–R20(逐类) | §四审计表每类一行:攻击面入口全清单+围栏判定+结论;缺口的修法带回归测试编号 | 同上 |
| V3 | R7 | 长会话探针(一次性 e2e,可弃):反复开关页签 N 轮后 DOM 节点数回落至基线带内,无单调增长 | 自动 |
| V4 | R9 | 探针:程序运行期间 spawn 的子进程(排除有意驻留的控制台宿主)在测试会话结束后无存活孤儿 | 自动 |
| V5 | R21–R23 | 三决定落 architecture 决策表+§1.5 Q1 归档;V1.5 §197 加审计行;tauri.conf NSIS 配置核对就绪 | 自动(文档核对) |
| V6 | 全部 | 既有回归全绿:phase3 64+git 33+recent 15+r3 8+pdf 19+vitest+cargo+check 0/0;动 watcher 链则 freeze-guard | 自动 |

## 四、技术实现方案

**审法**:每类先列"产生点/入口全清单"(grep 模式+人工核对),逐点判释放路径/围栏,
证据(file:line+一句话)填进下方审计表;发现的缺陷当场修+回归测试;审计表是本阶段
主产物,结论只住这一份。修复预期集中在:前端组件销毁钩子、缓存清理边角(改名/删除)、
Rust 侧命令超时面。不动架构。

**审计表(InDev 完成回填;证据=file:line,行号为 0.7.6 审计时点)**

| 类别 | 产生点/入口清单 | 判定 | 结论 |
|---|---|---|---|
| R1 Event Listener | addEventListener 全量 31 处:App 拖拽 95-100(onUp 配对)/main.ts 3 处(应用级)/ErrorDialog+四右键菜单(开挂卸清)/PdfViewer 120-125(unmount 清)+拖选 387-401(**activeDriver 兜底+8s 保险**,unmount 先杀)/shortcuts·stateSync·settingsStore(应用级单例)/App onMount listen 两处(unlisten 配对)/watcherStore initWatcher(应用级一次) | 全配对或应用级 | **净** |
| R2 CodeMirror | CodeViewer $effect 建视图/cleanup `v.destroy()`;0.7.4 字号重建=effect 重跑先 destroy | 配对 | **净** |
| R3 PDF Worker | pdfEngine 每文档独立 worker;acquireLib 先 terminate 旧;关最后页签 releaseEngineIfIdle 归零(L15);PdfViewer unmount: cleanup+destroy+releaseIfIdle | 配对 | **净** |
| R4 Canvas | PdfViewer releasePage→replaceChildren;虚拟化 ±2 页;renderedScale 清理 | 配对 | **净** |
| R5 Page Cache | tabsStore contentCache:closeFile:285/槽位回收:172/applyTabRenames 迁键:545/forgetTabs:559 四路全清;删除页签保内容=§83 设计 | 上界=开着的页签 | **净** |
| R6 Watcher | Rust 单槽(D6)start 换槽原子;App.svelte:201 effect 无激活项目即 stop;进程退出即亡 | 闭环 | **净**(补注:watcherStore lanes Map 按根累积两字段小对象,量级可忽略,记档不修) |
| R7 DOM | Svelte 卸载即拆;探针 V3:30 轮开关页签 document 节点数 105→105 **零增长** | 探针实证 | **净** |
| R8 Git Process | run_git_capped:10s 超时/截断即 kill/err 即 kill(125/132/143),读线程 join,CREATE_NO_WINDOW | 配对 | **净**;但命令壳同步跑主线程 → 见 P1 |
| R9 Child Process | run.rs spawn 后即忘=§117/§118 特性;探针 V4:会话结束零孤儿(target 构建树限定;owner 体验版客户端不涉) | 设计+探针 | **特性非泄漏** |
| R10 Path Traversal | resolve_file/resolve_inside/resolve_target 全 canonicalize+Path starts_with;git 侧 sanitize_rel 逐组件拒 `..`/绝对/`:magic`;hash 消毒 hex;盘根拒 | 全通道 | **净** |
| R11 URL Scheme | .url→shortcut_url(1MB 顶)→browser_url_allowed 仅 http/https(cargo 测);MD 链接 /^https?:/i 才 openUrl;file_url 百分号编码 | 双层 | **净** |
| R12 SVG | read_media data-URL→`<img>`(ImageViewer:4-6);全前端唯一 {@html}=MarkdownViewer 且 html:false | 无脚本路径 | **净** |
| R13 Markdown Script | markdown-it html:false(D4);validateLink 默认拦 javascript:;点击 handler 二道闸 | 三层 | **净** |
| R14/R15 Git 旗标 | git_base_args 全命令(pager/quotepath/optional-locks);diff_argv 带双旗标;**缺口:commit 视角 git show 两处无旗标** → 已修(show_diff_argv+commit_detail 各补 --no-ext-diff --no-textconv;cargo show_diff_argv_carries_safe_flags) | 缺口已修 | **漏已修** |
| R16 Command Injection | 全 spawn=Executable+Args Array;**缺口:cmd /K 载荷含路径元字符时 cmd 剥引号重析**(探针实证:单引号注入跑出 calc,双引号 idiom 干净)→ 已修(SpawnArg::CmdPath raw_arg 双引号 `""path""`;cargo 单元+真 spawn 回归各一) | 缺口已修 | **漏已修** |
| R17 Project Trust | §128/§129 定义的 UX 确认框=runWithTrust(handoffMenu:90);Rust 持扩展名+路径围栏;test_mode 自动取消;MSI 无 Run 行(§126) | 与规格一致(规格即 UX 门;渲染层攻破需先过 CSP,且渲染层从不解释项目内容为代码) | **按设计** |
| R18 EXE Launch | run_project_executable 仅 .exe+resolve_target 围栏+cwd=自身目录;白名单住 Rust | 净 | **净** |
| R19 Script Arguments | script_argv 固定 argv 无用户参数;无 -ExecutionPolicy(§120,cargo 断言);-File 不经 shell 解释 | 净 | **净** |
| R20 Frontend Shell | CSP:script 回落 default-src 'self'、connect 无外网、worker blob:;invoke 清单全语义命令;**缺口:capabilities 曾授渲染层 opener:allow-open-path `**`(任意路径 OS 关联打开=可执行)+opener:default(reveal/mailto)** → 已修(仅留 allow-open-url http/https;插件文档证实 scope 只管 IPC 层、Rust 侧自由函数不受影响;phase3 两探针断言 open_path/file:// 双拒) | 缺口已修 | **漏已修** |

**性能侧两笔 L35 同族修复(非泄漏类,主线程卫生)**:

| # | 问题 | 修法 |
|---|---|---|
| P1 | git_diff/git_commit_detail 同步命令起 git.exe 跑原生主线程——慢仓库点 diff 冻窗至 10s(L35 同族,git_snapshot 已 async 而这两处漏网) | 转 async+spawn_blocking(diff_inner/commit_detail_inner 拆同步核,cargo 测试直测内核) |
| P2 | read_text/media/binary+inspect 四读通道同步(最高 100MB 读盘+27MB base64 在主线程)——冷缓存开大 PDF 冻窗 | 同上转 async+spawn_blocking |

| D# | 决策 | 依据 | 备选 | 排除理由 |
|---|---|---|---|---|
| D1 | 审计先行逐项留证,不建常驻监控框架 | 一次性对账;常驻探针违背内存第一原则,审计价值在"此刻全量核过" | 建泄漏探测框架 | 本阶段禁功能;探针自身=新驻留 |
| D2 | 修复零新 UI;用户可感知 bug 一律修(不称"优化") | §184 禁令+AGENTS.md 边际效益条款 | 把顺手小改塞进本阶段 | 范围漂移 |
| D3 | T3 全量 Benchmark 与 NSIS 实际打包=闸前请示,不代跑 | AGENTS.md 红线 | 直接跑 | 红线不可代拍 |
| D4 | 发版三决定=R21–R23(owner"开工"确认 §184 初始建议);V1 正式打包动作不在本 SPEC | §184"发布前明确决定"指决定本身;打包是独立动作且是红线闸 | 本阶段顺手打出安装包 | 越红线 |
| D5 | 版本 0.7.6 起(三处) | 0.7.x 递增纪律(handoff §二) | 0.8.0 | 无 owner 指令不换段 |
| D6 | Idle RAM 179MB vs §163 target 150MB:Phase 1 已判"超标全来自 WebView2 空底座,非 gate";本阶段只审"我们这边没白驻留",不承诺压到 150 | §163 定性 target 非 gate;真实判据=同场景明显低于 VS Code(留给 T3 Benchmark 判) | 强压底座 | 越权且不可达 |
| D7 | cmd /K 防注入用双层引号 `""path""`+raw_arg | cmd 的 /C//K 文档行为:引号内含元字符即剥外层引号重析(探针实证 2026-10-11:单层引号下 `a&calc&` 文件夹分裂命令行跑出 calc;双层剥外留内,脚本照跑);Rust 标准转义与 cmd 规则不兼容,raw_arg 全控 | 仅单层引号 | 探针实证注入 |
| D8 | opener 收紧=删渲染层授权而非弃插件 | 插件文档:scope 仅 IPC 层强制,Rust 自由函数无检查→handoff.rs 不受影响;渲染层唯一合法用途=open_url http/https(MarkdownViewer 链接) | Rust 侧改直调 Win32 | 无收益(授权删干净即达目的) |

**内存账(交付时报)**:零新增驻留(四处修复均为线程池调度,无新常驻结构;SpawnArg=argv 构建期临时值);watcherStore lanes Map 为既有行为(见 R6 补注)未变。

## 五、测试覆盖矩阵(Draft→Ready 硬产物)

| R# | V# | 测法 | 所需夹具 | 状态 |
|---|---|---|---|---|
| R1–R9 | V1 | 代码审计证据表(§四,逐产生点 file:line) | 无 | ✓ |
| R7 | V3 | 一次性 e2e DOM 探针:30 轮开关页签节点数 105→105 零增长 | AIV-TestProject | ✓ |
| R9 | V4 | 一次性孤儿进程探针:会话结束 target 构建树+fixture 引用零存活 | 无 | ✓ |
| R10–R20 | V2 | 代码审计证据表+既有 cargo/vitest 安全测试对账+三缺口修复回归 | 无 | ✓ |
| R14/R15 | — | cargo show_diff_argv_carries_safe_flags(新) | 无 | ✓ |
| R16 | — | cargo cmd_path_with_metacharacter_stays_one_token + bat_in_ampersand_folder_runs_via_verbatim_quoting(真 spawn 注入回归,新×2) | 无 | ✓ |
| R20 | — | phase3 p10_opener_open_path_denied + p10_opener_file_url_denied(渲染层直调 IPC 断言拒绝,新×2) | AIV-TestProject | ✓ |
| R21–R23 | V5 | 文档核对:V1.5 §197 审计行+architecture Q1 归档/决策表/硬规则+tauri.conf NSIS targets 就绪 | 无 | ✓ |
| 全部 | V6 | 全档回归:phase3 **66**(+2)/git 33/recent 15/r3 8/pdf 19/vitest 60/cargo **99**(+3)/check 0/0/**freeze-guard 0/82**(动 watcher→git 链必跑) | scripts/e2e | ✓ |

## 六、变更与验收记录

| 日期 | 跃迁/变更 | 产物 |
|---|---|---|
| 2026-10-11 | 立项 Draft→Ready(A2 对齐完成:owner 看说人话范围表后原话"开工";R/V 与 §184 逐条对上,九+十一+三全覆盖) | 测试覆盖矩阵 6 行 |
| 2026-10-11 | InDev→InTest(**0.7.6 已发体验渠道,等 owner 复验**):审计表 20 行全回填(净 14/按设计 1/特性 1/漏已修 3+主线程 2);四修复=git 旗标+async、读通道 async、cmd /K 双引号防注入、opener 授权收紧;R9 探针插曲:注入实证时 calc 短暂弹窗(已清理,测试纪律教训——注入类真 spawn 测试的载荷命令应选无害命令) | 全档数字见 §五 V6 行 |
| 2026-10-11 | **返修一轮(0.7.7)**:owner 复验报障"点击字体放大缩小…有时按钮显示蓝色"——根因=连点落进双击窗口,浏览器按词选中按钮标签,原生 ::selection 蓝挂在按钮上(**L40**:`.viewer-body user-select:text` 罩住工具栏+Chromium 对 button 文字默认不豁免);修=全局 `button{user-select:none}`+两工具栏容器 none+容器内 input 显式恢复 text | 探针:修前 dblclick selection='+' 199 蓝像素/tri 'A+\n' 343 → 修后全空/19 基线;phase3 +1 `toolbar_buttons_not_selectable`(**67**/67)+pdf 19+r3 8+vitest 60+cargo 99+check 0 |
| 2026-10-12 | **T3 全量基准已跑**(owner"开跑"红线授权):A–I+Phase 1 Baseline 门全过(前端就绪 ≤1.2s/空闲 CPU 0.12 CPU·s·min⁻¹/空闲 RAM 200.2MB 未达 150 target=非 gate 判读留档/10.5 万文件零递归/Agent 防抖 3.5:1/PDF 5 页签 1.6×/25k 行 diff 截断/git-suite 33/33);附带 PDF 驻留 5 轮+GC 探针=**无应用侧无界泄漏**;基建发现 L42。**等 owner 验收** | 数字全文=testing.md §4 T3 行;脚本=scripts/e2e/benchmark-suite.py |
| 2026-10-12 | **验收通过(InTest→Done)**:owner 原话『上面这几个项目可以都先过了吧,但过了不代表后面不会改。我最近在用的过程当中,会不断看到并发现一些新问题,到时候再告诉你』;NSIS 打包=发布动作另行启动,届时仍须 owner 点头(webviewInstallMode 三选一) |
| 2026-10-26 | **NSIS 打包执行完毕(收尾遗留清偿)**:owner 拍板 webviewInstallMode=**offlineInstaller**(三选一,原话「离线大包」);0.8.13 安装包(~210MB)交付;调试端口债务同轮清偿——正式版门禁按渠道标识(.exp/debug 保留 9322,默认标识+release 永不设;merge_webview_args 纯函数 6 单测+正式版启动实证全进程树零监听) | 安装包路径与验证记录=docs/testing.md 0.8.13 行;决策=architecture §12 0.8.13 行 |
