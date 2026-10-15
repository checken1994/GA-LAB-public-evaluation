"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

import logging

logger = logging.getLogger(__name__)


"""
AI Parser - Extract và normalize answers từ AI responses
"""
import re


class AIParser:
    """Parse và normalize AI answers để improve accuracy."""

    @staticmethod
    def parse_conversion(question: str, ai_answer: str) -> str:
        """
        Parse conversion answer - extract số từ AI response.

        Examples:
          "1 USD = 0.92 EUR" -> "0.92"
          "Tỷ giá là 123.45 VND" -> "123.45"
        """
        if not ai_answer:
            return ai_answer

        # Tìm tất cả số trong câu trả lời
        numbers = re.findall(r'[\d,]+\.?\d*', ai_answer.replace(',', ''))

        if numbers:
            try:
                # Lấy số cuối cùng (thường là kết quả)
                value = float(numbers[-1])

                # Validate: tỷ giá hợp lý (0.001 < x < 100000)
                if 0.001 < value < 100000:
                    # Format: bỏ decimal không cần thiết
                    if value == int(value):
                        return str(int(value))
                    return str(round(value, 4))
            except (ValueError, IndexError) as e:
                logger.warning(f"Silent except: {e}")

        return ai_answer  # Giữ nguyên nếu không parse được

    @staticmethod
    def parse_math(question: str, ai_answer: str) -> str:
        """
        Parse math answer - extract kết quả tính toán.

        Examples:
          "2 + 3 = 5" -> "5"
          "Kết quả là 42" -> "42"
        """
        if not ai_answer:
            return ai_answer

        # Tìm "= số" hoặc "số" ở cuối
        match = re.search(r'=\s*([\d.-]+)', ai_answer)
        if match:
            return match.group(1)

        # Hoặc lấy số cuối
        numbers = re.findall(r'-?\d+\.?\d*', ai_answer)
        if numbers:
            return numbers[-1]

        return ai_answer

    @staticmethod
    def parse_temperature(question: str, ai_answer: str) -> str:
        """
        Parse temperature answer.

        Examples:
          "Temperature is 25°C" -> "25"
          "Nhiệt độ 30 độ" -> "30"
        """
        if not ai_answer:
            return ai_answer

        # Tìm số có thể là nhiệt độ (-50 to 60)
        numbers = re.findall(r'-?\d+\.?\d*', ai_answer)
        for num_str in reversed(numbers):
            try:
                value = float(num_str)
                if -60 <= value <= 60:
                    return str(int(value)) if value == int(value) else str(value)
            except ValueError:
                logger.debug('AIParser.parse_temperature: ValueError ignored', exc_info=True)
                continue

        return ai_answer

    @staticmethod
    def parse_weight(question: str, ai_answer: str) -> str:
        """
        Parse molecular weight / mass answer.

        Examples:
          "Molecular weight = 180.16 g/mol" -> "180.16"
          "Khối lượng phân tử: 58.5 g/mol" -> "58.5"
        """
        if not ai_answer:
            return ai_answer

        # Tìm số decimal TRƯỚC (ưu tiên)
        decimals = re.findall(r'\d+\.\d+', ai_answer)
        if decimals:
            try:
                for num_str in decimals:
                    value = float(num_str)
                    if 0.1 <= value <= 10000:
                        return num_str
            except ValueError as e:
                logger.warning(f"Silent except: {e}")

        # Sau đó tìm số nguyên phù hợp
        integers = re.findall(r'(?<!\d\.)\d+', ai_answer)
        for num_str in integers:
            try:
                value = int(num_str)
                if 1 <= value <= 10000:
                    return str(value)
            except ValueError:
                logger.debug('AIParser.parse_weight: ValueError ignored', exc_info=True)
                continue

        return ai_answer

    @staticmethod
    def parse_crypto_price(question: str, ai_answer: str) -> str:
        """
        Parse cryptocurrency price.

        Examples:
          "Bitcoin price: $65,432.10" -> "65432.10"
          "Giá BTC là 65k" -> "65000"
        """
        if not ai_answer:
            return ai_answer

        # Tìm số lớn (crypto prices thường > 100)
        # [V104.37 #83] TẠI SAO: reversed() + value>10 returned date "15"
        # instead of price "65432". Fix: forward iteration + higher threshold.
        numbers = re.findall(r'[\d,]+\.?\d*', ai_answer.replace(',', ''))
        for num_str in numbers:  # forward, not reversed
            try:
                value = float(num_str)
                if value > 100:  # [V104.37 #83] was: > 10 (matched dates/versions)  # Crypto prices typically > $10
                    return str(round(value, 2))
            except ValueError:
                logger.debug('AIParser.parse_crypto_price: ValueError ignored', exc_info=True)
                continue

        return ai_answer

    @staticmethod
    def auto_parse(question: str, ai_answer: str) -> str:
        """
        Auto-detect question type và parse accordingly.

        Returns: normalized answer string
        """
        if not ai_answer:
            return ai_answer

        q_lower = question.lower()

        # [V104.35 #69] TẠI SAO: substring 'đổi' matches "thay đổi", "đổi mới", "đổi trả"
        # → wrong routing to parse_conversion. 'eth' matches "method", "ethics".
        # Fix: use word-boundary regex for short keys.
        import re as _re

        # Conversion / Currency — require word boundary for short Vietnamese keys
        if 'chuyển đổi' in q_lower or _re.search(r'\bđổi\b', q_lower) or 'tỷ giá' in q_lower:
            return AIParser.parse_conversion(question, ai_answer)

        # Temperature
        if 'nhiệt độ' in q_lower or 'temperature' in q_lower:
            return AIParser.parse_temperature(question, ai_answer)

        # Weight / Molecular
        if 'khối lượng' in q_lower or 'weight' in q_lower or 'phân tử' in q_lower:
            return AIParser.parse_weight(question, ai_answer)

        # Crypto — use word boundary for 'eth' (was: substring matched "method")
        if any(c in q_lower for c in ['bitcoin', 'btc', 'ethereum', 'crypto', 'giá']) or \
           _re.search(r'\beth\b', q_lower):
            return AIParser.parse_crypto_price(question, ai_answer)

        # Math (default) — use word boundary for 'tính' (was: matched "tính toán" ok, but also "tính cách")
        if _re.search(r'\btính\b', q_lower) or 'bằng' in q_lower or '=' in ai_answer:
            return AIParser.parse_math(question, ai_answer)

        return ai_answer
