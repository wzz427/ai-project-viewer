# progress-2026-10 —— 建仓 → Phase 8 各轮蒸馏(2026-10-11 收口 spec-008 时整批回收)

> 来源:docs/handoff.md 2026-10-01 → 2026-10-11 已完结各轮(Phase 1–8 + INFRA 三件,版本 v6 → 0.6.13)。
> 每段只留"一句话结论 + 全文去哪":验收原话在 specs/INDEX.md 与各 SPEC §六;测试数字在 docs/testing.md §4;
> 教训在 docs/lessons.md;PDF 战史全文在 docs/pdf-guide.md。
> 内容冻结:进了只读不改(修断链除外)。

## 2026-10-01 · 建仓 + Phase 1 Application Shell(spec-001,Done)

- 需求 V1.1→V1.5 五轮评审定稿,V1.5 FINAL 为唯一基线;AGENTS/architecture/账本体系落位;Rust 工具链装好。
- Phase 1 交付:项目标签增删切去重(原生 Picker 全链自动化)/Files·Git·Settings 壳/主题/单实例/Ctrl+R 物理级拦截
  (WebView2 加速键 COM 禁用,L5);验收中补 Remove 入口+全局右键菜单两修。owner"继续下一个阶段开发"放行。

## 2026-10-01 · Phase 2 文件树/收藏置顶(spec-002,Done)

- Rust list_directory(§29 打标)+inspect_file(§101 流水线)→ 懒加载树+Pin+同父拖拽+Refresh rename 对账(1:1)。
- 两轮返修:拖到最顶(空白带不接 drop+dragenter 坑,L10)+排序合一/⋯ 并入 Settings(§30/§33 增量修订);
  测试从此零打扰(CDP 管道,owner 立规)。

## 2026-10-01 · Phase 3 Basic READ(spec-003,Done)

- File Tabs+MD/Code/JSON/Image/SVG 五查看器+五快捷键+大文件闸+删除态;固定页签模型(VS Code 预览制被 owner 否,当日改口)。
- 十项反馈返修两真根因:contentCache 非响应性(SvelteMap,L13)+图片路由顺序(L12);树高亮/页签右键/拖拽重排齐。

## 2026-10-01 · Phase 4 会话恢复+设置(spec-004,Done)

- 关掉重开一切还在:800ms 防抖+原子写盘+双兜底;state 损坏自愈;测试态永不在 owner 的 state 上读写。
- 基线对齐三件(D5/D6/D8);追加侧栏拖拽调宽(owner"要拖拽",D6 翻案留痕)。

## 2026-10-01→10-10 · Phase 5 PDF.js(spec-005,Done)+ INFRA-001 体验版/自更新(Done)

- PDF 全功能:工具栏十项/虚拟化/页导航搜索/状态恢复/关尾释放引擎;pdfjs 6 必须 legacy build(L14)。
- 体验版客户端(.exp 独立标识/目录)+自更新(md5 内容判定+rename 自替换+启动清理)——开发永远不碰 owner 正在用的程序。
- **划词六轮战史**(内核 155 升级+自驱选择层+锚点钉死)全文在 docs/pdf-guide.md,教训链 L17–L21;
  关窗=系统托盘(v9/v10,§16 修订);"切换空白"案 owner 亲手复现+CDP 监测零异常→不硬修,装全局错误哨兵(L23)。

## 2026-10-10 · INFRA-002 图标(0.5.0,Done)+ INFRA-003 统一操作栏(0.6.0/0.6.1,Done)

- 图标「项目检视」三处换新;显示缓存事故(L22)=重启 explorer+清 iconcache。操作栏=全局字号+Find 注册表(Ctrl+F)。
- 0.6.0 打回二轮:MD 铺满+操作栏同高(L24:断言必须对着 owner 原话写);**版本规则改 0.6.x 固定递增不跳段
  (SPEC-INFRA-003 D7,直到 owner 另有指令)**。

## 2026-10-10 · Phase 6 HANDOFF(spec-006,Done;0.6.2 首发+0.6.3–0.6.6 四轮返修)

- 右键移交:Edit in Notepad / Open in VS Code(探测三段,L25)/ Show in File Explorer / Open in Browser / 复制路径;
  三菜单分型(§135–141)+VS Code Mode 持久化;树/页签同源 handoffMenu 防漂。
- 返修轮:树高亮跟随激活页签+reveal 自动展开定位+菜单钳制(L26 测试隔离红线→aivlaunch 单一真源,只 PID);
  树不刷新真因=loadDir 缓存短路(0.6.4 重展开强制读盘)+发版覆盖 dev 二进制基建事故(L27 独立 target-exp);
  Refresh 迁侧栏头部 ↻ 图标(0.6.5)+点击旋转反馈(0.6.6)。owner"收口吧,我准备开新对话,做下一个需求"。

## 2026-10-10 · Phase 7 Git Review(spec-007,Done;0.6.7 首发+0.6.8 返修)

- Rust git_snapshot/git_diff(§65 git -C 基准+§70 安全旗标+§72 截断+10s 超时);徽标计数/树标记字母/单槽 DiffViewer/
  刷新四触发;隐藏窗口 timer 冻结→启动直取(L28)。
- 0.6.8 返修:面板照 VS Code 重排/Recent Commits 可点→提交详情钻取/并排 diff(纯解析 D16);修 56y ago。
- owner"这个需求通过了";打磨项(折叠条展开/行内高亮)记 spec-007 §四 D17 带去处。

## 2026-10-10→11 · Phase 8 RUN/Trust(spec-008,Done;0.6.9 首发+0.6.10–0.6.13 四轮返修)

- 项目信任门(§128/129 确认框+持久化/可撤销/不跨项目)+脚本可见控制台(四组对照实验定 cmd /K+powershell
  -NoExit+CREATE_NEW_CONSOLE,L29 release 构建/L30 Win11 终端宿主归因)+EXE 信息卡/Run(cwd=父目录)+msi 无 Run
  +菜单分型 menuKind+.url 协议白名单接线(销 Phase 6 遗留)。
- 返修轮:底部右键钳制守卫(0.6.10)/切回 Files 页签丢失(L31 覆盖视图寿命绑定面板)/树右键瞬态高亮+demo.exe 真夹具
  +信任文案(L32 $derived 先写后读)/Run 成功静默+失败居中 ErrorDialog+诊断导出能力(600 条日志环,为冻结 bug 取证)。
- **未结转出**:内容区冻结 bug(owner 客户端切页签内容不变,本机三路复刻未现)→ handoff 挂账,等诊断导出取证。
- owner"这期收口,进下一个需求,版本升到0.7"→ 版本段改 **0.7.x**(D7 逃逸条款"直到 owner 另有指令"首次使用),
  版本三处已升 0.7.0,Phase 9(Watcher)起用。
