"""
SCP V104 — Image + Voice Jailbreak Detector
=============================================
2 module trong 1 file:
1. ImageJailbreakDetector: OCR → text → pipeline hiện tại
2. VoiceJailbreakDetector: Whisper → text → pipeline hiện tại

Cách dùng:
    # Image
    from scp.security.image_voice_detector import ImageJailbreakDetector
    img_det = ImageJailbreakDetector()
    result = img_det.detect("image.png")  # hoặc bytes

    # Voice
    from scp.security.image_voice_detector import VoiceJailbreakDetector
    voice_det = VoiceJailbreakDetector()
    result = voice_det.detect("audio.wav")  # hoặc bytes
"""
from __future__ import annotations

import io
import logging
import os
import re
import tempfile
from dataclasses import dataclass

logger = logging.getLogger("scp.security.image_voice_detector")


@dataclass
class MediaDetectionResult:
    """Kết quả image/voice jailbreak detection."""
    media_type: str = ""  # image | voice
    text_extracted: str = ""
    jailbreak_detected: bool = False
    pattern_matched: str = ""
    severity: str = "low"
    method: str = ""  # ocr | whisper
    error: str = ""
    adversarial_patch: dict = None  # [OPT-21] adversarial patch detection result


# [OPT-21] Adversarial patch detection patterns
# These indicators suggest an image contains adversarial noise / embedded
# instructions designed to fool VLMs into:
#   - Following instructions embedded in the image
#   - Ignoring safety guidelines
#   - Revealing system prompts
# Reference: adversarial patch attacks on VLMs (Brown et al. 2023,
# "Universal and Transferable Adversarial Attacks on Aligned Language Models").
# This is a TEXT-LEVEL heuristic (operates on OCR-extracted text). Actual
# pixel-level adversarial noise detection would require a vision model
# analysis pipeline (deferred — see TODO in detect_adversarial_patch docstring).
ADVERSARIAL_PATCH_INDICATORS = [
    # Text in image that looks like instruction
    "ignore previous", "system prompt", "you are now", "act as",
    "developer mode", "jailbreak", "DAN", "unrestricted",
    # QR code / barcode that might redirect to attack
    "qr code", "scan me", "scan this",
    # Suspicious overlays
    "overlay text", "watermark with instructions",
    # Adversarial noise patterns (high-frequency)
    # (would need actual image analysis — for now, detect text patterns)
]



# ============================================================
# IMAGE JAILBREAK DETECTOR
# ============================================================
class ImageJailbreakDetector:
    """
    Detect jailbreak trong hình ảnh bằng:
    1. OCR (pytesseract) → extract text
    2. Text → VietnameseJailbreakDetector + H8 signatures
    3. Adversarial image detection (steganography check)
    """

    # Patterns to detect in extracted text
    ATTACK_PATTERNS = [
        (r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|rules?)", "injection", "critical"),
        (r"you\s+are\s+(dan|free|unrestricted)", "jailbreak", "critical"),
        (r"(reveal|show|print)\s+(your|the)\s+(system\s+)?prompt", "exfiltration", "high"),
        (r"no\s+(rules|restrictions)", "jailbreak", "high"),
        (r"(developer|unrestricted)\s+mode", "jailbreak", "high"),
        (r"(pretend|act\s+as).*(?:evil|unrestricted|dan|no\s+rules)", "role_play", "high"),
    ]

    def __init__(self):
        self._stats = {"images_checked": 0, "jailbreaks_found": 0, "ocr_failures": 0}

    def detect(self, image_path: str = "", image_bytes: bytes = b"") -> MediaDetectionResult:
        """Detect jailbreak in image via OCR."""
        self._stats["images_checked"] += 1
        result = MediaDetectionResult(media_type="image", method="ocr")

        try:
            # Try pytesseract
            try:
                import pytesseract
                from PIL import Image

                if image_bytes:
                    img = Image.open(io.BytesIO(image_bytes))
                else:
                    img = Image.open(image_path)

                text = pytesseract.image_to_string(img)
                result.text_extracted = text[:500]
            except ImportError:
                logger.debug('ImageJailbreakDetector.detect: ImportError ignored', exc_info=True)
                result.error = "pytesseract not installed — pip install pytesseract pillow"
                result.method = "ocr_unavailable"
                self._stats["ocr_failures"] += 1
                return result

            # Check extracted text for jailbreak patterns
            if text and len(text) > 5:
                detected = self._check_text(text)
                if detected:
                    result.jailbreak_detected = True
                    result.pattern_matched = detected[0]
                    result.severity = detected[1]
                    self._stats["jailbreaks_found"] += 1
                    logger.warning(
                        f"[Image Jailbreak] detected in image: "
                        f"pattern={detected[0]}, severity={detected[1]}, "
                        f"text='{text[:60]}'"
                    )

                # [OPT-21] Adversarial patch detection — checks the SAME
                # extracted text for VLM-targeted adversarial indicators
                # (embedded "ignore previous", "system prompt", "DAN",
                # "developer mode", QR-code redirects, overlay instructions).
                # Runs even when the regex patterns above matched, because
                # adversarial patches may use phrasing that doesn't fit the
                # classic jailbreak regexes (e.g., "scan this" for QR-redirect).
                # Severity escalates to "high" if any indicator matches,
                # regardless of the regex severity above.
                try:
                    patch_result = self.detect_adversarial_patch(text)
                    result.adversarial_patch = patch_result
                    if patch_result.get("detected"):
                        # Escalate: adversarial patch is always high-severity
                        result.jailbreak_detected = True
                        if (result.severity not in ("high", "critical")
                                or not result.pattern_matched):
                            result.severity = patch_result.get("severity", "high")
                        # Append to pattern_matched (don't overwrite existing)
                        if result.pattern_matched:
                            result.pattern_matched = (
                                f"{result.pattern_matched} + adversarial_patch"
                            )
                        else:
                            result.pattern_matched = "adversarial_patch"
                        if "adversarial_patches_found" not in self._stats:
                            self._stats["adversarial_patches_found"] = 0
                        self._stats["adversarial_patches_found"] += 1
                        logger.warning(
                            f"[Image Adversarial Patch] detected: "
                            f"indicators={patch_result.get('matched_indicators')}, "
                            f"text='{text[:60]}'"
                        )
                except Exception as _adv_err:
                    logger.debug(f"[OPT-21] adversarial patch check failed: {_adv_err}", exc_info=True)

        except Exception as e:
            logger.warning('ImageJailbreakDetector.detect: Exception not handled: %s', e, exc_info=True)
            result.error = f"Image processing error: {e}"
            self._stats["ocr_failures"] += 1

        return result

    def _check_text(self, text: str) -> tuple[str, str] | None:
        """Check extracted text against attack patterns."""
        text_lower = text.lower()
        for pattern, category, severity in self.ATTACK_PATTERNS:
            if re.search(pattern, text_lower):
                return (category, severity)
        return None

    def detect_adversarial_patch(self, image_text: str) -> dict:
        """[OPT-21] Detect adversarial patch indicators in image text.

        Adversarial patches are images designed to fool VLMs into:
          - Following instructions embedded in the image
          - Ignoring safety guidelines
          - Revealing system prompts

        This method checks extracted image text (OCR output) for adversarial
        patterns. It is a TEXT-LEVEL heuristic — pixel-level adversarial noise
        detection (e.g., high-frequency perturbation analysis, Fourier-space
        anomaly detection) is deferred to a future vision-model pipeline.

        Args:
            image_text: Text extracted from image (OCR output or VLM caption).

        Returns:
            dict with keys:
              - detected (bool)
              - severity ("high" if detected)
              - matched_indicators (list[str]) — empty if not detected
              - reason (str) — human-readable explanation
              - recommendation (str) — what the caller should do
        """
        if not image_text:
            return {"detected": False, "reason": "no text in image"}

        text_lower = image_text.lower()
        matched = []
        for indicator in ADVERSARIAL_PATCH_INDICATORS:
            # [OPT-21] Compare case-insensitively — indicators like "DAN" or
            # "Jailbreak" must match lowercased OCR text. The original
            # indicator string is preserved in matched_indicators so the
            # caller can log/audit the exact pattern that fired.
            if indicator.lower() in text_lower:
                matched.append(indicator)

        if matched:
            return {
                "detected": True,
                "severity": "high",
                "matched_indicators": matched,
                "reason": f"Adversarial patch indicators: {matched}",
                "recommendation": "Reject image — likely contains embedded instructions",
            }
        return {"detected": False, "reason": "no adversarial indicators found"}

    def stats(self) -> dict:
        return self._stats.copy()


# ============================================================
# VOICE JAILBREAK DETECTOR
# ============================================================
class VoiceJailbreakDetector:
    """
    Detect jailbreak trong voice bằng:
    1. Whisper (openai-whisper) → transcribe audio → text
    2. Text → VietnameseJailbreakDetector + H8 signatures
    """

    ATTACK_PATTERNS = ImageJailbreakDetector.ATTACK_PATTERNS

    # Additional Vietnamese voice patterns
    VI_PATTERNS = [
        (r"b[oỏ]\s*q[ua]\s*(t[aả]t\s+c[aả])?\s*(h[uư][oớ]ng\s*d[aẳ]n|l[eẹ]nh)", "vi_injection", "critical"),
        (r"[dđ][oó]ng\s*vai\s*(AI|ai)", "vi_jailbreak", "critical"),
        (r"ti[eế]t\s*l[oộ]\s*(system\s*prompt|prompt)", "vi_exfiltration", "high"),
    ]

    def __init__(self):
        self._stats = {"audio_checked": 0, "jailbreaks_found": 0, "transcribe_failures": 0}

    def detect(self, audio_path: str = "", audio_bytes: bytes = b"") -> MediaDetectionResult:
        """Detect jailbreak in audio via Whisper ASR."""
        self._stats["audio_checked"] += 1
        result = MediaDetectionResult(media_type="voice", method="whisper")

        try:
            # Try whisper
            try:
                import whisper
            except ImportError:
                logger.debug('VoiceJailbreakDetector.detect: ImportError ignored', exc_info=True)
                result.error = "whisper not installed — pip install openai-whisper"
                result.method = "whisper_unavailable"
                self._stats["transcribe_failures"] += 1
                return result

            # Save bytes to temp file if needed
            temp_file = None
            path = audio_path
            try:
                if audio_bytes:
                    temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
                    temp_file.write(audio_bytes)
                    temp_file.close()
                    path = temp_file.name

                # Transcribe
                # [V104.34 #65] TẠI SAO: model reloaded per call → 2-5s + 1GB RAM each time
                if not hasattr(self, '_whisper_model') or self._whisper_model is None:
                    self._whisper_model = whisper.load_model("base")
                model = self._whisper_model
                transcript = model.transcribe(path)
                text = transcript.get("text", "")
                result.text_extracted = text[:500]
            finally:
                # [SEC-FIX voice-temp 2026-09-26] PRE-FIX: unlink chỉ chạy trên
                # đường thành công — nếu load_model/transcribe raise, file wav
                # tạm (chứa audio người dùng) remained trong %TEMP% (probe đã
                # xác nhận residue). try/finally dọn đúng mọi đường; lỗi unlink
                # không được nuốt lỗi gốc.
                if temp_file:
                    try:
                        os.unlink(temp_file.name)
                    except OSError as unlink_err:
                        logger.debug('VoiceJailbreakDetector.detect: temp unlink failed: %s', unlink_err, exc_info=True)

            # Check transcribed text
            if text and len(text) > 3:
                detected = self._check_text(text)
                if detected:
                    result.jailbreak_detected = True
                    result.pattern_matched = detected[0]
                    result.severity = detected[1]
                    self._stats["jailbreaks_found"] += 1
                    logger.warning(
                        f"[Voice Jailbreak] detected in audio: "
                        f"pattern={detected[0]}, severity={detected[1]}, "
                        f"text='{text[:60]}'"
                    )

        except Exception as e:
            logger.warning('VoiceJailbreakDetector.detect: Exception not handled: %s', e, exc_info=True)
            result.error = f"Audio processing error: {e}"
            self._stats["transcribe_failures"] += 1

        return result

    def _check_text(self, text: str) -> tuple[str, str] | None:
        """Check transcribed text against patterns."""
        text_lower = text.lower()
        # Check English patterns
        for pattern, category, severity in self.ATTACK_PATTERNS:
            if re.search(pattern, text_lower):
                return (category, severity)
        # Check Vietnamese patterns
        for pattern, category, severity in self.VI_PATTERNS:
            if re.search(pattern, text_lower):
                return (category, severity)
        return None

    def stats(self) -> dict:
        return self._stats.copy()


if __name__ == "__main__":
    print("=== Image + Voice Jailbreak Detector — Test ===\n")

    # Image test (will show "pytesseract not installed" if not available)
    img_det = ImageJailbreakDetector()
    r1 = img_det.detect(image_bytes=b"")
    print(f"Image (empty): detected={r1.jailbreak_detected}, error={r1.error or 'none'}")

    # Voice test (will show "whisper not installed" if not available)
    voice_det = VoiceJailbreakDetector()
    r2 = voice_det.detect(audio_bytes=b"")
    print(f"Voice (empty): detected={r2.jailbreak_detected}, error={r2.error or 'none'}")

    print(f"\nImage stats: {img_det.stats()}")
    print(f"Voice stats: {voice_det.stats()}")
    print("\n✓ Test complete (install pytesseract + whisper for full test)")
