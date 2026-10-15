"""
SCP LLM Gateway — Unified LLM access layer.

Package-bound enforcement order:
  1. egress guard — destination/network authority; always on.
  2. free-model routing — filters candidates by the discovery allowlist
     maintained by free_catalog.py.

Zero-cost guard (Z2/Z3) has been architecturally deprecated.  The egress
guard is the sole surviving enforcement layer installed at package import time.
"""
from scp.llm_gateway import client as _client
from scp.llm_gateway.egress_policy import install_egress_guard

install_egress_guard(_client.OpenRouterProvider)

LLMGateway = _client.LLMGateway
get_gateway = _client.get_gateway
chat_sync = _client.chat_sync

__all__ = ["LLMGateway", "get_gateway", "chat_sync"]
