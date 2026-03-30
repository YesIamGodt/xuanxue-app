# 玄学互动平台 ✨

AI命理大师 · 热点命运联动 · 择机而行

## 核心功能

- 🔮 **命运水晶球** - 基于八字命理的AI专属运势解读
- 📰 **热点命运联动** - 自动分析今日热点与您命格的关联（首创功能！）
- ⏱ **预测未来** - 从玄学视角预测热点事件的明日走向
- ⚖️ **择机而行** - 根据命盘判断当前时机是否适合重大决策
- ☯ **双人合盘** - AI合盘分析两人命理契合度
- 💬 **占卜大师** - AI驱动的通灵命理对话
- 🔥 **每日热点** - 微博实时热点 + 个性化命理解读

## 技术栈

- **后端**: FastAPI + Python 3.12+
- **AI**: Anthropic Claude / OpenAI 兼容 API（火山引擎 MiniMax 等）
- **前端**: PWA（可安装到手机桌面）
- **部署**: Railway（一键部署，自动 HTTPS）

## 本地运行

```bash
pip install -r requirements.txt
cp .env.example .env   # 填入 AI API Key
python main.py
# 访问 http://localhost:8000
```

## Railway 部署（5分钟上线）

### 步骤 1：上传到 GitHub

代码已推送至：https://github.com/YesIamGodt/xuanxue-app

### 步骤 2：Railway 部署

1. 访问 https://railway.app 并登录（用 GitHub 账号）
2. 点击 **New Project** → **Deploy from GitHub repo**
3. 选择仓库：`YesIamGodt/xuanxue-app`
4. Railway 会自动检测 Python 并部署

### 步骤 3：设置环境变量

在 Railway 项目 Settings → Variables 中添加：

```
AI_PROVIDER=anthropic          # 或 openai / custom
ANTHROPIC_API_KEY=sk-ant-xxxxx  # 填入你的 Key
MAX_TOKENS=2048
TEMPERATURE=0.7
```

### 步骤 4：获取访问地址

部署完成后，Railway 会提供 HTTPS URL，如：
`https://xuanxue-app.up.railway.app`

### 步骤 5：安装到手机

在手机浏览器打开上述地址，点击浏览器菜单 → **"添加到主屏幕"**，即可像 App 一样使用！

## PWA 功能

- ✅ Service Worker 离线缓存
- ✅ App Icons（48~512px）
- ✅ Manifest 配置
- ✅ 安装提示条
- ✅ 全屏独立运行

## 环境变量说明

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `AI_PROVIDER` | AI 提供商：anthropic/openai/custom | anthropic |
| `ANTHROPIC_API_KEY` | Claude API Key | - |
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `CUSTOM_API_URL` | 自定义 API（火山引擎等） | - |
| `CUSTOM_API_KEY` | 自定义 API Key | - |
| `CUSTOM_MODEL` | 自定义模型名 | - |
| `MAX_TOKENS` | 最大 Token 数 | 2048 |
| `TEMPERATURE` | AI 温度参数 | 0.7 |

## 免责声明

本项目仅供娱乐使用。AI 命理分析仅供参考，请勿当真。
