import os

# Set environment variables BEFORE any SCP modules are imported by pytest.
#
# [A13a T02-05 note] `os.environ` (không phải monkeypatch.setenv) là CỐ Ý
# tại đây: các giá trị này phải có sẵn TRƯỚC KHI pytest import module SCP
# đầu tiên (config contract đọc env lúc import time), nên fixture
# monkeypatch của pytest chưa tồn tại ở giai đoạn này. Files conftest của
# từng suite (vd tests/T12_unified_chatbot/conftest.py) dùng monkeypatch
# cho env cần isolate per-test.
os.environ["SCP_API_PROFILE"] = "full"
os.environ["SCP_CAPABILITY_SECRET"] = "dummy-secret-for-tests-123"
os.environ["SCP_STORAGE_BACKEND"] = "sqlite"
os.environ["SCP_TOP_SYSTEMS_EGRESS"] = "0"
