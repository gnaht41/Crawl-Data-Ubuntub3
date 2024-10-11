# Sử dụng Python 3.9
FROM python:3.9-slim

# Đặt thư mục làm việc
WORKDIR /app

# Sao chép các file yêu cầu vào container
COPY requirements.txt requirements.txt

# Cài đặt các gói phụ thuộc
RUN pip install --no-cache-dir -r requirements.txt

# Sao chép mã nguồn của bạn vào container
COPY . .

# Chạy lệnh khởi động Scrapy
CMD ["scrapy", "crawl", "goodreads_spider"]
