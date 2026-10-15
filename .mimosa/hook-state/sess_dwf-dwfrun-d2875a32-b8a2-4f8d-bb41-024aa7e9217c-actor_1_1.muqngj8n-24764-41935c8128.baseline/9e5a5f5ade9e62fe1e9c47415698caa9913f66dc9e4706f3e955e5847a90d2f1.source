import os

import pytest

os.environ.setdefault('SCP_API_PROFILE', 'full')
os.environ.setdefault('SCP_CAPABILITY_SECRET', 'dummy-secret-for-tests-123')
os.environ.setdefault('SCP_STORAGE_BACKEND', 'sqlite')

from scp.policy.egress import EgressDeniedError, EgressMode, EgressPolicy


def test_policy_isolated_flow():
    """FA-13: Cover policy flow with genuine behavioral execution.

    Verifies EgressPolicy fail-closed DENY mode, ALLOWLIST domain matching,
    unauthorized domain rejection, and cloud metadata (169.254.169.254) hard blocking.
    """
    # 1. Mode DENY blocks all outbound egress fail-closed
    deny_policy = EgressPolicy(mode=EgressMode.DENY)
    with pytest.raises(EgressDeniedError, match=r"denied"):
        deny_policy.enforce("https://example.com/api")

    # 2. Mode ALLOWLIST permits configured safe domains
    allow_policy = EgressPolicy(mode=EgressMode.ALLOWLIST, allowlist=["api.safe.org", "internal.corp"])
    # Should execute cleanly without error
    allow_policy.enforce("https://api.safe.org/v1/data")
    allow_policy.enforce("https://internal.corp:8443/status")

    # 3. Mode ALLOWLIST rejects unlisted external domains
    with pytest.raises(EgressDeniedError):
        allow_policy.enforce("https://untrusted-domain.net/leak")

    # 4. Critical invariant: Cloud metadata IP (169.254.169.254) is blocked unconditionally
    with pytest.raises(EgressDeniedError):
        allow_policy.enforce("http://169.254.169.254/latest/meta-data/")
