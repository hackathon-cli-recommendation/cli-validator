class CommandInfo(object):
    def __init__(self, module, signature, parameters):
        self.module = module
        self.signature = signature
        self.parameters = parameters


class Result(object):
    def __init__(self, no_error: bool, msg=''):
        self.no_error = no_error
        self.msg = msg
