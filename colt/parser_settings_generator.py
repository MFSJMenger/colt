from .parser import HelpFormatter
from .colt import Colt


class HelpFormatterGenerator(Colt):

    _user_input = f"""
    #
    description =         :: literal
    #
    logo =                :: literal
    #
    short_description =   :: literal
    #
    seperator = \\n :: str
    #
    block_seperator = \\n\\n\\n :: str
    #
    main_order = {', '.join(HelpFormatter.settings['main_order'])} :: list(str) :: {', '.join(HelpFormatter.blocks)}
    #
    error_order = usage, error, space :: list(str) ::  {', '.join(HelpFormatter.blocks)}
    #
    short_order = usage, space, comment, space :: list(str) ::  {', '.join(HelpFormatter.blocks)}
    #
    args_order = pos_args, opt_args, subparser_args :: list(str) :: pos_args, opt_args, subparser_args
    #
    alias = :: str, optional
    #
    line_start = :: str, optional
    #
    line_end = :: str, optional
    #
    start = :: str, optional
    #
    end = :: str, optional

    [arg_block]
    indent = 2 :: int
    body_indent = 2 :: int
    delim = --------------------------------------------------- :: str

    [pos_args]
    title = positional arguments:
    indent = :: int, optional
    body_indent = :: int, optional
    delim = :: str, optional

    [opt_args]
    title = optional arguments:
    indent = :: int, optional
    body_indent = :: int, optional
    delim = :: str, optional

    [subparser_args]
    title = Subparser argument: %s
    indent = :: int, optional
    body_indent = :: int, optional
    delim = :: str, optional

    [arg_format]
    name = :: int, optional
    comment = :: int, optional
    choices = :: int, optional
    typ = :: int, optional
    seperator = :: int, optional

    [subparser_format]
    name = :: int, optional
    comment = :: int, optional
    """

    def from_config(cls, config):
        settings = config.to_dict()
        for key in ('seperator', 'block_seperator'):
            settings[key] = unescape(settings[key])
        res = remove_none_entries(settings)
        return res


def remove_none_entries(dct):
    out = {}
    for key, value in dct.items():
        if value is None:
            continue
        if isinstance(value, dict):
            value = remove_none_entries(value)
            if len(value) != 0:
                out[key] = value
            continue
        out[key] = value
    return out


def unescape(string):
    return string.replace('\\n', '\n')
