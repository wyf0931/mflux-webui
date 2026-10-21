# 文档索引

[返回项目首页](../README.md)

项目文档按用途分为四类：上手使用、配置与数据、开发运维、设计记录。

项目首页提供两个语言版本：[README.md](../README.md)（英文，主版本）与 [README.zh-CN.md](../README.zh-CN.md)（中文镜像），包含项目定位、功能亮点、环境与推荐配置、依赖与许可证表。`docs/` 下的详细文档统一使用中文；代码标识符、命令、依赖名称与第三方 API 名称保留英文。

## 使用

| 文档 | 内容 |
| --- | --- |
| [使用指南](usage.md) | 文生图、图生图、Qwen 多参考图编辑、模型库、队列与任务日志 |
| [AI 描述](image-description.md) | 独立描述页的使用流程、前置条件、输出结构与接口 |
| [macOS 桌面版](desktop.md) | 安装、首次使用、独立数据目录、本机打包与发布 |

## 配置与数据

| 文档 | 内容 |
| --- | --- |
| [模型与配置](configuration.md) | 模型目录、Hugging Face / ModelScope 渠道、环境变量、数据位置 |
| [Qwen Image 2.1 Turbo 接入](qwen-image-21-turbo.md) | 固定依赖版本、多参考图编辑要求与兼容性排查 |

## 开发与运维

| 文档 | 内容 |
| --- | --- |
| [开发与运维](development.md) | 环境要求、安装构建、后台运行、自动化检查、项目结构 |
| [主题与组件约定](theme.md) | daisyUI 主题变量、系统字体、组件与交互规范 |
| [项目协作说明](../AGENTS.md) | 开发命令与代码协作要求 |

## 设计记录

按时间记录当时的方案与验证范围，用于回溯决策，可能与当前实现存在差异。

| 文档 | 内容 |
| --- | --- |
| [macOS 桌面版实施方案](design/desktop-plan.md) | Tauri 2 打包范围、技术选择与实施顺序 |
| [Qwen 多参考图编辑适配](design/qwen-reference-editing-plan.md) | 交互、数据与缓存隔离的适配方案 |
| [桌面版发布说明](desktop-release-notes.md) | 当前桌面版的变更摘要，随 Release 发布 |
| [设计规格](superpowers/specs/) | 各阶段功能的设计规格存档 |
