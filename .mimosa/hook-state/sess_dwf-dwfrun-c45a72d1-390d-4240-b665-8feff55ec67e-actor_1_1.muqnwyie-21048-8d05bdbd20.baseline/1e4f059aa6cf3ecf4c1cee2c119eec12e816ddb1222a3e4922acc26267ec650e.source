"""
SCP - Viet Nam | Self-Correcting Pipeline
Copyright (c) 2026 SCP Vietnam Project. All Rights Reserved.




License: See LICENSE file
Contact: scp-vietnam@example.com
"""

"""
Core package - Phase0, Hypothesis Zone, Anchor, Antibody
"""
# Lazy imports to avoid circular dependency
# [FALSE-POS-FIX] ruff F822 undefined-export: PEP 562 __getattr__ resolves
# these names at runtime — ruff's static check can't see the lazy resolution.
# The file-level noqa directive below suppresses the false positive.
# ruff: noqa: F822
__all__ = [
    'Phase0Store', 'init_phase0_schema', 'init_schema', 'get_db',
    'EvidenceStore', 'ConclusionStore', 'ReasonChainStore',
    'EvidenceLinkStore', 'ChainStateService', 'db_exec',
    'HypothesisStore', 'RealityAnchor', 'AntibodyEngine',  # [BUGFIX] was 'HypothesisZone' — __getattr__ returns HypothesisStore, not HypothesisZone
]

def __getattr__(name):
    if name in ('Phase0Store', 'init_phase0_schema', 'init_schema', 'get_db',
                'EvidenceStore', 'ConclusionStore', 'ReasonChainStore',
                'EvidenceLinkStore', 'ChainStateService', 'db_exec'):
        from .phase0 import (
            ChainStateService,
            ConclusionStore,
            EvidenceLinkStore,
            EvidenceStore,
            Phase0Store,
            ReasonChainStore,
            db_exec,
            get_db,
            init_phase0_schema,
            init_schema,
        )
        return locals()[name]
    elif name == 'HypothesisStore':
        from .hypothesis_zone import HypothesisStore
        return HypothesisStore
    elif name == 'RealityAnchor':
        from .anchor import RealityAnchor
        return RealityAnchor
    elif name == 'AntibodyEngine':
        from .antibody import AntibodyEngine
        return AntibodyEngine
    raise AttributeError(f"module 'scp.core' has no attribute '{name}'")

