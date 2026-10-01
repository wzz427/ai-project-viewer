# AI 编程项目管理指南(操作手册 v2)

> **这是什么**:给 agent 的建仓操作手册——在全新仓库里**需要哪些文档、一上来建哪些、
> 随着项目发展什么时候建哪些**,以及每份怎么写。提炼自真实长跑项目 TinkerCode
> (2026-05~09,近百份需求文档、3,000 条测试、多轮发版)。
>
> **v2 重写说明**:v1 失败于写成了"方法论综述"——agent 读完知道原则、不知道明天上午干什么,
> 还把源项目的终态当成了新项目的起点(比如没发版就建 changelog)。
> v2 全部按**项目阶段 × 文档工序**组织,原则压缩进主文档模板,正文只讲操作。

## 怎么用(三句话)

1. **开新仓库** → 先读 [`00-doc-map.md`](./00-doc-map.md)(全书地图:什么阶段建什么文档),
   再照 [`01-startup.md`](./01-startup.md) 把第一天的事做完。
2. **做需求** → 一切按 [`02-dev-workflow.md`](./02-dev-workflow.md) 走
   (总需求讨论 → spec + architecture → roadmap 拆解 → specs/ 逐个过)。
3. **要哪份文档的模板** → [`templates/`](./templates/) 里找,**文件名 = 它在新仓库里的名字**,
   00 总表里每份文档都点名了对应模板。

## 全书地图

| 文件 | 答什么问题 | 什么时候读 |
|---|---|---|
| [`00-doc-map.md`](./00-doc-map.md) | 项目全生命周期,每个阶段该有/该建哪些文档(**全书心脏**) | 第一个读,随时回来查 |
| [`01-startup.md`](./01-startup.md) | 第一天干什么:安全三件、开发环境记录、AGENTS.md、总需求讨论 → spec + architecture | 开仓时 |
| [`02-dev-workflow.md`](./02-dev-workflow.md) | 需求怎么管:roadmap 拆解、specs/ 逐个过、每个需求的三步曲、需求文档怎么写 | 每个需求开始前 |
| [`03-testing.md`](./03-testing.md) | 怎么验证:验证标准→测试用例、可视化验证、自测分级 | 写完代码要验证时 |
| [`04-doc-operations.md`](./04-doc-operations.md) | 日常文档怎么维护:四本账、同步表、路由表、怎么向 owner 汇报 | 每段工作收口时 |
| [`05-handoff-wrap.md`](./05-handoff-wrap.md) | 怎么交接:handoff/lessons/history 三者关系、/wrap 命令怎么建立怎么用 | 上下文将满时 / 归档时 |
| [`06-anti-entropy.md`](./06-anti-entropy.md) | 文档膨胀了怎么办(五条要则,一页) | 归档时、感觉文档开始烂时 |
| [`07-backup-secrets.md`](./07-backup-secrets.md) | 备份怎么建、密钥怎么管 | 第 0 天,然后每季度 |
| [`templates/`](./templates/) | 18 份即拷即用模板(AGENTS / workflow / spec / architecture / roadmap / SPEC / 四本账 / how-to-report / wrap…) | 按总表点名取用 |
