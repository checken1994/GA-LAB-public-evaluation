"""
scp/core/config_contract.py
===========================
SCP Boot Configuration Contract.

DNA #23 — Xây quá trình có khả năng tự sửa.
DNA #6  — Gốc tin cậy phải nằm ngoài runtime.

Mục đích:
  Khai báo tập các biến môi trường bắt buộc và tùy chọn.
  Validate TẠI THỜI ĐIỂM BOOT — trước khi bất kỳ endpoint nào hoạt động.
  Fail-closed: thiếu biến required → raise ConfigContractError → server không boot.

Cách dùng:
  from scp.core.config_contract import validate_boot_config
  validate_boot_config()  # gọi đầu tiên trong lifespan()

Để thêm biến mới:
  - Required: thêm vào REQUIRED_ENV với hướng dẫn tạo
  - Optional: thêm vào OPTIONAL_ENV với giá trị mặc định và điều kiện cho phép
"""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("scp.core.config_contract")


class ConfigContractError(RuntimeError):
    """Raised when the boot configuration contract is violated."""
    pass


# =============================================================================
# CONTRACT: Biến môi trường bắt buộc
# Thiếu bất kỳ biến nào → server không boot.
# =============================================================================
REQUIRED_ENV: dict[str, str] = {
    "SCP_JWT_SECRET": (
        "JWT signing key. Tạo bằng: python -c \"import secrets; print(secrets.token_hex(32))\""
    ),
    "SCP_ADMIN_KEY": (
        "Mật khẩu admin cho POST /auth/token. "
        "KHÔNG được dùng giá trị dễ đoán như 'admin', '123456'. "
        "Tạo bằng: python -c \"import secrets; print(secrets.token_urlsafe(24))\""
    ),
}

# =============================================================================
# CONTRACT: Biến môi trường tùy chọn
# Định nghĩa để doc rõ mọi biến có thể dùng, giá trị mặc định an toàn.
# =============================================================================
OPTIONAL_ENV: dict[str, tuple[str, str]] = {
    "SCP_DEEP_AUDIT_BOOT_RUN": ("0", "Set to '1' để chạy deep audit ngay tại boot+60s (mặc định 0: bỏ vòng boot để tiết kiệm LLM quota, chu kỳ 24h giữ nguyên)."),
    "SCP_FAST_LEARNING_THREAD": ("0", "Set to '1' để bật thread fast-learning nền (chu kỳ LLM thích ứng 1-30 phút; mặc định 0 để tiết kiệm quota — /v104/learn/* vẫn dùng được on demand)."),
    "SCP_PRODUCTION_MODE": ("0", "Set to '1' để bật hardening mode (HTTPS redirect, strict CORS, no /docs)."),
    "SCP_DATA_DIR": ("data", "Thư mục lưu trữ SQLite, ledger, audit logs."),
    "SCP_CORS_ORIGINS": ("", "Danh sách origin hợp lệ cách nhau bởi dấu phẩy. Để trống = chỉ localhost."),
    "SCP_OTEL_ENABLED": ("0", "Set to '1' để bật OpenTelemetry tracing."),
    "SCP_WHY_LLM_ENABLED": ("0", "Set to '1' để WHY gate dùng LLM để phân tích."),
    "SCP_SANDBOX_STRICT": ("1", "Set to '0' để cho phép fallback sandbox (KHÔNG khuyến nghị production)."),
    "OPENROUTER_API_KEY": ("", "API key cho OpenRouter LLM. Không bắt buộc nếu dùng RAG-only mode."),
}

# =============================================================================
# SECURITY RULES: Giá trị bị cấm (phát hiện config "copy từ example")
# =============================================================================
FORBIDDEN_VALUES: dict[str, list[str]] = {
    "SCP_ADMIN_KEY": [
        "admin", "password", "123456", "secret", "test", "changeme",
        "super-secret-scp-v3-enterprise-key",  # giá trị cũ bị audit phát hiện
    ],
    "SCP_JWT_SECRET": [
        "secret", "supersecret", "my-secret", "jwt-secret", "changeme",
        "super-secret-scp-v3-enterprise-key",
    ],
}

# Độ dài tối thiểu bắt buộc (chars)
MIN_LENGTH: dict[str, int] = {
    "SCP_JWT_SECRET": 32,
    "SCP_ADMIN_KEY": 8,
}


def validate_boot_config(strict: bool = True) -> dict[str, str]:
    """
    Validate toàn bộ config contract trước khi server boot.

    Returns:
        dict với các biến đã được validate (chỉ REQUIRED_ENV).

    Raises:
        ConfigContractError: nếu bất kỳ required var nào thiếu hoặc vi phạm security rule.
    """
    errors: list[str] = []
    _warnings: list[str] = []
    validated: dict[str, str] = {}

    # --- Kiểm tra REQUIRED_ENV ---
    for var_name, help_text in REQUIRED_ENV.items():
        value = os.environ.get(var_name, "").strip()
        if not value:
            errors.append(
                f"[MISSING] {var_name} chưa được set.\n"
                f"  → Hướng dẫn: {help_text}\n"
                f"  → Thêm vào .env hoặc set trước khi chạy: export {var_name}=<value>"
            )
            continue

        # Kiểm tra giá trị bị cấm
        if var_name in FORBIDDEN_VALUES:
            for forbidden in FORBIDDEN_VALUES[var_name]:
                if value.lower() == forbidden.lower():
                    errors.append(
                        f"[FORBIDDEN] {var_name} có giá trị không an toàn: '{value}'. "
                        f"Giá trị này là ví dụ mẫu hoặc đã bị audit phát hiện là yếu."
                    )
                    break

        # Kiểm tra độ dài tối thiểu
        if var_name in MIN_LENGTH and len(value) < MIN_LENGTH[var_name]:
            errors.append(
                f"[TOO_SHORT] {var_name} phải có ít nhất {MIN_LENGTH[var_name]} ký tự "
                f"(hiện tại: {len(value)})."
            )

        validated[var_name] = value

    # --- Kiểm tra OPTIONAL_ENV (chỉ warn, không fail) ---
    for var_name, (default, _description) in OPTIONAL_ENV.items():
        value = os.environ.get(var_name, default)
        if value != default:
            logger.debug("[CONFIG] %s = %s (non-default)", var_name, value[:4] + "***" if len(value) > 4 else "***")

    # --- Kết luận ---
    if errors:
        error_block = "\n".join(f"  {e}" for e in errors)
        raise ConfigContractError(
            f"\n\n{'='*60}\n"
            f"[SCP ConfigContract] Server từ chối khởi động — {len(errors)} lỗi cấu hình:\n\n"
            f"{error_block}\n\n"
            f"Tạo file .env tại thư mục gốc và điền đầy đủ các biến bắt buộc.\n"
            f"{'='*60}\n"
        )

    logger.info("[ConfigContract] Boot config OK — %d required vars validated.", len(REQUIRED_ENV))
    return validated


def get_required(var_name: str) -> str:
    """
    Lấy giá trị của một required env var.
    Raise ConfigContractError ngay lập tức nếu thiếu (không dùng fallback).
    """
    value = os.environ.get(var_name, "").strip()
    if not value:
        raise ConfigContractError(
            f"[{var_name}] Biến bắt buộc chưa được set. "
            f"Chạy validate_boot_config() lúc boot để phát hiện sớm hơn."
        )
    return value
