# SPEC-020 · Markdown 数学公式与 Mermaid 图渲染

- **需求来源**: owner 2026-11-08 问「这个软件目前支持markdown数学公式和mermaid流程图渲染吗」
  → 现状核查=两者都不支持（markdown-it + task-lists + hljs，mermaid fence 落成纯代码文本）
  → owner 拍板：「都加。你写一个带数学公式和画图的md样例，做一下验证」。
- **范围**: MarkdownViewer 渲染态新增 (a) KaTeX 数学公式 (b) Mermaid 图。源码态、其他查看器不动。无新 UI（无按钮/无设置项——owner 规矩「所有操作必须有按钮」在此无涉：打开文件即自动渲染，不存在需入口的操作）。

## 二、技术方案

### D1 数学公式（静态接入，与 hljs 同先例）
- 插件 `@vscode/markdown-it-katex` 1.1.2（VS Code 内置 Markdown 预览同款），接进
  `createMarkdownRenderer()` 工厂链；`enableFencedBlocks:true`（```math 围栏一并支持）。
- 覆盖形态：行内 `$...$`、块级 `$$...$$`、```math 围栏；`\$` 转义；货币两 `$` 相邻
  不误判（插件按 VS Code 规则：开 `$` 后不许空格、闭 `$` 前不许空格）。
- katex 版本对齐 0.16.47 单份（插件与顶层共享；mermaid 自带的 0.18 嵌套在其懒加载
  chunk 内，与主包互不可见）。
- `katex/dist/katex.min.css` 随工厂模块 import；字体由 Vite 资产化，浏览器按需取。

### D2 Mermaid（懒加载，内存规则 V1.5 §6）
- 渲染期拦截：fence 渲染规则先于 hljs/katex 检查 info==`mermaid` → 产出
  `<div class="mermaid-block"><pre>转义源码</pre></div>` 占位（不进 hljs，自动探测不碰）。
- MarkdownViewer 后处理 pass：仅当文档真有 `.mermaid-block` 才 `await import("mermaid")`
  （12.x 独立 chunk），`mermaid.initialize({startOnLoad:false, securityLevel:"strict",
  theme:"default"})`（两套主题均为浅色）→ 逐块 `mermaid.render` → SVG 替换 innerHTML。
- 失败路径：解析抛错 → 块加 `mermaid-error` 样式、保留源码可读、清掉 mermaid 遗留的
  `#d<id>` 调试节点；不影响同文档其他块与其他内容。
- 竞态：effect 置 `live` 旗标（同 D3 图片 pass 先例 spec-012 L-f8），换文档后旧 promise
  写废弃 DOM 一律丢弃。

### D3 内存账（owner 2026-10-02 立规，交付必报）
- katex ~70KB(gz) 静态进主包——先例=hljs 19 语言静态；纯函数无运行时驻留。
- mermaid 引擎（MB 级）**首个含图文档才加载**；ESM 模块缓存不可卸载（与 PDF 关页签
  worker 归零机理不同），首次渲染后常驻 ~2–3MB 级——用 e2e 守卫固化「无图文档零加载」。
- 字体（katex woff2）浏览器按需取，不随包常驻。

### D4 安全（不弱化 §88 现状）
- `html:false` 不变：katex 输出由插件渲染器直出（trust:false 默认，无 `\href` 注入面）；
  mermaid fence 源码经 `md.utils.escapeHtml` 进 DOM；SVG 由 mermaid `securityLevel:"strict"`
  自有 sanitize 产出，`{@html}` 注入面不扩大。

## 三、样例与验收
- 样例：`scripts/e2e/fixtures/AIV-TestProject/docs/math-mermaid-demo.md`（生成器
  `make-fixtures.py` + 落盘双同步，本机无 reportlab 不能整树重建，沿 spec-018 先例）。
  内容覆盖：行内/块级公式、矩阵、aligned 多行、```math 围栏、`\$` 转义、货币不误判、
  flowchart/sequence/gantt 三类图、普通代码围栏回归。
- 守卫：
  - 单测（markdownRender.test.ts 增）：$…$ 出 katex 节点；`$50 … $70` 货币不出公式；
    ```mermaid fence → `div.mermaid-block` 占位且源码转义。
  - phase3-suite 增：打开样例 → `.katex`≥N、`.katex-display`≥1、`.mermaid-block svg`≥3；
    **懒加载断言**：先看纯文首档（README.md）时 `performance` 资源里无 mermaid chunk，
    打开样例后才出现。
  - 视觉验证（testing §2.3-6 铁律）：截图亲验公式排版与三类图形状。
- 发布：0.8.24 三处版本号，体验渠道常设授权发布。

## 四、不做
- 不做 mermaid 主题随 app 主题切换（仅两套浅色主题，`default` 一档够用）。
- 不做公式/图的手动刷新按钮（外部改动重读走 0.8.22 的 reloadOpenTabs 既有路径）。

## 五、施工记录(2026-11-08,0.8.24 已发)

- **方案变更:D1「katex 静态」→懒加载**。初稿按 hljs 先例静态接 katex;动手前用
  `node --expose-gc` 实测 katex 模块初始化即 ~2.67MB V8 常驻——跟 hljs(纯表驱动,
  零常驻)不是一类,按内存第一原则改为懒(D15)。mayContainMath 是廉价超集筛
  (含 `$` 即触发;货币文档会空拉一次引擎,输出仍正确,接受)。
- **首跑照出的实现 bug**:懒装插件只接进「新建」渲染器,首开公式文档的查看器实例
  建于加载前,chunk 拉了公式却不渲染——修=ensureMath 对在用实例补装(WeakSet 幂等)。
- **首跑照出的套件坑 ×2**(记 lessons L31):performance resource timing 默认 250 条
  缓冲区溢出静默丢条目(套件开机扩到 10000);playwright evaluate 带参函数忘传参
  恒 0 且「必须为 0」守卫空真(补「必须非 0」姊妹断言防自坏)。
- **视觉裁判 minor nit 不追**:错误块警示行用 --md-muted 偏淡,D14 有 --danger
  可用——0.8.24 已发版,为一条 cosmetic 重发不值当;下一版顺手换。
- 全档:check 0/0+vitest 159/159(+10)+phase3 PASS(+4)+freeze-guard 0/83+cargo 免跑;
  视觉×7 全过(公式排版/货币字面/三类图含 CJK 甘特/错误路径)。
