from collections import namedtuple


Entry = namedtuple("Entry", ("name", "value", "comment"))


class IsBlock:
    __slots__ = ()

    def __str__(self):
        return "IS_BLOCK"

    def __repr__(self):
        return "IS_BLOCK"


IS_BLOCK = IsBlock()


def comment_iterator(iterator, comment_string):
    for line in iterator:
        line, _, _ = line.partition(comment_string)
        line = line.strip()
        if line == "":   # Ignore empty lines
            continue
        yield line


def parse(iterator):
    if isinstance(iterator, str):
        iterator = iterator.splitlines()
    #
    comments = []

    for line in comment_iterator(iterator, "//"):
        if line.startswith('#'):
            if line.startswith('# '):
                comments.append(line[2:])
            else:
                comments.append(line[1:])
            continue
        yield parse_line(line, get_comments(comments))
        # reset comment
        comments = []


def parse_line(line, comment):
    if line.startswith('['):
        if not line.endswith(']'):
            raise ValueError(f"Do not understand line '{line}'")
        return Entry(line[1:-1].strip(), IS_BLOCK, comment)
    return parse_entry_line(line, comment)


def get_comments(comment):
    if comment == []:
        return None
    return "\n".join(comment)


def parse_entry_line(line, comment):
    name, delim, value = line.partition('=')
    if delim != '=':
        raise ValueError(f"Do not understand line '{line}'")
    return Entry(name.strip(), value, comment)
