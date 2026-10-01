# spec-001 · Application Shell(应用壳:窗口、项目标签、加/删项目、主题)

> 状态:Done —— 真值 = specs/INDEX.md。
> 创建:2026-10-01 **追溯建档**(开发时 specs/ 体系尚未建立,Phase 1 完成、owner 放行后补档;同日应 owner 要求补全为完整 SPEC 形态)。
> 需求源:V1.5 §175(Phase 1 批次);完成判据:V1.5 §192 清单 1–11 + 13(停止)。
> 写法同 spec-002:R 行挂 V1.5 节号指针,不重抄正文(workflow §五 A5)。

## 〇、值不值得做

- Phase 1 是 V1.5 §175–182 排期定死的第一批,"值不值"已在需求定稿时判过;判:做(V1 一切的地基)。

## 一、Pre-Draft 结论

- 追溯说明:本 Phase 开发前无 Pre-Draft 讨论记录;方案依据 = V1.5 §192 第一条开发指令 + 建仓会话(2026-10-01)。
- 核心取舍当时已由 V1.5 定死:Tauri 2 + Svelte(§154–§158 技术栈),无需选择题。

## 二、需求正文(R 编号;指针到 V1.5 §175)

| R# | 需求提要 | V1.5 依据 |
|---|---|---|
| R1 | 应用编译通过、能启动(Tauri 2 + Svelte 壳) | §175 技术栈;§192-1/2 |
| R2 | Single Instance:二次启动不新开窗,唤起已有窗口后自己退出 | §175;§16 |
| R3 | Project Tabs:多项目标签,可切换 | §175 |
| R4 | Add Project:从原生目录选择器添加项目 | §13 §175 |
| R5 | Remove Project:确认后从标签移除,磁盘项目不动 | §15 §175 |
| R6 | Project Dedup:同一根路径(尾斜杠/大小写/短名归一)不重复开 | §14 §175 |
| R7 | Sidebar Header:Files / Git / Settings 三入口(壳) | §175;§129 附近 |
| R8 | Settings 仅 Theme(占位页,system/light/dark) | §175;§24 |
| R9 | 应用级快捷键与 WebView2 加速键冲突的基础框架(P0 组合中央拦截,不误发浏览器行为) | §175;§146–§147 |
| R10 | Baseline Benchmark:启动时间(冷/温)、进程树 RAM、空闲 CPU、WebView2 进程数 | §175;§162–§166 |

**反例规则**:不实现 Phase 2+ 功能;不使用大量 TODO 假装完成;未实际运行不得宣称完成(§192"不得"块原文)。

## 三、验证标准(V 编号;= V1.5 §192 完成清单,证据在 testing.md §2)

| V# | 对应 R | 什么样算对 | 自动/人工 |
|---|---|---|---|
| V1 | R1 | cargo check 0 错 0 警;release 构建成功;应用实际启动出窗口 | 自动 |
| V2 | R2 | 二次启动进程退出码 0,活进程数 1,原窗口被唤起置前 | 自动 |
| V3 | R3 R4 R5 R6 | 标签增/删/切换全链:原生 Picker 选目录→添加;同根异写(小写/尾斜杠)再选→去重并切换;右键 Remove→确认→标签消失、磁盘完好 | 自动(UIA+CDP 全链) |
| V4 | R7 R8 | 三面板切换正常;Theme 三态生效且 system 跟随系统 | 自动(CDP) |
| V5 | R9 | 物理按 Ctrl+R:页面不刷新,拦截计数+1,toast 反馈;Ctrl+F/Ctrl+W/Ctrl+Tab 同框架就位 | 自动(物理键注入) |
| V6 | R10 | 四项 Baseline 数字落档:冷启动 ms/温启动 ms/进程树 Private MB/空闲 CPU%/WebView2 进程数 | 自动(脚本) |

## 四、技术实现方案(已交付;结构真值 = architecture.md §3 代码地图)

- Rust:`src-tauri/src/lib.rs` 装配(single-instance 插件置首:唤起+聚焦;dialog 插件;setup 内 COM 禁用 WebView2 加速键——Tauri 2 无 `browserAcceleratorKeys` 配置,走 `ICoreWebView2Settings3::SetAreBrowserAcceleratorKeysEnabled`,依赖版本对齐 wry,lessons L5);`project/manager.rs` `resolve_root`(dunce canonicalize 归一去重,拒盘根/非目录)+ `resolve_project` command,8 个单测。
- 前端:Svelte 5 runes + 纯 Vite(剥掉模板 SvelteKit,单窗口无路由);ProjectTabs / FilesPanel / ProjectContextMenu(共享右键菜单)/ Settings(Theme);`stores/projectStore`(内存态 tabs/activeId,addProjectViaPicker 带 catch)/ settingsStore / diagnosticsStore / toastStore;`services/shortcuts.ts` P0 五组合中央 dispatcher(capture 拦截+e.repeat 防连发+拦截计数)。
- 配置:`tauri.conf.json` 窗口 1280×800/min 960×600/CSP/NSIS bundle;桌面快捷方式指向 release exe(重建自动最新,验收入口)。

### 决策依据

状态只住一处:**结论与理由 = architecture.md §1 决策表(D1–D9)**,此处不重抄;翻案翻那份表。

## 五、测试覆盖矩阵(实际执行记录,证据 testing.md §2)

| R# | V# | 测法 | 夹具 | 状态 |
|---|---|---|---|---|
| R1 | V1 | cargo check/test(8/8)+ svelte-check(0/0)+ 实际启动截图 | — | ✓ |
| R2 | V2 | 双启进程探测 | — | ✓ |
| R3–R6 | V3 | CDP + UIA 驱动原生 Picker/确认框(方法 testing.md §1,lessons L6–L8) | aiv-test-projects Alpha/Beta | ✓ |
| R7 R8 | V4 | CDP 断言 + 截图 | — | ✓ |
| R9 | V5 | 物理键盘注入 + 拦截计数 | — | ✓ |
| R10 | V6 | 进程树/计数脚本(口径 §161:Private Memory) | — | ✓(RAM 179MB 超 150 target,压缩挂 Phase 10) |

## 六、变更与验收记录

| 日期 | 跃迁/变更 | 产物 |
|---|---|---|
| 2026-10-01 | 交付 + InTest | §192 清单 1–11 全过(testing.md §2);Baseline 落档 |
| 2026-10-01 | 验收反馈修复 ×2 | ① Remove 入口补到 Files 面板路径右键(共享 ProjectContextMenu);② 全局禁用 WebView 默认右键菜单;release 重建+回归(ecb8a32) |
| 2026-10-01 | InTest → Done | **owner 验收原话:"继续下一个阶段开发"**(按验收放行处理) |
| 2026-10-01 | 追溯建档 → 补全完整形态 | 应 owner 要求补 R/V/方案/矩阵(owner:"Spec 001 也得补上") |
