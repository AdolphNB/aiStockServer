# Deploy to Ubuntu

## 1. Quick Start (Development/Testing)

Use the shell script to run both services in the foreground:

```bash
chmod +x start_system.sh
./start_system.sh
```

## 2. Production Deployment (Systemd)

For production, it is recommended to use `systemd` to manage the services.

### Prerequisites

Assuming your project is located at `/opt/aiStockServer` and you have a virtual environment at `/opt/aiStockServer/venv`.

### Setup

1. Copy service files to systemd directory:
   ```bash
   sudo cp deploy/aistock-api.service /etc/systemd/system/
   sudo cp deploy/aistock-fetcher.service /etc/systemd/system/
   ```

2. Reload systemd daemon:
   ```bash
   sudo systemctl daemon-reload
   ```

3. Enable and start services:
   ```bash
   # Start API Server
   sudo systemctl enable aistock-api
   sudo systemctl start aistock-api

   # Start Data Fetcher
   sudo systemctl enable aistock-fetcher
   sudo systemctl start aistock-fetcher
   ```

### Management Commands

- Check status: `sudo systemctl status aistock-api aistock-fetcher`
- View logs: 
  - API: `journalctl -u aistock-api -f`
  - Fetcher: `journalctl -u aistock-fetcher -f`
- Restart: `sudo systemctl restart aistock-api aistock-fetcher`
