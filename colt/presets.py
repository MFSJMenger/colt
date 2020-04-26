from .generator import GeneratorBase
from .slottedcls import slottedcls


Preset = slottedcls("Preset", {"default": None, "choices": None})


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
        default = default.strip()
        if default == "":
            default = None
        return Preset(default, choices)


    def _update_tree(self):
        main = ""
        dct = {main: {}}
        for key, value in self.tree.items():
            if isinstance(value, Preset):
                dct[main][key] = value
            else:
                dct[key] = value
        return dct

    @staticmethod
    def _is_subblock(block):
        """prevent creation of subblocks!"""
        return False

    @staticmethod
    def _parse_choices(line):
        """Handle choices"""
        if line == "":
            return None
        line = line.replace("[", "").replace("]", "")
        line = line.replace("(", "").replace(")", "")
        choices = [choice.strip() for choice in line.split(",")]
        if choices == []:
            return None
        return choices
