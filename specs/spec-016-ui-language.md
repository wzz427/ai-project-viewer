# spec-016 界面语言切换 —— English / 简体中文

> owner 2026-10-26 增量需求原话:「要把现在的软件再做一个中文版。可以在软件设置里加一个语言选项,
> 支持切换英文和中文,默认是英文,翻译一个中文版出来。翻译完之后,把安装包也同步升级一下」。
> 对齐记录:范围+默认六条(owner 选「按方案开工」)——切换即时不重启/记住选择;翻整个界面不含文件内容;
> 后端报错翻主要路径;软件名保留;离线大包同步重打;版本 0.8.14。

## §一 范围

- 翻译面:侧栏两页签/文件树与页签右键菜单/设置面板/查看器工具栏/错误与属性弹窗/提示气泡/欢迎页/
  托盘右键菜单/时间显示("2h ago"→"2 小时前")/大文件确认与信任门对话。
- 不翻:用户文件内容(用户数据);软件名 "AI Project Viewer";Git/VS Code 等产品名;诊断导出报告(开发侧产物)。
- 后端报错:前端按已知文案**前缀/精确映射**翻译(rustErrors.ts,30 条),未知串原样透传(英文优于空白);
  带插值的报错翻固定前缀、动态尾巴(路径/OS 错误文本)保留。

## §二 关键决策

| # | 决策 | 理由/否决项 |
|---|---|---|
| D1 | locale 真值住 settingsStore($state),经 appState.settings.locale 持久化(可选字段,旧状态文件自愈 en) | 与 theme 同模式;选完即时生效=组件模板里 t() 读 $state 天然响应,零重挂 |
| D2 | 字典纯模块 dict.ts(en/zh 双 Record,I18nKey 类型锁键位对齐)+ 薄响应层 t.svelte.ts(t/tf/rt/relTime) | 字典可在纯 vitest 里测(键位对齐/非空/插值);响应层薄到不可能错 |
| D3 | 后端报错不穿 locale 进 Rust,前端展示期映射 | 给每条 Rust 命令传 locale=面大易漏;映射表带**源锚点守卫**(vitest grep Rust 源码,文案改词即红)封漂移 |
| D4 | 托盘菜单(Rust 建)按 set_tray_language 命令原地重建,条目 id 稳定 | 切换即时;事件处理器复用;启动时 initTheme 阶段恢复 zh 用户同步重建 |
| D5 | 中文字体:--font-ui 显式补 "Microsoft YaHei UI"/"Microsoft YaHei" | 不依赖系统静默回退,混排一致 |
| D6 | 语言名各自原文显示(English / 简体中文) | 惯例:用户永远找得到自己的语言 |
| D7 | 翻译顺手清理:Settings 尾部过时备注 "Git settings arrive with their feature (Phase 7)" 删除(Git 已上线,过时承诺) | 用户可见的错误信息不上秤 |

## §三 实现

- `src/lib/i18n/dict.ts`(en/zh ~210 键)、`t.svelte.ts`(t/tf/rt/relTime)、`rustErrors.ts`(30 条映射+锚点)。
- 31 组件+菜单工厂 handoffMenu.ts+3 store(tabs/project/watcher)全部换 t()/tf();gitFormat.relativeTime 委托字典(en 默认,既有单测不动)。
- Rust:tray_labels(单一来源)+ set_tray_language 命令;cargo 132/132(+1 tray_labels_follow_locale)。
- e2e 守卫(phase3 +4):header 翻转/右键菜单翻转/状态文件持久化 zh/切回 en 稳态。
- 安装包:重打 NSIS 离线大包入 仓库`离线安装包/`(两语言一个包,装机后自选)。

## §四 状态

- InTest(2026-10-26):0.8.14 已发体验渠道待 owner 验收;安装包已重打。
- 验收路径=owner Update→重启→Settings→Language→简体中文:①整个界面变中文;②右键文件菜单中文;
  ③重启后仍是中文;④切回 English 立即回。术语译法不满意随时报,改词分钟级。
