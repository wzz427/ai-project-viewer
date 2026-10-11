# code-review-2026-10-11 —— V1 收口前全面代码评审报告

> 评审对象:整个项目完整代码 @ 0.7.7(commit fc82c60)。owner 指令"对这个项目做一次全面的 code review"。
> 方法:四路并行深读(Rust 后端 / 前端状态层 / 前端组件层 / 0.7.6–0.7.7 修复专项+配置审计),
> 全部高、中级发现经评审会话逐条回读源码验证属实;已知项(lessons L1–L40、spec-011 审计表
> 判"净"且现状未变)不重复收录。
> 基线实测(2026-10-11):svelte-check 0 错 0 警 / vitest 60/60 / cargo 99/99,全绿。
> 回收方式:修复批(0.7.8)逐条消费本清单后,本文件归档进 history/。
> 对号说明:AI-Project-Guide 无评审报告模板,本文件按总原则"没有才允许自创"建,一次性证据。

## 总结论

代码质量整体高于同类规模项目平均水准:架构纪律执行到位,教训以结构性修法落地,
安全围栏经全仓核对一致,**无 Critical 级(数据丢失/安全突破)发现**。
存在 2 高 / 15 中 / 约 25 低真实缺陷,集中在三件事:
① 0.7.6 自立"重活禁上主线程"规则没有全量核对(updater/13 个同步命令长尾);
② PDF 查看器"完成时写回"模式缺取消语义(renderedScale/scrollTimer/runSearch 同根因三次现身);
③ 两处解析器没覆盖的输入形态(多行提交消息、merge 提交 combined diff)。

## 高(2 条,建议优先修)

### H1 提交详情丢失多行提交消息,正文行可成假文件条目

- 位置:`src-tauri/src/git.rs:792-826`(parse_commit_detail)、格式串 `git.rs:855`
- 机理:`--format=%H%x1f%an%x1f%aI%x1f%B` 的 `%B` 是**多行**原始正文,解析只取第一行当
  header,正文行全部进入文件条目解析循环。①Message 字段只显示 subject(多行消息高频,
  用户可见);②正文行含单个 TAB 时命中**无 alphanumeric 守卫**的两字段分支(`:812`),
  生成指向不存在路径的幻影文件条目。既有测试只用单行消息故全绿。
- 修法:格式串尾部加记录分隔符(如 `%B%x1e`),解析按 `\x1e` 切 header 与文件区。
  补一条多行消息夹具回归。

### H2 更新检查在原生主线程整读 exe 做 md5——每次启动必跑,无更新也白读

- 位置:`src-tauri/src/updater.rs:77-93`(check_update)、`:116-127`(apply_update)
- 机理:同步命令里 `md5_of(&incoming), md5_of(&current)` 元组两臂都求值——即使
  updates\ 不存在(连 dev 构建)也把运行中 exe(约 6MB)主线程整读;UpdateButton 挂载即调
  =体验版**每次启动**都付(冷缓存/杀软扫描下百 ms 级冻窗)。apply_update 更重:整 exe
  拷贝+三次全读(约 24MB IO)同步跑主线程,点 Update 即冻窗。L35 同族,spec-011 P1/P2
  只圈了 git+四读通道,漏了 updater。
- 修法:两命令转 async+spawn_blocking;读 current 前先判 incoming.exists()。

## 中(15 条)

### 正确性——用户可感知

| # | 问题 | 位置 |
|---|---|---|
| M1 | 从树重开**已开着**的 PDF 页签,阅读位置重置回第 1 页——addOrActivate 保留清单(markdownMode/jsonMode/scrollPosition/pinned)独缺 pdfState,而 openFile 的 PDF 分支每次构造 `page:1` 默认值,`Object.assign(existing, tab)` 先覆盖后恢复漏了它 | `src/lib/stores/tabsStore.svelte.ts:138-143, 339-348` |
| M2 | **merge 提交**的详情 diff 是 combined 格式(`@@@` 头、双前缀行),前端 HUNK_RE 只认 unified——行号错位、内容丢失;`git log -n 20`(git.rs:558)无 --no-merges,RECENT COMMITS 含 merge 可点入。spec-011 R14/R15 只核旗标未核输出格式族(审计盲区) | `src-tauri/src/git.rs:742-757` + `src/lib/services/diffSideBySide.ts:30` |
| M3 | Markdown 查看器切 Source 再切回不恢复滚动;且在 Source 模式下切走/关页签,卸载钩子持 onMount 时的死引用(container 已换绑),离屏元素 scrollTop=0 把 CodeViewer 刚保存的真实位置**覆盖为 0**——滚动保存/恢复对切过模式的 MD 页签整体失效 | `src/lib/components/Viewers/MarkdownViewer.svelte:78-84, 132-137` |
| M4 | 快速切项目(A→B)后活着的可能是旧项目 A 的 watcher:两个 start_project_watch 各自 spawn_blocking,**完成顺序不保证**(canonicalize+watch() 耗时因盘况而异),后完成者覆盖槽位;前端 fire-and-forget 不 await。表现为 B 的实时刷新静默失效直到下次切换(A 的批次也被前端丢弃)。spec-011 R6"换槽原子"只对了单次 swap,没对乱序 | `src-tauri/src/watcher.rs:248-269` + `src/App.svelte:201-208` |

### 崩溃面与资源

| # | 问题 | 位置 |
|---|---|---|
| M5 | read_text 在 inspect(判编码,读样本)与 fs::read(读全文)两次打开之间文件被外部截断时,decode_bytes 按 BOM 长度**固定切片 panic**(`&bytes[3..]`/`&bytes[2..]`);release `panic="abort"`=整应用崩溃。watcher reloadFile 恰把这条放进"文件正被写"的时间窗(本产品主用途=AI 会话持续写文件) | `src-tauri/src/file_inspect.rs:216-231` |
| M6 | run_git_capped 运行期不排空 stderr(排空线程在 try_wait 出结果后才 spawn):git 大量打 warning 时(损坏对象/失效 submodule)被管道背压卡住,本可成功的调用误报 10s 超时 | `src-tauri/src/git.rs:95-158` |
| M7 | PDF 渲染任务从不 cancel 且同页可并发重复渲染:renderTask 未保存;跳过判据 renderedScale 在渲染**完成后**才写,进行中的页被再次 renderPage(canvas+TextLayer 双份白干);缩放连打时逐页堆积。spec-011 R4 只核 canvas 释放(审计盲区) | `src/lib/components/Viewers/PdfViewer.svelte:228-271, 403` |
| M8 | PDF 搜索不可取消:大文件搜索中途切页签 → task.destroy() → getPage reject 落进全局 unhandledrejection 哨(污染冻窗疑案取证);连按 Enter 两轮循环交错写 matches | `src/lib/components/Viewers/PdfViewer.svelte:480-505` |
| M9 | 滚动后 300ms 内切页签,迟到的 scrollTimer 把已保存滚动位置覆盖(scroller 已 null → scrollPosition: undefined);后果=退化为当页顶部,页码/缩放仍正确(cleanup 时 persistState 用闭包活值) | `src/lib/components/Viewers/PdfViewer.svelte:122-141, 429-437` |

### 一致性与安全纵深

| # | 问题 | 位置 |
|---|---|---|
| M10 | gitStore 防抖合并漏了"在途"状态:fire() 在启动 fetch **之前** delete pending → fetch 在途时(大仓库秒级)新来的 refreshGitNow 拿不到 pending 开第二个并发 fetch;旧响应后落覆盖新状态,且 fetchInto 的分组校验基于旧数据可**误关正看着的 diff 视图**。触发=watcher 批次与手动↻/聚焦刷新交叠 | `src/lib/stores/gitStore.svelte.ts:151-174` |
| M11 | open_with_default_app 无可执行扩展围栏:resolve_target 只管路径在根内,open_path(ShellExecuteW) 对 .exe/.bat/.cmd/.lnk/.scr/.hta = **执行**,绕过信任门与 run.rs 白名单。0.7.6 刚删掉渲染层 opener open-path 授权(D10,威胁模型=渲染层被 pdf.js/CM 攻破),这条自定义命令把同一能力递了回来。前端菜单不给 exe 此入口,但命令对页面任意 JS 可调。spec-011 R18 只审了 run_project_executable(审计盲区)。注意 .msi 是 §126 明文走 System Default,修法须保留 | `src-tauri/src/handoff.rs:200-204` |
| M12 | 13 个同步命令仍带 IO/进程(0.7.6 async 化长尾):list_directory(展开树节点高频)、resolve_project(启动会话恢复逐项目,网络盘 SMB 超时×N)、save_state/load_state(JSON+fsync)、write_diagnostics、handoff 五命令(canonicalize+读 .url+ShellExecuteW 可秒级)、run 两命令。单次几十 ms 但都在原生主线程,与 L35 同机理 | `file_tree.rs:103` / `project/manager.rs:53-60` / `state/mod.rs:70-105` / `handoff.rs:159-231` / `run.rs:98-129` |
| M13 | CodeViewer 构建 effect 依赖过宽:①isDark() 读 settings.theme 在依赖内 → 切主题整建 EditorView,"不重建换主题"的 reconfigure effect 被架空;②cleanup 写回 tab.scrollPosition(自身依赖)诱发额外一轮重建;③theme="system" 时运行中切换系统深浅色无响应(matchMedia 无响应性) | `src/lib/components/Viewers/CodeViewer.svelte:62-111` |
| M14 | applyTabRenames 改名目标与既有页签撞名(依赖 L33 已知幻影 rename 残余/git checkout 式 del+add 配对):产生两个同 rel 页签 + 内容缓存互相覆写;applyTreeRenames 的 pin 映射同族 | `src/lib/stores/tabsStore.svelte:535-557` |
| M15 | NSIS 段未显式设定 webviewInstallMode,默认 downloadBootstrapper=装机时联网下 WebView2,离线机器装不上。R21 已拍 NSIS,实际打包是红线闸——打包前须过秤并显式定 installMode/webviewInstallMode | `src-tauri/tauri.conf.json` bundle 段 |

## 低(约 25 条,记账排队)

### Rust

| # | 问题 | 位置 |
|---|---|---|
| L-r1 | to_project_rel 在 path==scope 时 `path[scope.len()+1..]` 越界 panic(构造条件:项目根恰为父仓库 gitlink 条目,极难触达;panic=abort 下=崩溃) | `git.rs:368-378` |
| L-r2 | unquote 不识别 `\a\b\v\f` 与八进制 `\ooo` 转义:文件名含控制字符时 quotepath=false 仍 C-quote,还原出错名 → 树/面板显示错、diff pathspec 对不上 | `git.rs:341-363` |
| L-r3 | pathspec 未用字面量魔法:文件名含 `*`/`?`/`[` 时 git_diff/show 可纳入无关文件;修法 `:(literal)` 前缀 | `git.rs:719-733` |
| L-r4 | relaunch 用 std::process::exit(0) 绕过 RunEvent::Exit → 跳过退出状态落盘(丢最后防抖窗内变更,如刚开的页签);且注释声称 exit-then-start 实为 spawn-then-exit | `updater.rs:142-149` |
| L-r5 | cmd /K 载荷的 %VAR% 展开面未被 D11 探针覆盖(路径字面含成对 `%` 时理论上可破坏内层引号;前置条件极苛刻,记档) | `run.rs:55-57` |
| L-r6 | run_err_string 在 message 为空时固定返回 "git diff failed.",commit_detail 失败被误报 | `git.rs:866-874` |
| L-r7 | bat_host_outlives_script_body 测试直接 .arg() 单层引号,与产线 apply_args 路径分叉(新 ampersand 测试已走产线) | `run.rs:299-304` |

### 前端

| # | 问题 | 位置 |
|---|---|---|
| L-f1 | App 划词复制菜单未过视口钳制(0.6.3 同款"菜单被边缘裁掉"漏网);且 gitViewShowing 时 Ctrl+W 关的是不可见的文件页签而非眼前 diff | `App.svelte:315-326, 148-152` |
| L-f2 | GitPanel 的 `const now = $derived(Date.now())` 无响应式源,惰性求值一次永不失效——"5m ago" 长会话漂移失真 | `GitPanel.svelte:18` |
| L-f3 | 提交行 tooltip 的 `&#10;` 在表达式字符串里是字面六字符,不换行;应换 `\n` | `GitPanel.svelte:152` |
| L-f4 | 诊断 live-check 探 `.commit-detail`,CommitDetailView 根类名是 `.commit-view`——提交详情视图永远报 "(none)",冻窗疑案取证探针在该视图上指错方向 | `SettingsPanel.svelte:67-68` |
| L-f5 | forgetGit 不撤销待发防抖(timer)也不拦在途 fetch:移除项目 400ms 窗内 → 已移除项目的 git 快照复活并驻留到退出,违"关闭即释放"(两路独立发现) | `gitStore.svelte.ts:151-155, 186-190` |
| L-f6 | ImageViewer 工具栏(尺寸读数 span)缺 user-select:none——0.7.7"双击变蓝"在另一工具栏的同族残余 | `ImageViewer.svelte:83-135` |
| L-f7 | UnsupportedViewer 占位文案 "arrive in Phase 6" 已过时(Phase 6 已交付),成不实信息 | `UnsupportedViewer.svelte:36-38` |
| L-f8 | MarkdownViewer 本地图片解析的在途请求无取消(watcher reload 时旧回调仍写旧 img;重复 IPC,无视觉错误) | `MarkdownViewer.svelte:42-56` |
| L-f9 | 链式改名(同窗 a→b、b→c)首匹配落在中间态:页签迁到 b 而盘上已是 c → reloadFile 失败 → 活文件误标 deleted;renamedRel/mapPath 应迭代到不动点 | `watcherApply.ts:40-46` |
| L-f10 | 会话恢复不按 resolved rootPath 查重:手编 state/短名-junction 同根时得到两个同根项目,removeProject 一个会把另一个的树/页签/git 一起 forget | `sessionRestore.svelte.ts:69-85` |
| L-f11 | ensureContentLoaded 缺 executable 分支(自述"镜像 openFile 路由"不成立);当前唯一调用方在组件层先拦掉故无触发,第二个调用方出现即翻车。附带:超限文件被复用"已删除"语义 | `tabsStore.svelte.ts:593-599` |
| L-f12 | 注释漂移两处:shortcuts.ts 称加速键由 tauri.conf 禁用(实为 Rust COM,lessons L5);projectStore 称钳制 200–600(实际 appState 是 180 起,aria-valuemin=200 也不一致) | `shortcuts.ts:5-9` / `projectStore.svelte.ts:66-67` |
| L-f13 | 手编 state 的 pinnedItems 列表不去重,重复名渲染重复行(其余字段自愈都做了,独缺这个) | `appState.ts:247-253` |

### 配置与脚本

| # | 问题 | 位置 |
|---|---|---|
| L-c1 | md5 crate 2018 年后未维护(用途=体验渠道内容比对非签名);择机换 RustCrypto md-5 | `Cargo.toml:28` |
| L-c2 | CSP 未显式收紧 base-uri/form-action(两者不回落 default-src);纯纵深加固 | `tauri.conf.json` |
| L-c3 | install-experience.ps1:客户端运行中时 Copy-Item 中途抛错生硬,"请先关闭"提示在脚本尾部才出现,顺序反了 | `install-experience.ps1:22` |
| L-c4 | make-icon.py 硬编码 `C:\Windows\Fonts\msyh.ttc`,无该字体机器崩(dev 工具) | `make-icon.py:181` |
| L-c5 | swap-experience-client.py 路径插进 PS 单引号串(LOCALAPPDATA 含 ' 理论断串);staged 整读 exe 与 Rust 流式不一致(一次性脚本,无实害) | `swap-experience-client.py:45, 99` |
| L-c6 | tsconfig 未开 noUncheckedIndexedAccess 等可选收紧 | `tsconfig.json` |
| L-c7 | SettingsPanel 侧栏 5 个 input 继承 body user-select:none(L40 论断下双击选词被压,打字不受影响;旧账非 0.7.7 引入) | `SettingsPanel.svelte:109-175` |

依赖版本经 CVE 检索无已知命中:pdfjs-dist 6.3.289(未开 scripting)、markdown-it 15.0.2
(CVE-2025-7969 前置条件=自定义 highlight,不成立)、vite 8.3.1(dev-server 类 CVE 已修在其后)。

## 0.7.6/0.7.7 五笔修复复核(spec-011 §六)

| 修复 | 判定 | 备注 |
|---|---|---|
| git show 补 --no-ext-diff/--no-textconv | **修对** | 全仓 git 构建点核对(git.rs 单文件收敛)无漏带;--name-status 处属 belt-and-braces 无害 |
| cmd /K raw_arg 双层引号防注入 | **修对** | 全部 spawn 点核对(powershell -File/notepad/Code/git/explorer 均无 cmd 重析面);NTFS 禁 `"` 无歧义;残余=%VAR% 展开面(L-r5 记档) |
| opener 授权收紧 | **修对且面已最小** | 前端唯一调用=MarkdownViewer openUrl 且过 http/https 闸;但 M11 的自定义命令把能力部分递回(见中清单) |
| 六通道 async+spawn_blocking | **转对、无锁跨 await** | 同类面长尾=H2+M12;另 release panic=abort 下 JoinError 分支实际不可达(防御写法,非缺陷) |
| 0.7.7 button user-select:none | **修对** | 全仓无 textarea/select/contenteditable;侧栏 input 选词=L-c7 旧账;图片工具栏一处残余=L-f6 |

## 对 0.7.6 审计的四点补充(不推翻结论,印证"抽样≠全量")

1. R18 只审 run_project_executable,漏 open_with_default_app 旁路(M11);
2. R4 只核 canvas 释放,未覆盖渲染任务取消与重复调度(M7);
3. R14/R15 只核旗标,未核 merge 提交输出格式族(M2);
4. async 化只圈 git+四读通道,未对全部 30 个命令回头核对(H2/M12)。

## 建议处理顺序(等 owner 拍板)

1. **T3 全量基准之前修**:H2(check_update 污染启动测量)+ M7(重复渲染污染渲染档测量),
   顺带 H1/M1/M3(几行级用户可见修复)同批;
2. **随 0.7.8 修复批**:M2(Rust 一行)/M5(一行)/M4/M10/M11/M6/M8/M9/M13/M14;
3. **记账排队**:全部低级项;
4. **NSIS 打包前过秤**:M15(与红线闸同场)。
