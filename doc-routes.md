# doc-routes —— 规矩在「动作发生那一刻」送达(AGENTS §四 防漂第二法)

> 建档 2026-11-05(L29 五度重演触发;AGENTS 原文:「想让某规矩在动作发生时自动送达 →
> 同一条规矩第二次被忘时建,先靠 AGENTS 表」)。**一行=一个触发动作→一条规矩全文或指针**;
> 规矩本体住它该住的文档,这里只挂指针,防止抄了就漂。

| 触发动作(我要开始…) | 到点送达的规矩 |
|---|---|
| 构建 GUI 测试二进制 / 跑任何 e2e 套件 / 发布体验版之前 | **必须 `pnpm tauri build --no-bundle`,绝不裸 `cargo build --release`**(lessons L29,五度重演;裸 cargo 缺 custom-protocol→页面 localhost 拒绝连接白屏,且会刷新 exe mtime 骗过 `_assert_fresh_build` 防闸;**症状=白屏/chrome-error/连接拒绝,先疑此条**) |
