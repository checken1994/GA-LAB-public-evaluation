import logging

logger = logging.getLogger("scp.cognitive_router")

async def run_pre_judge_hooks(question: str, context_dict: dict):
    # 1. Threat Detector (Security)
    try:
        from scp.security.threat_detector import ThreatDetector
        td = ThreatDetector()
        threat_score = await td.analyze(ip="127.0.0.1", headers={}, body=question)
        context_dict["threat_score"] = threat_score
        if threat_score and threat_score.get("risk_level") == "CRITICAL":
            logger.warning(f"[SECURITY] ThreatDetector flagged query: {threat_score}")
    except Exception as e:
        logger.debug(f"ThreatDetector hook failed: {e}", exc_info=True)

    # 2. Why Engine (Meta)
    try:
        if "tại sao" in question.lower() or "why" in question.lower():
            from scp.meta.why_engine import WhyEngine
            why = WhyEngine()
            plan = why.create_verification_plan(question)
            if plan:
                context_dict["why_plan"] = plan.__dict__
    except Exception as e:
        logger.debug(f"WhyEngine hook failed: {e}", exc_info=True)

    return context_dict
