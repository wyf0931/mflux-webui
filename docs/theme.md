# 前端主题与组件约定

## 当前技术栈

页面由 Flask / Jinja 渲染，Alpine.js 管理交互，Tailwind CSS 4 负责布局，daisyUI 5 提供组件。
现有按钮、表单控件、卡片、标签、表格、导航及下拉菜单均沿用 daisyUI。
自定义代码集中在主题、页面布局和生成、上传、筛选等业务交互，没有另建基础组件库。
构建继续使用 Tailwind CLI 与 esbuild，暂不引入 Vite。

## 主题

主题定义集中在 `mflux_webui/static/css/input.css`，使用 daisyUI 的 `daisyui/theme` 插件。
`rausch` 是默认浅色主题，`rausch-dark` 是保持现有明暗切换能力的扩展。
主题选择保存在 `mflux.theme` 中，首次打开使用浅色，不随操作系统自动切到深色。

| 内容 | 浅色规范 |
| --- | --- |
| 主色 | `#ff385c` |
| 主按钮按下 | `#e00b41` |
| 主按钮禁用 | `#ffd1da` |
| 正文画布 | `#ffffff` |
| 导航与柔和表面 | `#f7f7f7` |
| 正文与标题 | `#222222` |
| 边框 | `#dddddd` |
| 错误 | `#c13515` |
| 控件圆角 | 8px |
| 卡片圆角 | 14px |
| 标签、筛选胶囊圆角 | 9999px |

参考提供的 Airbnb 设计规范；根据项目要求，顶部导航使用独立的柔灰底色，深色模式使用对应的表面色。
不使用 Luxe / Plus 子品牌配色，也不加载 Airbnb Cereal 等专有字体。
字体统一使用系统栈，中文回退包含 `PingFang SC`、`Hiragino Sans GB`、`Microsoft YaHei`、`Noto Sans CJK SC`。
无需访问 Google Fonts 或下载字体，中文和英文采用同一套字号与字重层级。

## 组件使用

- 使用 daisyUI 的 `btn`、`input`、`select`、`textarea`、`card`、`badge`、`navbar`、`tabs`、`dropdown`、`menu`、`table`、`alert`、`modal`。
- 使用 Tailwind 工具类组织页面布局，不引入第二套组件库。
- 主操作使用 `btn-primary`，导航及筛选使用中性样式，避免整页堆叠品牌色。
- 状态标签保持不换行、不可压缩。画廊操作在键盘聚焦时也应显示。
- 表单聚焦使用墨色边框，不使用彩色光晕。保留可见的键盘焦点，并尊重减少动画的系统偏好。
- 常规表面保持平面；浮层与图片卡片悬停共用一档阴影。
- 导航使用 `tab-active` 与 `aria-current="page"` 标记当前页；不要统一覆盖所有 tab 的下划线变量，否则未激活项也会出现下划线。
- 队列表格外层使用 `card`、1px 主题边框和 14px 圆角；小屏使用表格内横向滚动，避免页面整体溢出。
- 队列结果的“查看图片”与“查看日志”统一使用 `btn btn-link btn-sm` 文字按钮，不添加边框。
- 日志使用 daisyUI `modal` 与原生 `<dialog>`，完整内容放入可滚动、可换行的 `pre`。

## 桌面窗口布局（macOS）

桌面版通过 `<html data-desktop="true">` 与 Web 版区分，同一份模板在两处渲染：

| 项目 | Web 版 | 桌面版 |
| --- | --- | --- |
| 顶部导航 | 标签栏（`site-header`，80px） | 隐藏，改用左侧边栏 |
| 导航形态 | 顶部 tab + 手机端下拉菜单 | 188px source list 侧边栏，条目 30px，选中态为 11% 文字色底色 + 主色图标 |
| 页面标题 | 正文内 `28px` 的 `h1` | 工具栏固定显示应用名 `MFlux-GUI`（13px 半粗体，不随栏目变化）；正文标记 `data-page-heading` 的 `h1` 隐藏，其余 `h1` 收敛到 15px，当前栏目由侧边栏选中态表示 |
| 标题栏 | 浏览器标签 | 与系统标题栏合并：`titleBarStyle: Overlay` + `hiddenTitle`，交通灯位于 (18, 19)，工具栏左侧留 86px |
| 窗口拖动 | — | 工具栏与标题文字标记 `data-tauri-drag-region` |
| 滚动 | 页面整体滚动 | `body` 固定 100vh 且 `overflow: hidden`，只有 `main` 滚动 |
| 滚动条 | 浏览器默认 | 11px overlay 样式：透明轨道、3px 透明边框 + `content-box` 缩进拇指 |

窗口默认 1200×820，最小 960×640（侧边栏占 188px）。新增页面时：

- 页面级标题继续用 `<h1 class="text-[28px] font-semibold" data-page-heading>`，桌面版会自动隐藏并在工具栏显示导航名称；导航名称来自 `base.html` 的 `nav_items`。
- 不要把内容高度写成固定值，交给 `main` 滚动；横向溢出用页面内部容器包裹（表格加 `overflow-x-auto`），不要撑开窗口。
- 桌面专属样式统一写成 `[data-desktop="true"]` 前缀并放在 `@layer` 之外，确保能覆盖 Tailwind 工具类。

## 修改与验证

调整主题优先修改 daisyUI 变量；只有变量不能表达的品牌与交互样式才添加组件级覆盖。
组件级覆盖位于 Tailwind 的 `utilities` 层，避免被 daisyUI 的组件子层覆盖。
修改后运行 `npm run build`，检查生图、图生文、画廊、模型库和队列页面的浅色、深色及手机宽度；桌面布局改动还需要在打包后的应用里确认工具栏、侧边栏与滚动行为。
服务缓存 Jinja 模板时，需在生成队列空闲后重启服务才能看到模板变化。
