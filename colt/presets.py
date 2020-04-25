from .generator import GeneratorBase
from .validator import NOT_DEFINED


class Preset:
    
    __slots__ = ("default", "choices")

    def __init__(self, default=None, choices=None):
        if default == "":
            default = None
        self.default = default
        self.choices = choices

    def __str__(self):
        return f"Preset(default={self.default}, choices={self.choices})"

    def __repr__(self):
        return f"Preset(default={self.default}, choices={self.choices})"


class PresetGenerator(GeneratorBase):

    comment_char = "###"
    default = '__QUESTIONS__'

    leafnode_type = Preset

    def __init__(self, questions):
        GeneratorBase.__init__(self, questions)
        self.tree = self._update_tree()

    def leaf_from_string(self, name, value, parent=None):
        """Create a leaf from an entry in the config file

        Args:
            name (str):
                name of the entry

            value (str):
                value of the entry in the config

        Kwargs:
            parent (str):
                identifier of the parent node

        Returns:
            A leaf node

        Raises:
            ValueError:
                If the value cannot be parsed
        """
        default, _, choices = value.partition(self.seperator)
        choices = self._parse_choices(choices)
        return Preset(default.strip(), choices)

    def _update_tree(self):
        main = ""
        dct = {main: {}}
        for key, value in self.tree.items():
            if isinstance(value, Preset):
                dct[main][key] = value
            else:
                dct[key] = value
        return dct

    @classmethod        
    def _is_subblock(cls, block):
        """prevent creation of subblocks!"""
        return False

    def _parse_choices(self, line):
        """Handle choices"""
        if line == "":
            return None
        if line is NOT_DEFINED:
            return None
        line = line.replace("[", "").replace("]", "")
        line = line.replace("(", "").replace(")", "")
        return [choice.strip() for choice in line.split(",")]


def set_preset(questions, presets):
    #
    presets = PresetGenerator(presets).tree
    #
    print(presets)
    for block, fields in presets.items():
        block = questions[block]
        for key, preset in fields.items():
            if key not in block:
                return
            print("set key", key)
            if preset.default is not None:
                block[key].default = preset.default
            if preset.choices is not None:
                block[key].choices = preset.choices

            print(block[key])
