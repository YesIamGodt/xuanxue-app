# 日常AI服务 ✨

一套实用的日常AI服务应用，包含Web版本和Flutter跨平台APP版本！

## 功能特性

- 📕 **小红书文案生成器** - 一键生成吸引人的小红书风格文案
- 💬 **智能回怼助手** - 高情商回怼话术，让你再也不怕尴尬场景
- 🔮 **AI算命** - 趣味命理解读，娱乐至上

## 项目结构

```
daily-ai-services/          # Web版本和后端API
daily-ai-services-flutter/  # Flutter APP版本（iOS/Android）
```

## 快速开始 - Web版本

### 1. 安装依赖

```bash
cd daily-ai-services
pip install -r requirements.txt
```

### 2. 配置环境变量

```bash
cp .env.example .env
# 编辑.env文件，填入你的Anthropic API密钥
```

### 3. 启动服务

```bash
python -m uvicorn main:app --reload
```

### 4. 访问应用

打开浏览器访问：http://localhost:8000

## 快速开始 - Flutter APP版本

### 1. 安装Flutter

首先需要安装Flutter SDK：https://flutter.dev/docs/get-started/install

### 2. 安装依赖

```bash
cd daily-ai-services-flutter
flutter pub get
```

### 3. 配置环境变量

```bash
cp assets/.env.example assets/.env
# 编辑assets/.env文件，配置API地址
```

**注意**：Flutter APP需要先启动后端API服务！

### 4. 运行APP

```bash
# Android
flutter run

# iOS (需要Mac)
flutter run -d ios
```

## 技术栈

### Web版本
- **后端**: FastAPI + Python 3.12+
- **AI**: Anthropic Claude API
- **前端**: 原生 HTML/CSS/JavaScript

### Flutter APP版本
- **框架**: Flutter 3.x
- **语言**: Dart
- **支持平台**: iOS、Android

## 赚钱思路

### 1. 免费增值模式 (Freemium) 🔥推荐
- **基础版**: 每个功能每天免费使用3次
- **会员版**: ¥9.9/月 无限使用，优先响应，更多高级选项

### 2. 按次付费
- 每次使用0.1-0.5元
- 适合低频用户

### 3. API服务
- 提供RESTful API
- ¥0.1-0.5/次调用
- 批量购买优惠

### 4. 定制服务
- 为企业或个人定制专属的AI工具
- 一次性开发费 ¥5000-50000
- 年维护费 15-20%

## 扩展功能建议

- 添加更多AI服务（如：情书生成、检讨书、祝福语等）
- 用户系统和历史记录
- 分享功能，一键分享到社交平台
- 支持自定义Prompt模板
- 图片生成能力（集成DALL-E、Midjourney等）

## 免责声明

本项目仅供学习和娱乐使用。AI算命功能纯属娱乐，请勿当真。使用本项目产生的任何后果由使用者自行承担。
