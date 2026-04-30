# 📸 智能相册清理器（Smart Photo Cleaner）

利用 AI 自动识别并清理相册中的截图和模糊照片，帮助你快速释放存储空间。基于 Streamlit 构建，调用 Novita AI 的多模态视觉模型进行智能分类。

## ✨ 功能特点

- 📤 **批量上传**：支持 jpg、jpeg、png 格式图片。
- 🤖 **AI 智能分析**：调用 `qwen3-vl-8b-instruct` 模型，自动判断每张图片属于「截图」「模糊」还是「正常」。
- 🗑️ **一键清理**：可一键删除所有被判定为截图或模糊的图片，或将单张图片移入回收站。
- ♻️ **回收站机制**：删除的图片暂存于 `deleted/` 目录，支持清空回收站。
- 🎨 **美观界面**：七彩渐变首页 + 彩虹 loading 动画，操作直观。

## 🛠️ 技术栈

| 类别         | 使用技术                                 |
| ------------ | ---------------------------------------- |
| 前端/界面    | Streamlit                                |
| 后端服务     | Python 3.8+                              |
| AI 推理 API  | Novita AI（`qwen3-vl-8b-instruct`）      |
| 图像处理     | base64 + 本地文件存储                    |
| 依赖库       | requests, streamlit, numpy, pillow (间接) |

## 📦 安装与运行

### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/smart-photo-cleaner.git
cd smart-photo-cleaner
