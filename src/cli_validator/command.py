from typing import List, Optional


class CommandInfo(object):
    def __init__(self, module: Optional[str], signature: List[str], parameters: List[str]):
        self.module = module
        self.signature = signature
        self.parameters = parameters
