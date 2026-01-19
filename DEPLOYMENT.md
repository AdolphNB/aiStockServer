# 生产环境部署指南

## 服务器环境准备

### 1. 安装 Python 依赖

在服务器上执行以下命令安装所有依赖：

```bash
# 方式1: 使用 pip 安装
pip install -r requirements.txt

# 方式2: 使用 pip3 安装（推荐）
pip3 install -r requirements.txt

# 方式3: 使用 uv 安装（更快）
# 首先安装 uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# 然后使用 uv 安装依赖
uv pip install -r requirements.txt
```

### 2. 验证安装

```bash
# 验证关键包是否安装成功
python3 -c "import fastapi; print('FastAPI:', fastapi.__version__)"
python3 -c "import akshare; print('AKShare:', akshare.__version__)"
python3 -c "import pandas; print('Pandas:', pandas.__version__)"
```

### 3. 初始化数据目录

```bash
python3 init_data_dirs.py
```

### 4. 启动服务

```bash
# 开发环境（带自动重载）
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 生产环境（推荐使用 gunicorn）
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000 --access-logfile - --error-logfile -
```

## 常见问题解决

### 问题1: ModuleNotFoundError: No module named 'fastapi'

**原因**: 未安装依赖包

**解决方案**:
```bash
pip3 install -r requirements.txt
```

### 问题2: 权限错误

**原因**: 没有写入数据目录的权限

**解决方案**:
```bash
# 确保当前用户有权限写入 data 目录
sudo chown -R $USER:$USER /root/aiStockServer/data
chmod -R 755 /root/aiStockServer/data
```

### 问题3: 端口被占用

**原因**: 8000 端口已被其他服务占用

**解决方案**:
```bash
# 查看占用端口的进程
sudo lsof -i :8000

# 杀死占用端口的进程
sudo kill -9 <PID>

# 或者使用其他端口
uvicorn app.main:app --host 0.0.0.0 --port 8001
```

## 使用 systemd 管理服务

### 1. 创建服务文件

```bash
sudo nano /etc/systemd/system/aistock.service
```

### 2. 添加以下内容

```ini
[Unit]
Description=AIStock Data API Server
After=network.target

[Service]
Type=notify
User=root
WorkingDirectory=/root/aiStockServer
Environment="PATH=/usr/local/bin:/usr/bin:/bin"
ExecStart=/usr/bin/gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3. 启动和管理服务

```bash
# 重载 systemd 配置
sudo systemctl daemon-reload

# 启动服务
sudo systemctl start aistock

# 设置开机自启
sudo systemctl enable aistock

# 查看服务状态
sudo systemctl status aistock

# 查看日志
sudo journalctl -u aistock -f

# 停止服务
sudo systemctl stop aistock

# 重启服务
sudo systemctl restart aistock
```

## Nginx 反向代理配置

### 1. 安装 Nginx

```bash
sudo apt update
sudo apt install nginx -y
```

### 2. 配置反向代理

```bash
sudo nano /etc/nginx/sites-available/aistock
```

### 3. 添加配置

```nginx
server {
    listen 80;
    server_name www.mcptools.xin;

    client_max_body_size 10M;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### 4. 启用配置

```bash
# 创建软链接
sudo ln -s /etc/nginx/sites-available/aistock /etc/nginx/sites-enabled/

# 测试配置
sudo nginx -t

# 重启 Nginx
sudo systemctl restart nginx
```

### 5. 配置 SSL (可选但推荐)

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx -y

# 获取 SSL 证书
sudo certbot --nginx -d www.mcptools.xin

# 自动续期
sudo certbot renew --dry-run
```

## 性能优化建议

### 1. Worker 数量配置

```bash
# CPU 核心数
nproc

# 推荐 Worker 数量 = (2 × CPU核心数) + 1
# 例如: 4核CPU, 推荐 9 个 worker
gunicorn app.main:app -w 9 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 2. 内存监控

```bash
# 监控内存使用
free -h

# 监控进程内存
ps aux | grep gunicorn
```

### 3. 日志轮转

创建日志轮转配置：

```bash
sudo nano /etc/logrotate.d/aistock
```

添加内容：

```
/var/log/aistock/*.log {
    daily
    rotate 7
    compress
    delaycompress
    notifempty
    create 0640 root root
    sharedscripts
    postrotate
        systemctl reload aistock > /dev/null 2>&1 || true
    endscript
}
```

## 监控和维护

### 1. 健康检查

```bash
# 检查服务状态
curl http://localhost:8000/health

# 检查数据状态
curl http://localhost:8000/api/v1/data/status
```

### 2. 性能监控

```bash
# 安装 htop
sudo apt install htop -y

# 监控系统资源
htop

# 监控网络连接
netstat -tuln | grep 8000
```

### 3. 定期维护

```bash
# 清理旧的实时数据（保留最近7天）
find /root/aiStockServer/data/kline_realtime/ -type f -mtime +7 -delete

# 备份数据库
cp /root/aiStockServer/aistock.db /root/backups/aistock_$(date +%Y%m%d).db
```

## 安全建议

1. **防火墙配置**
```bash
# 允许 HTTP/HTTPS
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp

# 禁止直接访问 8000 端口（只允许内部访问）
sudo ufw deny 8000/tcp

# 启用防火墙
sudo ufw enable
```

2. **更新系统配置**
```bash
# 修改 app/core/config.py
SECRET_KEY: str = "your-secure-secret-key-here"  # 使用强密码
ADMIN_PASSWORD: str = "your-admin-password"  # 修改默认密码
```

3. **限制 API 访问（可选）**
- 添加 API 密钥认证
- 实施速率限制
- 使用 IP 白名单

## 故障排查

### 查看日志

```bash
# 服务日志
sudo journalctl -u aistock -n 100 --no-pager

# Nginx 日志
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# 应用日志
tail -f /root/aiStockServer/logs/app.log
```

### 重启服务

```bash
# 重启应用
sudo systemctl restart aistock

# 重启 Nginx
sudo systemctl restart nginx

# 完全重启
sudo systemctl restart aistock nginx
```

## 备份策略

### 1. 数据备份

```bash
# 创建备份脚本
sudo nano /root/scripts/backup_aistock.sh
```

```bash
#!/bin/bash
BACKUP_DIR="/root/backups/aistock"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# 备份数据库
cp /root/aiStockServer/aistock.db $BACKUP_DIR/aistock_$DATE.db

# 备份数据文件
tar -czf $BACKUP_DIR/data_$DATE.tar.gz -C /root/aiStockServer data/

# 删除30天前的备份
find $BACKUP_DIR -type f -mtime +30 -delete

echo "Backup completed: $DATE"
```

```bash
# 添加执行权限
chmod +x /root/scripts/backup_aistock.sh

# 添加到 crontab（每天凌晨2点备份）
crontab -e
```

添加：
```
0 2 * * * /root/scripts/backup_aistock.sh >> /var/log/aistock_backup.log 2>&1
```

## 升级步骤

```bash
# 1. 备份当前版本
cd /root
tar -czf aiStockServer_backup_$(date +%Y%m%d).tar.gz aiStockServer/

# 2. 拉取最新代码
cd /root/aiStockServer
git pull

# 3. 更新依赖
pip3 install -r requirements.txt --upgrade

# 4. 重启服务
sudo systemctl restart aistock

# 5. 验证
curl http://localhost:8000/health
```

## 完整部署命令清单

```bash
# 1. 安装依赖
cd /root/aiStockServer
pip3 install -r requirements.txt

# 2. 初始化数据目录
python3 init_data_dirs.py

# 3. 配置 systemd 服务
sudo nano /etc/systemd/system/aistock.service
# (粘贴上面的服务配置)

# 4. 启动服务
sudo systemctl daemon-reload
sudo systemctl start aistock
sudo systemctl enable aistock

# 5. 配置 Nginx（可选）
sudo apt install nginx -y
sudo nano /etc/nginx/sites-available/aistock
# (粘贴上面的 Nginx 配置)
sudo ln -s /etc/nginx/sites-available/aistock /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# 6. 验证部署
curl http://localhost:8000/health
curl http://www.mcptools.xin/health
```

## 联系支持

如遇到问题，请查看：
- 服务日志: `sudo journalctl -u aistock -f`
- 应用文档: `README.md`, `IMPLEMENTATION_NOTES.md`
- 在线文档: http://www.mcptools.xin:8000/docs
