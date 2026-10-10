# scripts/e2e —— GUI 端到端回归(全量入库)

> 2026-10-10 owner 指令:测试脚本一律入库,禁止再依赖 `%TEMP%`。
> 完整规范见 **docs/testing.md**(§2 规程、§3 本清单);PDF 专属知识见 docs/pdf-guide.md。

## 跑法

- 解释器:**conda pywork**(`C:\Users\wzzpk\.conda\envs\pywork\python.exe`,Playwright/reportlab/pypdf/psutil 已装);
- 前置:release 构建已产出(`pnpm tauri build --no-bundle`);夹具=桌面 `AIV-TestProject`(PDF 夹具丢了用 `make-fixtures.py --force` 重建);
- 所有脚本**自带零打扰启动**(AIV_HIDDEN=1 → 窗口移屏幕外 -2500 保持渲染 → CDP 驱动),
  不抢鼠标、不弹窗、不碰真实 state(owner 2026-10-09 立规)。

## 清单

| 脚本 | 覆盖 | 何时跑 |
|---|---|---|
| `pdf-selection-battery.py` | PDF 文本选择全场景(V1–V8:正常拖/边距出界/按住空白上下移动[owner 反选原场景]/行首垫内起选/跨页/串台污染/宽屏右出界[Emulation 1536]/双击选词)。页面内派发事件驱动 | 凡动 PdfViewer/文本层/选择驱动 |
| `pdf-suite.py` | PDF 查看器功能 19 项:渲染/翻页/缩放/fit/搜索/虚拟化/释放/恢复/扫描件 | 凡动 PDF 相关 |
| `phase3-suite.py` | 查看器回归(MD/代码/JSON/图片/页签/编码/快捷键),自启动版 | 凡动查看器与页签 |
| `acceptance-r3.py` | 验收轮 8 项:更新按钮位置/MD 任务清单/右键 Copy/PDF 文本层 | UI 通用改动 |
| `real-input-battery.py` | 真实鼠标 8 手势电池(app+官方 oracle 双模式,前台守卫+事件到达验证) | **仅 owner 明确许可占用鼠标时**;日常禁用 |
| `make-fixtures.py` | 重建 PDF 夹具(10 页文本/100 页文本/100 页扫描 ~14MB/tab-1..5;`--target DIR --force`) | 夹具丢失/损坏时 |
| `oracle/oracle.html` | 官方 pdf.js 完整查看器驱动页(判定"我们的问题还是上游/内核") | 疑上游问题时 |

## oracle 搭建(一次性,约 2 分钟)

```
mkdir %TEMP%\aiv-oracle && cd scripts\e2e\oracle
copy oracle.html %TEMP%\aiv-oracle\
xcopy /E /I <仓库>\node_modules\pdfjs-dist\legacy %TEMP%\aiv-oracle\legacy
xcopy /E /I <仓库>\node_modules\pdfjs-dist\web     %TEMP%\aiv-oracle\web
copy %USERPROFILE%\Desktop\AIV-TestProject\pdf\sample-10p-text.pdf %TEMP%\aiv-oracle\
pywork python -m http.server 8899 --bind 127.0.0.1 --directory %TEMP%\aiv-oracle
:: 然后在被测 app 的 WebView 里打开 http://127.0.0.1:8899/oracle.html(CDP pg.goto)
```
(oracle 运行时依赖从 node_modules 现取,不入库,避免与 pdfjs-dist 版本漂移。)

## 新增场景的规矩

- 断言写进脚本自判 PASS/FAIL,不留人工判读;
- 场景来自 owner 的**原话手势**(窗口状态/出界方向/移动路径都要复刻,testing.md §2.3);
- 历史一次性诊断脚本(sweep/fight-log/max-repro/stepwise/probe 等)不入库,
  方法记录在 testing.md §4 与 lessons,需要时照配方重建。
