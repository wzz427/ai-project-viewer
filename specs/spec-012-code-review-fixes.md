# SPEC-012-code-review-fixes —— code review 查出的 44 个问题,全都修掉?(0.7.8 修复批)

> 状态:Draft —— **状态与"去处"的唯一真值 = INDEX.md 那一行**,本页不抄第二份。
> 创建:2026-10-11。Pre-Draft 出处:owner 原话"我想全部修复。你写一个针对code review的修复spec,
> 对所有问题提出修复方案";证据基线=【docs/code-review-2026-10-11.md】(全部条目位置/机理/触发
> 条件住那份报告,本 SPEC 按条目号指针化,不重抄——A5 精神)。

## 〇、值不值得做(两栏三出口,一行各一句)

- 好处:2 高(多行提交消息丢正文=每次多行 commit 可见;更新检查启动必冻主线程)·15 中(冻窗/崩溃/
  静默失效面)·25 低(文案/防御/注释漂移)——V1 收口前最后一道质量债清偿;评审已验证根因,修复确定性高。
- 代价:40+ 处改动跨约 25 文件,全档回归一轮+体验版一轮;风险=面广,但每条独立、有报告行号锚定,
  且不动架构(报告总体印象:无一条"结构烂")。
- 判:值→做(owner 已拍"全部修复")。

## 一、Pre-Draft 结论

- 核心选择题:范围=报告 44 条全量(M15 除外,见 D7)→ owner 原话拍板(上方引);
  其余选型见 §四决策表 D1–D8。
- 标杆对照:M2 对齐 VS Code——merge 提交详情默认 first-parent 视角。
- **界面确认**:N/A——修复批零新 UI(唯一文案改动=UnsupportedViewer 过时提示语换指路文案)。

## 二、需求正文(R 编号;使用者视角,组级+条目号指针)

> 通用反例规则(全组适用):**不新增产品功能;不顺手重构不在报告清单里的代码;每条修复必须能
> 对应报告条目号**(防范围漂移);零新增常驻(内存账,§四末)。穷尽性:报告 44 条即全集,
> 修复批无空态/首用维度,N/A。

| R# | 组 | 覆盖条目 | 需求(使用者视角) |
|---|---|---|---|
| R1 | 提交信息与 diff 正确性 | H1/M2/L-r2/L-r3/L-r6 | 多行提交消息完整显示且正文不再变成假文件;merge 提交点开能看到对第一父的并排 diff(不错位);文件名含控制字符/通配符时 diff 与文件列表仍正确;"提交详情失败"不再误报成"git diff failed" |
| R2 | 主线程卫生 | H2/M12 | 启动/点更新/展开树/切项目/保存状态/外部移交/运行脚本,任何路径都不再冻原生窗口(重活全数下线程池);无更新 staged 时更新检查不再白读当前 exe |
| R3 | watcher 与 git 刷新时序 | M4/M10/L-f5/L-f9 | 快速切项目后新项目的文件变化照常实时刷新;git 徽标/列表不被旧快照覆盖,正开着的 diff 不被误关;移除的项目状态真释放(不复活驻留);同窗链式改名页签跟到最终名(不误标已删除) |
| R4 | PDF 资源与搜索 | M7/M8/M9 | 缩放连打/滚动不再成倍白干渲染;搜索中途切页签不产生错误哨噪音,连按回车结果不交错;滚动后立刻切走,回来位置不退化为页顶 |
| R5 | 页签与会话状态一致性 | M1/M3/M13/M14/L-f10/L-f11/L-f13 | 重开已开的 PDF 从原位置继续;MD 切 Source 再回来滚动位置不丢、关页签不把位置清零;切主题代码查看器不整建、跟随系统深浅色即时生效;改名撞名不产生重复页签;恢复的状态不重复建项目;置顶列表无重复行 |
| R6 | 安全围栏补全 | M11/L-r1/L-c2 | "系统默认打开"对可执行类扩展一律拒绝并引导走 Run(信任门);.msi 保持 §126 明文放行;畸形 scope 不再可能 panic;CSP 显式收紧 base-uri/form-action |
| R7 | UI 文案与显示 | L-f1/L-f2/L-f3/L-f4/L-f6/L-f7/L-f12/L-c7 | 划词复制菜单不被窗口边缘裁掉;git 视图时 Ctrl+W 关的是眼前的 diff;相对时间不再永久失真;提交提示框正常换行;诊断 live-check 在提交详情视图报真值;图片工具栏双击不变蓝;不支持格式的提示不再说"Phase 6 会来";注释/aria 与实现一致;侧栏输入框双击可选词 |
| R8 | 工程与脚本卫生 | L-r4/L-r5/L-r7/L-c1/L-c3/L-c4/L-c5/L-c6/L-f8 | 更新重启不丢最后防抖窗内的状态;路径含 % 的脚本给出明确拒绝而不是理论注入面;宿主测试走产线引号路径;md5 依赖换维护版;装机脚本先提示后拷贝;图标脚本字体可回退;换装脚本路径插值安全;tsconfig 开索引访问收紧;MD 图片在途请求可取消 |

**反例规则(不许做什么)**:R6 不许把 .msi 一并禁掉(§126 明文);R4 不许为取消语义引入
新的常驻结构;R2 不许把命令转 async 后改变任何命令的返回语义(前端 invoke 契约不变)。

## 三、验证标准(V 编号;可判定)

| V# | 对应 R | 什么样算对(可判定) | 自动/人工 |
|---|---|---|---|
| V1 | R1 | cargo 新增:①多行消息夹具(正文含 TAB 行)→ Message 完整+文件列表无幻影条目;②merge 提交(真 git 造 merge)→ show 输出为 unified(first-parent)且前端 parseUnifiedDiff 全行对齐;③含控制字符文件名 unquote 还原正确;④pathspec :(literal) 下 `a*b.py` 只匹配自身;⑤commit_detail 失败文案含 "commit" | 自动 |
| V2 | R2 | 全仓 grep `#[tauri::command]`:同步 fn 且函数体含 fs::/Command/ShellExecute 的数量=0;cargo 新增 check_update 无 staged 时零读盘断言;既有 cargo/vitest 全绿 | 自动 |
| V3 | R3 | cargo 新增 watcher 代次测试(后完成的旧 start 自弃,槽=最后请求的 root);vitest renamedRel 链式改名到不动点;**watcher-freeze-guard 0/冻窗采样**(动 watcher 链必跑)+git-suite 全绿 | 自动 |
| V4 | R4 | pdf-suite 新增:①缩放连打 N 轮后渲染调用数≤页数×1(计数探针);②搜索中切页签→零 unhandledrejection(诊断环断言);③滚动后<300ms 切走再回来,scrollPosition 不为 undefined(e2e 探针) | 自动 |
| V5 | R5 | phase3 新增:重开已开 PDF(非激活→树双击)页码保持;MD Rendered→Source→切走→回来滚动位置=保存值;git-suite:视图切换/刷新不再误关 diff(构造并发刷新探针);vitest:pinnedItems 去重、链式改名 | 自动 |
| V6 | R6 | cargo 新增 open_with_default_app 拒绝表断言(exe/bat/cmd/lnk/scr/hta/jse/vbe/js/jar/com/pif 拒,msi 过,txt/pdf 过);to_project_rel(scope==path) 返回 "." 不 panic;tauri.conf 含 base-uri 'none' form-action 'none' | 自动 |
| V7 | R7 | phase3:image 工具栏双击 selection 为空(与 0.7.7 探针同款);复制菜单在视口底缘右键仍可点(clampMenu 复用断言);git 视图 Ctrl+W 后 gitViewShowing=false;其余=代码核对+截图 | 自动+V-human(截图) |
| V8 | R8 | 脚本 dry-run 过;cargo relaunch 前置 flush 断言(单测 perform 层);`pnpm check` 在 noUncheckedIndexedAccess 下 0 错(或触发 D6 止损线则记档) | 自动 |
| V9 | 全部 | 全档回归:phase3(≥67)+git 33+recent 15+r3 8+pdf 19+vitest(≥60)+cargo(≥99)+check 0/0+freeze-guard 0;发版 0.7.8 体验渠道 | 自动 |

## 四、技术实现方案

**修法逐条**(条目号→一行修法;位置/机理见报告):

- **G1(R1)**:H1=`%B` 后追加 `%x1e`,parse_commit_detail 以 `split_once('\u{1e}')` 切
  header/文件区(D5);M2=show_diff_argv 加 `--first-parent`(D2);L-r2=unquote 补
  `\a\b\v\f`+八进制字节级解析;L-r3=pathspec 前缀 `:(literal)`;L-r6=run_err_string 按
  调用方传语境词。
- **G2(R2)**:H2+M12 十五个命令(check/apply_update、list_directory、resolve_project、
  save/load_state、write_diagnostics、handoff 五命令、run 两命令)按既有 `*_inner` 模式机械转
  async+spawn_blocking;check_update 读 current 前先 `incoming.exists()` 短路。
- **G3(R3)**:M4=WatchSlot 旁存 `expected_root: Mutex<PathBuf>`,start 入口先记,blocking 完成
  时不一致即 drop 自己的 debouncer 返回 Ok(D3);M10=fetchInto 单飞(per-root 在途 promise
  复用,完成时若有新请求标记补一轮);L-f5=forgetGit 取 pending clearTimeout+delete+在途
  root 已遗忘即丢弃(与 M10 同处);L-f9=renamedRel/mapPath 迭代到不动点。
- **G4(R4)**:M7=renderPage 保存 RenderTask,重渲同页/释放先 cancel;pendingRenders Set
  in-flight 守卫(上界=可见页数);M8=searchGen 代次计数+循环每步检查+searching 重入拒绝;
  M9=unmount cleanup `clearTimeout(scrollTimer/anchorTimer)`。
- **G5(R5)**:M1=addOrActivate 保留清单加 `pdfState: existing.pdfState ?? tab.pdfState`;
  M3=MD 滚动保存/恢复挪进 `$effect`(依赖 markdownMode+container),cleanup 读活引用且
  非 rendered 分支跳过;M13=构建 effect 依赖收窄(scrollPosition 快照进局部量、isDark 用
  $derived 提升),reconfigure effect 补 matchMedia change 监听;M14=applyTabRenames 迁移前
  查 openFiles 是否已有 next,有则旧页签标 deleted 不迁缓存(pin 映射同理查重);L-f10=
  sessionRestore push 前按 resolved rootPath 查重;L-f11=ensureContentLoaded 开头补
  executable 早退;L-f13=parseProject pinnedItems 去重。
- **G6(R6)**:M11=open_with_default_app 加扩展拒绝表(D4),错误文案引导"右键 Run(需信任)";
  L-r1=to_project_rel 判 path==scope 返回 ".";L-c2=CSP 追加 `base-uri 'none'; form-action 'none'`。
- **G7(R7)**:L-f1=copyMenu 套 clampMenu+ctrl+w 先判 gitViewShowing;L-f2=删假 $derived,
  渲染处现算 Date.now();L-f3=`\n` 换 `&#10;`;L-f4=选择器改 `.commit-view`;L-f6=
  ImageViewer `.toolbar{user-select:none}`;L-f7=文案改"Use the tab context menu to hand
  off this file.";L-f12=两处注释对齐实现+aria-valuemin 对齐 180;L-c7=app.css 全局
  `input{user-select:text}`(与 0.7.7 button none 对偶)。
- **G8(R8)**:L-r4=relaunch 前同步调 state flush 再 exit+修正注释;L-r5=script 路径含 `%`
  时拒绝并提示改名;L-r7=bat_host 测试改走 apply_args;L-c1=md5→RustCrypto md-5;L-c3=
  install-experience.ps1 运行检测前置;L-c4=字体探测回退链;L-c5=路径插值转义+流式拷贝;
  L-c6=开 noUncheckedIndexedAccess(D6 止损线);L-f8=图片 effect cleanup 置 cancelled。

### 决策依据(后续翻案只翻这节)

| # | 结论 | 理由 | 当时排除了什么 | 为什么排除 |
|---|---|---|---|---|
| D1 | 一批全修、发 0.7.8 一版(内部按高→中→低顺序,每完成一组跑对应档) | owner"全部修复";44 条彼此独立、跨模块冲突面小 | 分两版 0.7.8/0.7.9 | 回归+发版双倍成本 |
| D2 | M2=Rust 侧 `--first-parent` 一行,前端 parser 不动 | VS Code 同款视角;combined 解析复杂度高收益低 | 前端支持 combined 格式 | 工作量高且仅 merge 提交受益 |
| D3 | M4=Rust 槽代次校验(完成时过期自弃) | 根因在后端完成乱序;后端修一处,前端 effect 不动 | 前端 effect 串行 await | 治标且拖慢切换、仍有 effect 重入窗口 |
| D4 | M11 拒绝表=exe/bat/cmd/lnk/scr/hta/jse/vbe/js/jar/com/pif,**msi 豁免** | 白名单住 Rust 的既有格局,镜像补黑名单;§126 明文 msi 走 System Default | 连 msi 一起拒 | 违 §126 |
| D5 | H1 用 `%x1e` 记录分隔符切 header | git format 的多行安全边界;启发式按行判状态字母会误伤正文首行恰好像状态的合法消息 | `[A-Z]\tp` 启发式 | 脆,假阳/假阴都构造得出 |
| D6 | L-c6 开 noUncheckedIndexedAccess,暴露错误>20 处则记档延后(止损线) | 收紧良性但暴露面未知 | 直接不开 / 无条件全清 | 前者治标不治本,后者可能吞掉本批主线 |
| D7 | M15(NSIS webviewInstallMode)本批不写值,挂 R21 打包轮 owner 三选一(embed/offline/bootstrapper) | 发版参数与 R21 同场;提前写死无验收场景 | 本批直接写 offlineInstaller | 越权代拍发版决策 |
| D8 | L-r4 relaunch 前同步 flush | 更新重启丢"刚开的页签"用户可感 | 保持现状仅修注释 | 状态丢失真实发生 |

**内存账(交付时报)**:零新增常驻——M10 单飞=复用在途 promise;M7 pendingRenders 上界=可见
页数(±2 窗口);M4 代次=既有槽旁一个 PathBuf;其余均为等量替换或防御分支。

## 五、测试覆盖矩阵(Draft→Ready 硬产物)

| R# | V# | 测法 | 所需夹具 | 状态 |
|---|---|---|---|---|
| R1 | V1 | cargo 新增 5 项(多行消息/merge first-parent/控制字符 unquote/literal pathspec/文案) | tmp 真 git 仓库(含 merge+多行消息+控制字符名文件) | ⚠(方案) |
| R2 | V2 | grep 全量核对+cargo 新增 1+既有全绿 | 无 | ⚠ |
| R3 | V3 | cargo watcher 代次+vitest 不动点+**freeze-guard 必跑**+git-suite | scripts/e2e 既有 | ⚠ |
| R4 | V4 | pdf-suite 新增 3 探针(渲染计数/零 unhandledrejection/scrollPosition 保真) | PDF 夹具 | ⚠ |
| R5 | V5 | phase3 新增 3+git-suite 并发探针+vitest 2 | AIV-TestProject | ⚠ |
| R6 | V6 | cargo 拒绝表+scope==path+conf 核对 | 无 | ⚠ |
| R7 | V7 | phase3 3 探针+截图自查(V-human) | AIV-TestProject | ⚠ |
| R8 | V8 | 脚本 dry-run+cargo flush 断言+check | 无 | ⚠ |
| 全部 | V9 | 全档回归+发版 0.7.8 | 全部 | ⚠ |

## 六、变更与验收记录

| 日期 | 跃迁/变更 | 产物 |
|---|---|---|
| 2026-10-11 | 立项 Draft(owner"我想全部修复。你写一个针对code review的修复spec") | 本文档+测试矩阵 9 行 |
