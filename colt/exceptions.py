class Error(Exception):
    pass


class ErrorSettingAnswerFromFile(Error):

    def __init__(self, filename, msg):
        self.filename = filename
        self.msg = msg

    def __repr__(self):
        return f"ErrorSettingAnswerFromFile: file = '{self.filename}'\n{self.msg}"

    def __str__(self):
        return f"ErrorSettingAnswerFromFile: file = '{self.filename}'\n{self.msg}"
