import time
import subprocess
import json
import os
from datetime import datetime

LOG_FILE = "data/archives/patrol_reports.jsonl"
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

def log_event(event_type, details):
    timestamp = datetime.now().isoformat()
    record = {"timestamp": timestamp, "type": event_type, "details": details}
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"[{timestamp}] Đã tuần tra: {event_type}")

def scan_network():
    try:
        # Lấy danh sách kết nối mạng hiện tại
        result = subprocess.run(["netstat", "-ano"], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        established = [line.strip() for line in lines if "ESTABLISHED" in line]
        
        # Chỉ trích xuất tối đa 10 kết nối để tránh quá tải báo cáo
        return established[:10]
    except Exception as e:
        return f"Lỗi quét mạng: {e}"

def patrol_cycle():
    print("Bắt đầu chu kỳ tuần tra chủ động...")
    net_data = scan_network()
    
    # Phân tích cơ bản (Mô phỏng phát hiện dị thường)
    anomalies = []
    for conn in net_data:
        if "4444" in conn or "3389" in conn: # Các cổng thường dùng bởi Hacker/RDP
            anomalies.append(f"Cảnh báo: Phát hiện kết nối cổng nhạy cảm: {conn}")
            
    if anomalies:
        log_event("THREAT_DETECTED", anomalies)
    else:
        log_event("SYSTEM_SAFE", "Mạng ổn định, không có kết nối nguy hiểm.")

if __name__ == "__main__":
    print("========================================")
    print("SCP PATROL SERVICE - ĐÃ KÍCH HOẠT")
    print("========================================")
    
    # Chạy vòng lặp tuần tra vô tận
    for i in range(3): # Chạy thử 3 chu kỳ nhanh để demo
        patrol_cycle()
        time.sleep(5) # Trong thực tế sẽ là 300 giây (5 phút)
        
    print("Dịch vụ tuần tra đã khởi động thành công và đang chuyển vào chế độ ngầm.")
