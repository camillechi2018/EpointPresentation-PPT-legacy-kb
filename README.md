# 企业 PPT 模板知识库 v0.11

本目录存放217个逐页原稿组件、24个补建组件、主题图库、SVG与图片素材、预览及对象登记。目录结构与 `catalog.json` 中的相对路径一致，未来可原样发布到受控文件服务器。

`brand-assets/` 收录用户提供的 6 款 Logo SVG 原件、对应的兼容 PNG，以及配置和素材清单。Skill 默认把 Logo 作为独立 PNG 图片对象添加到每页；素材库保留 SVG 原件供更换版本和重新生成。按需缓存可用 `fetch_library.py --brand-assets`。

- [文件清单](knowledge-manifest.json)：记录文件的 SHA-256、大小、241个组件所需文件及主题素材索引。
- [组件目录](catalog.json) 与 [主题图库](image-catalog.json)：供 Skill 先检索再按需获取。
- 主题图库的每张背景在 `image-catalog.json/backgrounds` 中保留唯一颜色与视觉标签：强调色系、强调色值与占比、明暗、调色板、视觉冲击力及复核状态。`theme-assets/background-colorway-index.json` 由这些主记录自动生成，不单独手工修改。当前68张背景的视觉分数由助手对照预览复核，状态仍为 `assistant_preview_reviewed_pending_user`，不是用户确认的正式评级。
- `layouts/<组件ID>/blank.pptx` 是生成用可编辑版；`example.pptx` 和大图总览只供识别版式。
- [独立 Skill](../epoint-presentation-v0.11/SKILL.md) 在同级目录，通过自身 `knowledge-base.json` 连接此库。

源模板和全部资产仍处于待评审状态。用户已明确允许将本知识库发布到公开 GitHub 仓库；公开可下载不代表品牌 VI、内容事实或素材使用范围已经获正式批准。本地目录与按需缓存流程已验证。

# SVG 颜色角色

`theme-assets/svg-role-bindings.json` 逐素材登记源 SVG 的颜色角色，供技能按主题生成 SVG 变体并同步替换 PPTX 的 PNG 回退图。映射由模板颜色归纳，仍需视觉复核；没有登记的素材不自动猜测换色。

# 扩充主题色系

新增背景先在 `image-catalog.json/backgrounds` 登记图片来源、角色、配套可编辑版式、颜色标签与视觉分数；运行 `python analysis/build_background_colorway_index.py` 重建索引，运行同脚本的 `--check` 校验。发布前更新 `knowledge-manifest.json` 中变更文件的 SHA-256 和大小，再提交到当前 Git 仓库。Skill 用目标主题色先找同色系背景，按视觉冲击力排序，中性背景仅作为后备；没有直接匹配时返回 `color_match_gap=true`。标签不会将原图换色，需要另行编辑原生结构、导出 SVG 变体或新增背景。

# 首批动效标注

`content-p175/p186/p195/p075/p147/p056/p078/p086` 八个组件的 `motion.json` 登记节点分组、形状 ID 和点击揭示顺序；`catalog.json` 的 `motion` 字段可定位标注，`knowledge-manifest.json` 将它们列入组件核心文件。Skill 在整套 PPTX 组装完成后读取标注并添加原生 PowerPoint 淡入效果。标注状态为助手结构复核、待放映验收；其他组件不自动加对象动画。添加新动效时先确认图形和文字的形状 ID、讲述顺序及是否在版式母版层，不能仅按字段后缀或坐标推断业务顺序。

# 第二批动效标注

新增 `content-p057/p063/p071/p105/p133/p134/p152/p153` 八个组件的 `motion.json`。曲线时间线按视觉从左到右、阶梯按从下到上、对比页按左右观点依次揭示；连接线、背景和对比中心标记保持静态。P063 的箭头端部形状与对应流程节点同一步出现，避免放映前出现孤立色块。第二批共 33 个点击步骤、158 个对象效果；已用 PowerPoint 导出视频逐页抽查，仍须在填入真实业务内容后核对讲述顺序。
