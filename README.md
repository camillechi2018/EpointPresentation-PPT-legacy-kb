# 企业 PPT 模板知识库 v0.11

本目录存放217个逐页原稿组件、24个补建组件、主题图库、SVG与图片素材、预览及对象登记。目录结构与 `catalog.json` 中的相对路径一致，未来可原样发布到受控文件服务器。

`brand-assets/` 收录用户提供的 6 款 Logo SVG 原件、对应的兼容 PNG，以及配置和素材清单。Skill 默认把 Logo 作为独立 PNG 图片对象添加到每页；素材库保留 SVG 原件供更换版本和重新生成。按需缓存可用 `fetch_library.py --brand-assets`。

- [文件清单](knowledge-manifest.json)：记录文件的 SHA-256、大小、241个组件所需文件及主题素材索引。
- [组件目录](catalog.json) 与 [主题图库](image-catalog.json)：供 Skill 先检索再按需获取。
- `layouts/<组件ID>/blank.pptx` 是生成用可编辑版；`example.pptx` 和大图总览只供识别版式。
- [独立 Skill](../epoint-presentation-v0.11/SKILL.md) 在同级目录，通过自身 `knowledge-base.json` 连接此库。

源模板和全部资产仍处于待评审状态。用户已明确允许将本知识库发布到公开 GitHub 仓库；公开可下载不代表品牌 VI、内容事实或素材使用范围已经获正式批准。本地目录与按需缓存流程已验证。

# SVG 颜色角色

`theme-assets/svg-role-bindings.json` 逐素材登记源 SVG 的颜色角色，供技能按主题生成 SVG 变体并同步替换 PPTX 的 PNG 回退图。映射由模板颜色归纳，仍需视觉复核；没有登记的素材不自动猜测换色。
