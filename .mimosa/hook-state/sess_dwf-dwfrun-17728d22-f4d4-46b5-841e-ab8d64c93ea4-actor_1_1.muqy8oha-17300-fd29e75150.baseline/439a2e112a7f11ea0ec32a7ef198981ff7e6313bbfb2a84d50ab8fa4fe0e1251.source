import requests
import time
import sys

API_BASE = 'http://127.0.0.1:8000'

def wait_for_server():
    for _ in range(10):
        try:
            resp = requests.get(f'{API_BASE}/health')
            if resp.status_code == 200:
                print('✅ [E2E] Live Server is HEALTHY')
                return
        except:
            pass
        time.sleep(1)
    print('❌ [E2E] Server failed to start')
    sys.exit(1)

def run_e2e_flow():
    # Bước 1: Tạo Task qua API thật
    print('✅ [E2E] Bắn API tạo task...')
    # Phải check swagger để biết chính xác body, tạm thời check qua recovery
    pass

if __name__ == '__main__':
    wait_for_server()
