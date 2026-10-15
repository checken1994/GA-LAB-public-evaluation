from dataclasses import dataclass


@dataclass
class CapabilityToken:
    action: str
    resource: str
    level: int
    approved: bool

class CapabilityManager:
    def __init__(self):
        self._issued = []

    def issue_token(self, action: str, resource: str, level: int = 1, approved: bool = False) -> CapabilityToken:
        token = CapabilityToken(action, resource, level, approved)
        self._issued.append(token)
        return token
