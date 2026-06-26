# Local Auto-Start Guide

Mục tiêu: khi mở máy, stack local có thể tự chạy lại gồm ClickHouse, MinIO, Kafka,
Airflow, API backend và frontend dashboard.

## Chạy local stack

```bash
./scripts/start_local_stack.sh
```

Script này sẽ:

- bật Docker services chính bằng `docker compose up -d`;
- unpause DAG `stock_lakehouse_daily`;
- trigger DAG batch ngay khi start;
- chạy backend API ở `http://localhost:8000`;
- chạy frontend ở `http://localhost:5173`.

Nếu chỉ muốn bật dashboard/API mà không chạy batch:

```bash
TRIGGER_DAG_ON_START=0 ./scripts/start_local_stack.sh
```

Lưu ý: full batch OHLCV toàn thị trường có thể chạy lâu do giới hạn API và delay request.

## Tắt local stack

Chỉ tắt API và frontend:

```bash
./scripts/stop_local_stack.sh
```

Tắt cả Docker containers:

```bash
STOP_DOCKER=1 ./scripts/stop_local_stack.sh
```

## Auto-start khi login Linux/systemd

Tạo user service:

```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/dataengineervdt.service <<'EOF'
[Unit]
Description=DataEngineerVDT local dashboard stack
After=docker.service

[Service]
Type=oneshot
WorkingDirectory=/home/mihuyenn/projects/DataEngineerVDT
ExecStart=/home/mihuyenn/projects/DataEngineerVDT/scripts/start_local_stack.sh
RemainAfterExit=yes

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable dataengineervdt.service
systemctl --user start dataengineervdt.service
```

Nếu dùng WSL và systemd chưa bật, cách đơn giản hơn là chạy `./scripts/start_local_stack.sh`
sau khi mở terminal đầu tiên.

## URL sử dụng

- Frontend dashboard: `http://localhost:5173`
- Backend API health: `http://localhost:8000/api/health`
- Airflow: `http://localhost:8080` với `admin/admin`
- MinIO Console: `http://localhost:9001` với `minioadmin/minioadmin`
