# 1. Base Image nhẹ
FROM python:3.11-slim

# 2. Setup môi trường
WORKDIR /app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Quan trọng: Giúp Python tìm thấy code trong thư mục src
ENV PYTHONPATH=/app/src

# 3. Cài đặt thư viện
# Copy file quản lý gói
COPY pyproject.toml uv.lock ./
# Cài đặt thư viện (Dùng pip để cài từ file pyproject.toml)
RUN pip install --no-cache-dir .

# 4. Copy code nguồn vào
COPY src/ ./src
COPY alembic.ini .
COPY migration/ ./migration

# 5. Mở cổng
EXPOSE 8000

# 6. Lệnh chạy
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]