# 玄学互动 - 阿里云部署指南

## 方式一：ECS 实例部署（推荐，稳定）

### 第一步：购买阿里云 ECS
1. 访问 https://www.aliyun.com 注册/登录
2. 进入 ECS 控制台 → 创建实例
3. 选择配置（最低配置即可）：
   - 地域：**华北2（北京）或华东1（杭州）**（国内访问快）
   - 实例规格：ecs.s6-c1m1.small（最便宜，约20元/月）
   - 镜像：Ubuntu 22.04 或 CentOS 8
   - 带宽：按量付费，最小 1Mbps
   - 安全组：开放端口 **8000, 22**

### 第二步：登录 ECS 并执行部署
```bash
# 登录 ECS（用阿里云控制台的"VNC远程连接"或本地SSH）
ssh root@你的ECS公网IP

# 在 ECS 上执行以下命令：
apt update && apt install -y docker.io docker-compose python3 python3-pip git

# 克隆代码
git clone https://github.com/YesIamGodt/xuanxue-app.git
cd xuanxue-app

# 设置环境变量（在 /root/xuanxue-app/.env 文件中写入）
cat > .env << 'EOF'
AI_PROVIDER=anthropic
ANTHROPIC_API_KEY=sk-ant-your-key-here
MAX_TOKENS=2048
TEMPERATURE=0.7
EOF

# 构建并启动
docker build -t xuanxue-app .
docker run -d --name xuanxue -p 8000:8000 --restart always \
  -v $(pwd)/.env:/app/.env xuanxue-app

# 测试
curl http://localhost:8000/api/date

# 配置域名（可选，使用 nginx 反向代理）
# 参考 https://help.aliyun.com/document_detail/216177.html
```

### 第三步：开放安全组
在阿里云 ECS 控制台 → 安全组 → 添加规则：
- 协议：TCP
- 端口：8000
- 来源：0.0.0.0/0

### 第四步：更新 APK 的 API 地址
将 `static/assets/main-DrAKBdKT.js` 中的 Railway URL 替换为你的 ECS IP：
```bash
# 在本地项目执行：
sed -i 's/xuanxue-app-production.up.railway.app/你的ECS公网IP/g' static/assets/main-DrAKBdKT.js
sed -i "s/xuanxue-app-production.up.railway.app/你的ECS公网IP/g" static/script.js

# 重新打包 APK
build_apk.bat
```

---

## 方式二：阿里云函数计算（更便宜，按调用计费）

适合流量不大的场景（免费额度很高）。

### 步骤：
1. 阿里云函数计算控制台 → 创建服务 → 创建函数
2. 选择 Python 3.11 runtime
3. 上传代码（需要将 FastAPI 改为函数计算格式）
4. 配置触发器：HTTP 触发

**注意**：这种方式需要改造代码，改动较大。

---

## 方式三：微信小程序（分发最方便）

### 优势：
- 微信内直接打开，无需安装
- 分享方便（转发卡片）
- 微信支付集成方便

### 步骤：
1. 注册微信小程序：https://mp.weixin.qq.com/
2. 下载微信开发者工具
3. 将 `dist/` 打包为小程序项目
4. 后端 API 改为云开发或独立的 API 服务

---

## 快速测试本地服务器

如果只是想测试手机端：

```bash
# 1. 确保手机和电脑在同一网络（非 Guest 网络）
# 2. 查看电脑 IP
ipconfig

# 3. 启动本地服务器
python start_local_server.py

# 4. 手机浏览器访问 http://电脑IP:8000
```

> ⚠️ Guest 网络有隔离，手机无法直接访问电脑。换用家庭WiFi或手机热点。

---

## 当前 APK 测试方法

1. **安装最新 APK**：`玄学互动_v2.0.apk`
2. **先测试网络**：手机浏览器打开 https://xuanxue-app-production.up.railway.app/api/date
   - 如果打不开 = Railway 在你网络下被屏蔽，需要换服务器
   - 如果能打开 = Railway 可用，APK 应该正常工作
3. **如果 Railway 被屏蔽**：按上面的阿里云部署步骤，替换 API 地址后重新打包
