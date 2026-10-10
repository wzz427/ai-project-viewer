# SPEC-INFRA-003 — 文本查看器统一操作栏(字号 + Find)+ MD 阅读列居中

> owner 2026-10-10 14:02 指令(复验截图反馈,两条):
> ①"MD 文档在最大化之后,右边还是冒出一个空白的区域";
> ②"除了 PDF 以外,其他的文档都缺少一个字体大小调节的按钮……统一放在一起,模仿 PDF 设置一个对文本区进行操作的'操作栏',不光能调节字体,还有一个 Find in Document"。
> owner 插队需求,沿用 INFRA 编号家族(非 Phase;spec-006 仍保留给 Phase 6 HANDOFF)。发版 **0.6.0**(0.5.0 已被图标段+缩进线段合用,此段独立起号)。

## 一、需求(R)与验证(V)

| R | 内容 | V |
|---|---|---|
| R1 | MD/代码/JSON 查看器顶部有一条与 PDF 同风格的统一操作栏:字号调节(A− / 当前px / A+)+ Find 输入框(命中计数 n/m + 上/下条导航) | V1:phase3-suite 新增 3 项——MD 工具栏字号点击后 `--viewer-font-size` 变化且持久(重开还原);MD Find 输入关键词出计数;代码查看器 Find 跳转选中 |
| R2 | Find 行为对齐 PDF 的"页导航级"先例(命中计数+跳转):代码查看器=CodeMirror 选中并滚到命中处;MD 渲染态=选中命中并滚到所在块 | V1 覆盖;V2-human:owner 复验手感 |
| R3 | Ctrl+F 统一聚焦当前查看器的 Find 框(含 PDF);无注册者时回退 CodeMirror 原生面板 | V2-human + 代码审查(dispatcher 单点改动) |
| R4 | MD 渲染态阅读列(860px 上限保留,可读性)在宽窗口**居中**,不再出现右侧大片空白 | V1:phase3-suite 断言 `.rendered` 左右留白差 ≤2px |
| R5 | 全局错误捕捉:window error/unhandledrejection 转 console.error(为上次未复现的"切换空白"留观察哨) | 代码审查;触发即出现在 CDP 控制台 |

## 二、决策表

| # | 决策 | 依据 |
|---|---|---|
| D1 | 字号按钮操作**全局** `settings.fontSize`(§22 既有设置,同 Settings 面板同一旋钮),非每文档独立 | "对文本区操作"最小心智;PDF 的每文档 zoom 是画布缩放、语义不同;零新增持久化状态 |
| D2 | 操作栏住共享组件 `ViewerToolbar.svelte`;**CodeViewer 自带**(JSON/MD-source 经嵌套自动获得);MD 渲染态自己挂一份;PDF 保持自己的富工具栏不动 | owner 说"模仿 PDF"=以 PDF 为样式范本,不改造 PDF |
| D3 | 代码 Find:一次全文扫描拿命中位置表(计数+跳转同源);MD 渲染态 Find:TreeWalker 扫文本节点,命中选中+滚动 | PDF 先例"页导航级"(spec-005 D5);字符级高亮装饰不做 |
| D4 | MD 右侧空白=860px 列不居中 → `margin:0 auto` 居中(不取消上限) | 上限是可读性设计(spec-003 视觉轮);空白感的根源是"不居中像排版事故" |
| D5 | Ctrl+F 经新的 activeFind 注册表(活动查看器 onMount 注册/卸载注销),空时回退 CM openSearchPanel | 与 codeSearchRegistry 同构;单一分发点 |
| D6 | 不在本批处理"切换空白"旧案 | owner 亲手复现+全程监测零异常=未复现;装 R5 观察哨后留观,再犯即留名 |

## 三、测试

phase3-suite 增 4 项(R1×2/R4/R5 之外的 resize 守卫):工具栏字号、MD Find、代码 Find、MD 居中;另加**"视口拉宽后跨类型切页签"守卫用例**(本轮 owner 报障的教训,防同类回归)。跑:vitest + svelte-check + phase3-suite + acceptance-r3;Rust 未动(cargo 随构建)。
