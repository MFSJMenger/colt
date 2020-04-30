class Error(Exception):
    pass


class ErrorSettingAnswerFromFile(Error):

    def __init__(self, filename, msg):
        super().__init__()
        self.filename = filename
        self.msg = msg

    def __repr__(self):
        return f"ErrorSettingAnswerFromFile: file = '{self.filename}'\n{self.msg}"

    def __str__(self):
        return f"ErrorSettingAnswerFromFile: file = '{self.filename}'\n{self.msg}"


class ErrorSettingAnswerFromDict(Error):

    def __init__(self, msg):
        super().__init__()
        self.msg = msg

    def __repr__(self):
        return f"ErrorSettingAnswerFromDict:\n{self.msg}"

    def __str__(self):
        return f"ErrorSettingAnswerFromDict:\n{self.msg}"
