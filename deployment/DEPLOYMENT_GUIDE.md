# AIStock Server 部署指南

本指南介绍如何在Ubuntu服务器上部署AIStock服务器，实现生产环境运行。

## 系统要求

- Ubuntu 20.04 LTS 或更高版本
- Python 3.9+
- Nginx
- 域名：www.mcptools.xin
- SSL证书（推荐使用Let's Encrypt）

## 1. 服务器初始设置

### 1.1 创建专用用户

```bash
# Create dedicated user for the application
sudo adduser --system --group --home /opt/aistock aistock
```

### 1.2 安装系统依赖

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Install required packages
sudo apt install -y python3-pip python3-venv nginx certbot python3-certbot-nginx
```

## 2. 应用部署

### 2.1 上传代码

```bash
# Create application directory
sudo mkdir -p /opt/aistock/aiStockServer
sudo chown -R aistock:aistock /opt/aistock

# Upload your code to /opt/aistock/aiStockServer
# You can use scp, rsync, or git clone
# Example using git:
sudo -u aistock git clone <your-repo-url> /opt/aistock/aiStockServer
```

### 2.2 创建虚拟环境并安装依赖

```bash
# Switch to aistock user
sudo -u aistock bash

# Create virtual environment
cd /opt/aistock
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate

# Install dependencies
cd aiStockServer
pip install -r requirements.txt

# Exit aistock user
exit
```

### 2.3 配置环境变量

创建环境变量文件：

```bash
sudo nano /opt/aistock/.env
```

添加以下内容（根据实际情况修改）：

```bash
# Server Configuration
PORT=8000
SERVER_URL=https://www.mcptools.xin

# Database
DATABASE_URL=sqlite:////opt/aistock/data/aistock.db

# WeChat Pay Configuration (获取后填入)
WECHAT_APPID=your_wechat_appid
WECHAT_MCHID=your_merchant_id
WECHAT_API_KEY=your_api_key
WECHAT_API_V3_KEY=your_api_v3_key

# Admin
ADMIN_USERNAME=admin
ADMIN_PASSWORD=your_secure_password_here

# Security
SECRET_KEY=your_very_secure_secret_key_here
```

```bash
# Set proper permissions
sudo chown aistock:aistock /opt/aistock/.env
sudo chmod 600 /opt/aistock/.env
```

### 2.4 创建数据目录和日志目录

```bash
# Create directories
sudo mkdir -p /opt/aistock/data
sudo mkdir -p /var/log/aistock

# Set permissions
sudo chown -R aistock:aistock /opt/aistock/data
sudo chown -R aistock:aistock /var/log/aistock
```

## 3. 配置Systemd服务

### 3.1 复制服务文件

```bash
# Copy systemd service file
sudo cp /opt/aistock/aiStockServer/deployment/systemd_service.conf /etc/systemd/system/aistock.service

# Reload systemd
sudo systemctl daemon-reload
```

### 3.2 启动服务

```bash
# Enable service on boot
sudo systemctl enable aistock

# Start service
sudo systemctl start aistock

# Check status
sudo systemctl status aistock

# View logs
sudo journalctl -u aistock -f
```

## 4. 配置Nginx

### 4.1 获取SSL证书

```bash
# Get Let's Encrypt certificate
sudo certbot certonly --nginx -d www.mcptools.xin -d mcptools.xin

# Certificate will be saved at:
# /etc/letsencrypt/live/mcptools.xin/fullchain.pem
# /etc/letsencrypt/live/mcptools.xin/privkey.pem
```

### 4.2 配置Nginx

```bash
# Copy nginx configuration
sudo cp /opt/aistock/aiStockServer/deployment/nginx.conf /etc/nginx/sites-available/aistock

# Create symbolic link
sudo ln -s /etc/nginx/sites-available/aistock /etc/nginx/sites-enabled/

# Remove default site if exists
sudo rm -f /etc/nginx/sites-enabled/default

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

## 5. 负载均衡配置（多Worker）

为了支持20+并发用户，建议配置多个worker进程：

### 方法1：使用Gunicorn（推荐）

systemd服务文件中已配置了gunicorn的多worker模式。根据服务器CPU核心数调整worker数量：

```bash
# 编辑服务文件
sudo nano /etc/systemd/system/aistock.service

# 修改 --workers 参数
# 推荐配置：workers = (2 x CPU核心数) + 1
# 例如：4核CPU -> 9个workers
--workers 9
```

### 方法2：手动启动多个Uvicorn进程

```bash
# 使用提供的脚本
cd /opt/aistock/aiStockServer/deployment
chmod +x multi_worker_setup.sh

# 启动多个worker
sudo ./multi_worker_setup.sh start

# 查看状态
sudo ./multi_worker_setup.sh status

# 停止
sudo ./multi_worker_setup.sh stop
```

## 6. 防火墙配置

```bash
# Allow HTTP and HTTPS
sudo ufw allow 'Nginx Full'

# Allow SSH (if not already allowed)
sudo ufw allow 22/tcp

# Enable firewall
sudo ufw enable

# Check status
sudo ufw status
```

## 7. 监控和维护

### 7.1 查看日志

```bash
# Application logs
sudo journalctl -u aistock -f

# Nginx access logs
sudo tail -f /var/log/nginx/aistock_access.log

# Nginx error logs
sudo tail -f /var/log/nginx/aistock_error.log
```

### 7.2 健康检查

访问健康检查端点：

```bash
curl https://www.mcptools.xin/health
```

### 7.3 后台管理

访问后台管理界面：

```
https://www.mcptools.xin/admin
```

默认用户名密码：admin/admin（请尽快修改）

## 8. 微信支付配置

### 8.1 获取微信支付商户号

1. 访问微信支付商户平台：https://pay.weixin.qq.com
2. 注册并完成商户认证
3. 获取以下信息：
   - AppID（应用ID）
   - 商户号（MchID）
   - API密钥（Key）

### 8.2 配置支付参数

编辑环境变量文件：

```bash
sudo nano /opt/aistock/.env
```

填入实际的微信支付参数。

### 8.3 重启服务

```bash
sudo systemctl restart aistock
```

## 9. 性能优化建议

### 9.1 数据库优化

如果订阅用户增多，建议从SQLite迁移到PostgreSQL或MySQL：

```bash
# 安装PostgreSQL
sudo apt install -y postgresql postgresql-contrib

# 创建数据库
sudo -u postgres psql
CREATE DATABASE aistock;
CREATE USER aistock WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE aistock TO aistock;
\q

# 更新DATABASE_URL
DATABASE_URL=postgresql://aistock:your_password@localhost/aistock
```

### 9.2 Redis缓存（可选）

对于高并发场景，可以添加Redis缓存：

```bash
# 安装Redis
sudo apt install -y redis-server

# 启动Redis
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

## 10. 故障排查

### 服务无法启动

```bash
# 查看详细日志
sudo journalctl -u aistock -n 100 --no-pager

# 检查配置文件
sudo -u aistock /opt/aistock/venv/bin/python -c "from app.core.config import settings; print(settings)"
```

### Nginx 502错误

```bash
# 检查后端服务是否运行
sudo systemctl status aistock

# 检查端口是否监听
sudo netstat -tlnp | grep 800
```

### 支付回调失败

```bash
# 检查Nginx日志
sudo tail -f /var/log/nginx/aistock_access.log | grep notify

# 检查应用日志
sudo journalctl -u aistock -f | grep wechat
```

## 11. 安全加固

1. **定期更新系统**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

2. **配置自动SSL证书续期**
   ```bash
   # Certbot会自动配置续期，检查定时任务
   sudo systemctl status certbot.timer
   ```

3. **限制SSH访问**
   ```bash
   # 禁用root登录，只允许密钥认证
   sudo nano /etc/ssh/sshd_config
   # 设置：
   # PermitRootLogin no
   # PasswordAuthentication no
   ```

4. **配置fail2ban防止暴力破解**
   ```bash
   sudo apt install -y fail2ban
   sudo systemctl enable fail2ban
   sudo systemctl start fail2ban
   ```

## 12. 备份策略

### 12.1 数据库备份

```bash
# 创建备份脚本
sudo nano /opt/aistock/backup.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/opt/aistock/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup database
cp /opt/aistock/data/aistock.db $BACKUP_DIR/aistock_$DATE.db

# Keep only last 7 days of backups
find $BACKUP_DIR -name "aistock_*.db" -mtime +7 -delete

echo "Backup completed: aistock_$DATE.db"
```

```bash
# 设置权限并添加到crontab
sudo chmod +x /opt/aistock/backup.sh
sudo crontab -e
# 添加：每天凌晨2点备份
0 2 * * * /opt/aistock/backup.sh
```

## 支持

如有问题，请查看项目文档或联系技术支持。
