# spec-001 · Application Shell(应用壳:窗口、项目标签、加/删项目、主题)

> 状态:Done —— 真值 = specs/INDEX.md。
> **追溯建档(2026-10-01)**:开发时(2026-10-01)specs/ 体系尚未建立,Phase 1 完成并验收后补此档。
> 需求源:V1.5 §175(Phase 1 批次);验收标准:V1.5 §188 对应块 + §192 完成清单 1–11。
> R/V 不在此重抄——本 SPEC 的需求与验证真值全在 V1.5 上述节;自测证据在 docs/testing.md §2。

## 实现记录(一句话级,详情住各自文档)

- 栈:Tauri 2.12 + Svelte 5(纯 Vite,剥掉模板 SvelteKit);工程结构 architecture.md §3。
- 交付:窗口壳、Single Instance、Project Tabs(Add/Remove/Dedup,含原生 Picker 全链)、Files/Git/Settings 三面板壳、Theme(system/light/dark)、P0 快捷键中央拦截框架(WebView2 加速键 COM 禁用,lessons L5)。
- 验收:2026-10-01 owner"继续下一个阶段开发"放行;验收反馈两件(Remove 入口、默认右键菜单)当日修复回归(ecb8a32)。
- Baseline:启动冷 992ms/温 88ms,进程树 Private 179MB(超 150 target,压缩手段挂 Phase 10)——数字与口径 docs/testing.md §3。

## 变更与验收记录

| 日期 | 跃迁/变更 | 产物 |
|---|---|---|
| 2026-10-01 | 追溯建档(直接 Done) | owner 放行原话见 handoff §一;自测清单 testing.md §2 |
