# FoldForge / 纸模工坊 初步开发文档 v0.1

## 1. 项目概述

### 1.1 项目名称

英文名：FoldForge
中文名：纸模工坊
Slogan：Turn imagination into printable paper models.
中文：把想象折成立体。

### 1.2 项目定位

FoldForge 是一款基于人工智能和计算几何技术的纸模型生成应用。它可以将用户上传的 3D 模型、图片或文字描述转换为可打印、可裁剪、可折叠、可粘接的纸模型套件。

传统纸模软件通常面向熟悉 3D 建模和展开图制作的用户，而 FoldForge 面向更广泛的人群，包括：

* 纸模玩家；
* 手作爱好者；
* 亲子教育用户；
* 游戏模型爱好者；
* 动漫 / IP 周边爱好者；
* 建筑模型爱好者；
* 教育机构；
* 创作者和设计师。

FoldForge 的核心目标不是简单地完成 3D 模型展开，而是帮助用户生成一套真正可以制作出来的纸模型方案。

---

## 2. 产品核心价值

### 2.1 一句话定义

把任何想象，变成一套可以打印、裁剪、折叠和粘接的纸模型。

### 2.2 核心差异

传统工具解决的是：

> 我有一个 3D 模型，请帮我展开。

FoldForge 解决的是：

> 我有一个想法，请帮我生成一套真的能做出来的纸模型。

### 2.3 核心能力

FoldForge 需要具备以下能力：

1. 3D 模型上传；
2. 模型自动清理；
3. 模型自动简化；
4. 高模转低模；
5. 曲面纸艺化；
6. 自动切缝；
7. 自动展开；
8. 自动生成粘贴边；
9. 自动生成山折 / 谷折线；
10. 自动编号；
11. 自动排版；
12. 自动生成 PDF / SVG / DXF；
13. 自动评估制作难度；
14. 自动生成组装说明书；
15. 后续支持文字生成纸模；
16. 后续支持图片生成纸模。

---

## 3. 目标用户

### 3.1 核心用户

#### 纸模玩家

他们希望将自己喜欢的角色、动物、建筑、道具、机器人、怪物等变成纸模型。

需求：

* 生成好看的纸模；
* 能打印；
* 能制作；
* 有编号；
* 有说明；
* 难度可控。

#### 亲子手工用户

他们希望给孩子制作简单、有趣、可打印的手工材料。

需求：

* 简单；
* 安全；
* 步骤清楚；
* 图案可爱；
* 可以涂色；
* A4 打印即可。

#### 游戏 / 动漫爱好者

他们希望把游戏中的角色、道具、怪物、建筑变成实体纸模。

需求：

* 风格化；
* 低多边形；
* 色彩明显；
* 可以收藏和分享。

#### 教育用户

他们可以用 FoldForge 制作几何、动物、历史建筑、科学模型。

需求：

* 可批量生成；
* 可黑白打印；
* 可课堂使用；
* 有说明文字；
* 支持低成本制作。

---

## 4. 产品形态

### 4.1 Web 应用优先

第一阶段优先开发 Web 应用，而不是桌面应用或移动应用。

原因：

1. 用户无需安装；
2. 上传、生成、下载流程简单；
3. 适合后续做社区和模板库；
4. 适合接入云端 AI 能力；
5. 适合商业化。

### 4.2 后续可扩展

后续可以扩展为：

* 桌面版；
* iPad 版；
* 移动端轻量版；
* Blender 插件；
* Cricut / Silhouette 裁切机插件；
* 纸模模板社区。

---

## 5. MVP 范围

### 5.1 MVP 只做什么

第一阶段只做：

> 上传 3D 模型 → 自动生成纸模展开图 → 下载 PDF / SVG。

MVP 支持：

1. 上传 OBJ / STL / GLB；
2. 3D 模型预览；
3. 模型基本信息显示；
4. 难度选择；
5. 纸张尺寸选择；
6. 成品高度设置；
7. 自动模型简化；
8. 自动展开；
9. 自动粘贴边；
10. 自动编号；
11. 自动排版；
12. SVG 预览；
13. PDF 下载；
14. 可制作性评分。

### 5.2 MVP 暂时不做什么

第一阶段暂时不做：

1. 复杂 AI 文生 3D；
2. 图片生成 3D；
3. 高质量纹理烘焙；
4. 复杂社区系统；
5. 付费系统；
6. 用户个人主页；
7. 移动端 App；
8. 裁切机深度适配；
9. 全自动高精度组装动画；
10. 大规模模型市场。

这些功能作为第二阶段和第三阶段开发。

---

## 6. 产品流程

### 6.1 MVP 用户流程

```txt
进入首页
  ↓
点击 Start Creating
  ↓
进入 Studio
  ↓
上传 3D 模型
  ↓
查看 3D 预览
  ↓
选择纸张、难度、尺寸、风格
  ↓
点击 Generate
  ↓
后端处理模型
  ↓
生成展开图
  ↓
查看 2D 预览
  ↓
查看可制作性评分
  ↓
下载 PDF / SVG
  ↓
打印、裁剪、折叠、粘接
```

### 6.2 后续 AI 用户流程

```txt
输入文字描述
  ↓
AI 生成低多边形 3D 模型
  ↓
用户选择风格和难度
  ↓
生成纸模展开图
  ↓
下载纸模套件
```

```txt
上传图片
  ↓
AI 识别主体
  ↓
生成纸艺风格 3D 模型
  ↓
自动展开
  ↓
生成 PDF / SVG / 说明书
```

---

## 7. 页面设计

### 7.1 首页

首页目标是让用户立刻理解产品。

核心文案：

```txt
AI Paper Model Studio

Turn any 3D model into a printable papercraft kit.

Upload a model, generate templates, print, cut, fold and build.
```

首页模块：

1. Hero 区；
2. 上传入口；
3. 三步流程；
4. 示例作品；
5. 功能介绍；
6. 使用场景；
7. CTA 按钮。

### 7.2 Studio 页面

Studio 是核心工作台。

布局建议：

```txt
┌─────────────────────────────────────────────┐
│ Top Bar: FoldForge / Project Name / Export  │
├──────────────┬────────────────┬─────────────┤
│ Left Panel   │ 3D Preview      │ Right Panel │
│ Upload       │ Model Canvas    │ 2D Unfold   │
│ Settings     │ Stats           │ Pages       │
│ Generate     │ Craftability    │ Downloads   │
├──────────────┴────────────────┴─────────────┤
│ Bottom Log / Processing Status              │
└─────────────────────────────────────────────┘
```

左侧面板：

* Upload Model；
* Paper Size；
* Difficulty；
* Style；
* Target Height；
* Add Tabs；
* Add Numbers；
* Add Fold Lines；
* Generate Button。

中间区域：

* 3D 模型预览；
* Orbit Controls；
* 模型统计；
* 可制作性评分。

右侧面板：

* 2D 展开图预览；
* 页面缩略图；
* Download PDF；
* Download SVG；
* Download ZIP。

底部：

* 处理状态；
* 错误日志；
* 生成进度。

---

## 8. 技术架构

### 8.1 总体架构

```txt
Frontend: Next.js / React / Three.js
        ↓
API Gateway: FastAPI
        ↓
Geometry Services:
  - Model Loader
  - Mesh Cleaner
  - Mesh Simplifier
  - Seam Generator
  - Unfolder
  - Tab Generator
  - Layout Engine
  - SVG Exporter
  - PDF Exporter
        ↓
Storage:
  - uploads
  - processed
  - exports
        ↓
Database:
  - projects
  - files
  - exports
  - settings
```

### 8.2 前端技术

推荐：

* Next.js；
* React；
* TypeScript；
* Tailwind CSS；
* shadcn/ui；
* Three.js；
* React Three Fiber；
* Zustand。

### 8.3 后端技术

推荐：

* Python；
* FastAPI；
* Pydantic；
* Trimesh；
* Open3D；
* NumPy；
* Shapely；
* svgwrite；
* reportlab；
* Blender headless。

### 8.4 存储

MVP：

* 本地文件夹：

  * storage/uploads；
  * storage/processed；
  * storage/exports。

后续：

* Cloudflare R2；
* AWS S3；
* Supabase Storage。

---

## 9. 核心后端模块

### 9.1 Model Loader

职责：

* 读取 OBJ / STL / GLB；
* 统一转换为内部 mesh；
* 提取顶点、面、边；
* 计算 bounding box；
* 计算模型尺寸；
* 识别 mesh 类型。

### 9.2 Mesh Cleaner

职责：

* 移除重复顶点；
* 修正法线；
* 合并相近点；
* 移除孤立面；
* 检测孔洞；
* 检测非流形边；
* 检测过小面。

### 9.3 Mesh Simplifier

职责：

* 根据难度降面；
* 保留大体轮廓；
* 合并细碎结构；
* 删除不可制作的小零件；
* 曲面低多边形化。

难度目标：

```txt
Easy: 50 - 150 faces
Standard: 150 - 500 faces
Advanced: 500 - 1500 faces
```

### 9.4 Seam Generator

职责：

* 选择切缝；
* 控制零件大小；
* 避免展开重叠；
* 控制粘贴边数量；
* 尽量把切缝放在不明显位置。

MVP 可以先使用简单规则：

1. 根据 face adjacency 构建图；
2. 根据法线夹角判断折线强度；
3. 优先在大角度处切开；
4. 控制每个 patch 的面数；
5. 生成多个 island。

### 9.5 Unfolder

职责：

* 将 3D patch 展开为 2D polygon；
* 保留边长；
* 标记相邻关系；
* 输出 2D pieces。

MVP 允许近似展开。后续需要加入：

* overlap detection；
* island splitting；
* energy minimization；
* UV-like unwrap；
* better packing。

### 9.6 Tab Generator

职责：

* 在边界边生成粘贴边；
* 控制 tab 宽度；
* 避免 tab 相互重叠；
* 给 tab 编号；
* 记录目标连接边。

### 9.7 Layout Engine

职责：

* 将展开 pieces 排版到 A4 / A3 / Letter 页面；
* 控制边距；
* 自动分页；
* 避免重叠；
* 保持可打印范围；
* 生成页面信息。

### 9.8 SVG Exporter

职责：

* 输出矢量线稿；
* 区分裁切线；
* 区分山折线；
* 区分谷折线；
* 添加编号；
* 添加页面边框；
* 添加标题信息。

### 9.9 PDF Exporter

职责：

* 将 SVG 转换为 PDF；
* 或直接生成 PDF；
* 支持多页；
* 支持打印尺寸；
* 保持比例准确。

### 9.10 Instruction Generator

MVP 阶段可以只生成简单说明。

后续加入 AI：

* 自动生成组装步骤；
* 每个步骤对应零件编号；
* 生成难点提示；
* 生成儿童版说明；
* 生成图文说明书。

---

## 10. 核心 API

### 10.1 Health

```http
GET /health
```

### 10.2 上传模型

```http
POST /api/upload-model
```

请求：

* multipart/form-data
* file

返回：

```json
{
  "projectId": "project_001",
  "status": "uploaded",
  "sourceFileUrl": "/storage/uploads/project_001/model.glb"
}
```

### 10.3 处理模型

```http
POST /api/process-model
```

请求：

```json
{
  "projectId": "project_001",
  "settings": {
    "paperSize": "A4",
    "difficulty": "standard",
    "style": "low_poly",
    "targetHeightMm": 200,
    "addTabs": true,
    "addNumbers": true,
    "addFoldLines": true,
    "addCutLines": true,
    "colorMode": "line_art"
  }
}
```

返回：

```json
{
  "projectId": "project_001",
  "status": "ready",
  "processedModelUrl": "/storage/processed/project_001/model.glb",
  "unfoldSvgUrl": "/storage/exports/project_001/template.svg",
  "unfoldPdfUrl": "/storage/exports/project_001/template.pdf",
  "stats": {
    "faces": 320,
    "pieces": 24,
    "pages": 5,
    "difficultyScore": 68
  },
  "warnings": [
    "Some pieces may be small for hand cutting.",
    "Try Easy mode if this is your first papercraft model."
  ]
}
```

### 10.4 获取项目

```http
GET /api/projects/{projectId}
```

### 10.5 下载文件

```http
GET /api/projects/{projectId}/export/pdf
GET /api/projects/{projectId}/export/svg
GET /api/projects/{projectId}/export/zip
```

---

## 11. 数据模型

### 11.1 Project

```ts
type Project = {
  id: string;
  name: string;
  sourceType: "upload_3d" | "text_to_3d" | "image_to_3d";
  sourceFileUrl?: string;
  processedModelUrl?: string;
  unfoldSvgUrl?: string;
  unfoldPdfUrl?: string;
  status: "created" | "uploaded" | "processing" | "ready" | "failed";
  settings: ProjectSettings;
  stats?: ProjectStats;
  warnings?: string[];
  createdAt: string;
  updatedAt: string;
};
```

### 11.2 ProjectSettings

```ts
type ProjectSettings = {
  paperSize: "A4" | "A3" | "Letter";
  difficulty: "easy" | "standard" | "advanced";
  style: "low_poly" | "cute" | "geometric";
  targetHeightMm: number;
  addTabs: boolean;
  addNumbers: boolean;
  addFoldLines: boolean;
  addCutLines: boolean;
  colorMode: "color" | "line_art";
};
```

### 11.3 ProjectStats

```ts
type ProjectStats = {
  originalFaces: number;
  processedFaces: number;
  pieces: number;
  pages: number;
  estimatedBuildTimeMinutes: number;
  difficultyScore: number;
};
```

---

## 12. 可制作性评分

### 12.1 评分目标

可制作性评分用于告诉用户：

* 这个模型适不适合做成纸模；
* 是否太复杂；
* 是否需要降低难度；
* 是否需要放大尺寸；
* 是否存在过细结构。

### 12.2 评分维度

1. 面数；
2. 零件数量；
3. 最小零件尺寸；
4. 粘贴边数量；
5. 页面数量；
6. 过细结构；
7. 非流形边；
8. 孔洞；
9. 展开重叠；
10. 预计制作时长。

### 12.3 评分结果

```json
{
  "score": 82,
  "level": "good",
  "estimatedBuildTimeMinutes": 90,
  "warnings": [
    "This model is suitable for standard papercraft.",
    "Use 160gsm paper for better stiffness."
  ]
}
```

等级：

```txt
0 - 39: difficult
40 - 59: risky
60 - 79: good
80 - 100: excellent
```

---

## 13. 导出格式

### 13.1 PDF

用于普通用户打印。

PDF 内容：

* 页面边框；
* 裁切线；
* 折线；
* 粘贴边；
* 编号；
* 标题；
* 比例信息；
* 推荐纸张；
* 页码。

### 13.2 SVG

用于高级用户和矢量编辑。

SVG 内容：

* 分层结构；
* cut layer；
* fold mountain layer；
* fold valley layer；
* tab layer；
* text layer；
* optional color layer。

### 13.3 DXF

后续支持，用于裁切机或激光切割机。

### 13.4 ZIP

包含：

```txt
project-name.zip
  template.pdf
  template.svg
  instructions.pdf
  preview.png
  model.glb
  README.txt
```

---

## 14. 开发阶段

### Phase 0：产品原型

目标：

* 明确产品定位；
* 画出页面结构；
* 确认 MVP；
* 搭建技术验证原型。

产出：

* 产品文档；
* 页面草图；
* 技术架构；
* 示例流程。

### Phase 1：MVP 闭环

目标：

完成最小可用产品。

功能：

* 上传 3D 模型；
* 3D 预览；
* 后端模型处理；
* 简单展开；
* SVG 输出；
* PDF 输出；
* 下载文件。

成功标准：

用户可以上传一个简单模型，比如低多边形兔子、盒子、机器人，然后下载 A4 展开图，打印后可以大致折叠成模型。

### Phase 2：纸模质量优化

目标：

提升“真的能做出来”的能力。

功能：

* 更好的 seam 选择；
* 更好的 island packing；
* 重叠检测；
* 粘贴边优化；
* 自动编号优化；
* 纸张厚度补偿；
* 更可靠的可制作性评分。

成功标准：

展开图更少重叠，更容易剪裁和粘接。

### Phase 3：AI 生成能力

目标：

让用户不需要自己上传 3D 模型。

功能：

* 文字生成低多边形模型；
* 图片生成纸艺风格模型；
* AI 自动简化模型；
* AI 自动生成组装说明；
* AI 自动生成标题和描述；
* AI 自动推荐难度。

成功标准：

用户输入“生成一个可爱的低多边形小狐狸纸模”，系统可以生成可打印模板。

### Phase 4：社区与商业化

目标：

从工具变成平台。

功能：

* 用户账号；
* 项目保存；
* 模板广场；
* 收藏；
* 分享；
* Remix；
* 创作者发布；
* 付费模板；
* 会员高级导出；
* 教育专题包。

---

## 15. 风险与难点

### 15.1 计算几何难点

难点：

* 任意 mesh 未必适合纸模；
* 高模展开后无法制作；
* 曲面会产生大量小面；
* 展开图可能重叠；
* 自动切缝质量影响制作体验；
* 粘贴边可能冲突；
* 复杂模型需要拆件。

应对：

* MVP 限制模型复杂度；
* 默认低多边形化；
* 提供 Easy / Standard / Advanced；
* 提供警告；
* 后续加入手动编辑 seam；
* 后续加入 AI 修复建议。

### 15.2 用户体验难点

难点：

* 用户不懂 3D 模型；
* 用户不知道什么模型适合纸模；
* 用户可能上传过于复杂的模型；
* 用户希望“一键生成”，但结果可能无法制作。

应对：

* 清晰的错误提示；
* 可制作性评分；
* 推荐参数；
* 示例模型；
* 新手模式；
* 自动降面；
* 自动尺寸建议。

### 15.3 AI 生成难点

难点：

* Text-to-3D 模型质量不稳定；
* 图片转 3D 可能不准确；
* 生成模型可能不适合纸模；
* 需要纸艺风格约束。

应对：

* AI 生成放到第二阶段；
* 第一阶段先做好 3D 上传展开；
* 后续只生成低多边形、纸艺友好的模型；
* 建立模型规范化流程。

---

## 16. 商业化方向

### 16.1 免费功能

* 上传简单模型；
* 低分辨率 PDF；
* 基础纸张尺寸；
* 少量项目保存。

### 16.2 付费功能

* 高清 PDF；
* SVG / DXF 导出；
* AI 文生纸模；
* 图片生纸模；
* 高级模型修复；
* 高级组装说明；
* 批量导出；
* 商用授权；
* 模板商店发布。

### 16.3 目标市场

* 纸模玩家；
* 亲子教育；
* 手工课程；
* 游戏玩家；
* 动漫周边；
* 建筑模型；
* 博物馆教育；
* 科普模型；
* 创作者经济。

---

## 17. 第一版推荐开发优先级

### P0：必须完成

* 项目初始化；
* 首页；
* Studio 页面；
* 模型上传；
* 3D 预览；
* 后端接收文件；
* 简单 mesh 加载；
* 简单展开 SVG；
* PDF 导出；
* 下载按钮。

### P1：重要

* 自动降面；
* 粘贴边；
* 编号；
* A4 排版；
* 可制作性评分；
* 处理进度；
* 错误提示。

### P2：增强

* ZIP 导出；
* 示例模型；
* 项目保存；
* 组装说明；
* 黑白 / 彩色切换；
* 页面缩略图。

### P3：后续

* Text-to-3D；
* Image-to-3D；
* 社区；
* 付费系统；
* 裁切机适配；
* AI 说明书。

---

## 18. MVP 成功标准

第一版不追求完美算法，但必须做到：

1. 用户可以上传一个简单 3D 模型；
2. 前端能看到 3D 预览；
3. 后端能处理模型；
4. 系统能生成 SVG 展开图；
5. 系统能生成 PDF；
6. 用户能下载打印；
7. 展开图包含裁切线、折线、粘贴边、编号；
8. 页面有基本美观度；
9. 代码结构清晰；
10. 后续可以继续接入更高级算法和 AI 能力。

最终，FoldForge 应该从一个简单的模型展开工具，逐步成长为一个 AI 纸模内容生成平台。
