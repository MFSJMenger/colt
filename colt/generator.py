from abc import abstractmethod
from collections import namedtuple, OrderedDict
from collections.abc import Mapping, MutableMapping
#
import configparser
import re


class GeneratorBase(Mapping):
    """Contains all core logic to generate
       code from a given config string/file

       Main use is the QuestionGenerator in colt,
       but it can also be used for other config based
       automatic code generators

       **IMPORTANT NOTE**:
       This works only if the objects generated by this method behave like
       `dictionaries` unless they are `leaf nodes`, which can be anything.
       They need therefore to have get(key, default=None) implemented!

       The tree generated by the basic generator can contain the following
       elements:

                 Node: basic container for the elements of our tree
                       basically is a `dict` and should behave like one
                       every node can contain several subnodes.

            Leaf Node: the actual elements one wants to store within
                       the tree, they are stored at the end

            Branching: a conditional branching. Similar to a standard `Node`,
                       but a branching contains a Leaf Node and then a dict of `Nodes`.

        A tree can be any of the elements above, but typically it is
        either a Branching or a Node
    """

    # please select leaf and branching type
    leafnode_type = None
    branching_type = None
    #
    node_type = dict
    #
    seperator = "::"
    default = '__GENERATOR__'
    # is there a branching in the tree?
    is_branching_regex = re.compile(r"(?P<branch>.*)\((?P<node>.*)\)")
    # named tuple to store the pair
    Branch = namedtuple("Branch", ["branch", "node"])

    def __init__(self, treeconfig):
        """Main Object to generate abstract tree from configstring

        Args:
            config(string):
                string that should be converted in the tree
        """
        if isinstance(treeconfig, (self.leafnode_type, self.node_type, self.branching_type)):
            self.tree = treeconfig
        elif not isinstance(treeconfig, str):
            raise TypeError("Generator only accepts type string!")
        self.tree, self._keys = self._configstring_to_keys_and_tree(treeconfig)

    @classmethod
    @abstractmethod
    def leaf_from_string(cls, name, value):
        """Create a leaf from an entry in the config file

        Args:
            name (str):
                name of the entry

            value (str):
                value of the entry in the config

        Returns:
            A leaf node

        Raises:
            ValueError:
                If the value cannot be parsed
        """

    @classmethod
    def new_branching(cls, name, leaf=None):
        """Create a new empty branching"""
        raise NotImplementedError("Branching not implemented in this tree, "
                                  "please implement 'new_branching'")

    @staticmethod
    def new_node():
        """Create a new node of the tree"""
        return {}

    def add_elements(self, configtree, parentnode=None, overwrite=True):
        """add elements to a particular node of the tree"""
        tree = self._get_subtree(parentnode)
        # check that treeconfig is correct type!
        subtree, keys = self._get_keys_and_subtree(configtree, parentnode=parentnode)
        self._update_keys(keys)
        # update subtree
        if overwrite is True:
            tree.update(subtree)
            return
        # overwrite it
        for key, item in subtree.items():
            if key not in tree:
                tree[key] = item

    def add_branching(self, leaf_name, branching_cases, parentnode=None):
        """Add a branching node inside `parentnode` with name `leaf_name`

        Args:
            leaf_name (str):
                name of leaf that should be replaced with a branching node

            branching_cases (dict):
                dictionary containing the cases that are implemented in the branching

        Kwargs:
            parentnode (str):
                name of the parent node

        Example:
            >>> questions.add_branching("sampling", {name: sampling.questions for name, sampling
                                                     in cls._sampling_methods.items()})
        """
        tree = self._get_subtree(parentnode)
        # generate the new branching, in case it exist return exisiting one
        tree[leaf_name] = self._new_branching_node(tree.get(leaf_name), leaf_name)
        # add branching to keys
        cases = self._join_keys(parentnode, leaf_name)
        self._update_keys(cases)
        # add cases!
        for case, config in branching_cases.items():
            # create name of real parent
            parent = self._join_keys(parentnode, self._join_case(leaf_name, case))
            subtree, keys = self._get_keys_and_subtree(config, parentnode=parent)
            self._update_keys(keys)
            tree[leaf_name][case] = subtree

    def add_node(self, name, config, parentnode=None):
        """Add a new `node` with name `name` in given `parentnode`

        Args:
            name (str):
                name of the new node

            config (string, tree):
                the config specifying the given node

        Kwargs:
            parentnode (str):
                The name of the parent node, the new node should be created in

        Raises:
            ValueError:
                If a node already exists

        Example:
            >>> _question = "sampling = "
            >>> questions.add_node("software", {name: software.questions for name, software
                                                in cls._softwares.items()})
        """
        tree = self._get_subtree(parentnode)
        subtree, keys = self._get_keys_and_subtree(config, name=name, parentnode=parentnode)
        self._update_keys(keys)
        #
        if tree.get(name) is None:
            tree[name] = subtree
        else:
            raise ValueError(f"Node '{name}' in [{parentnode}] should not exist")

    def __getitem__(self, key):
        node = self.get_node(self.tree, key)
        if node is None:
            raise KeyError(f"Node {key} does not exisit")
        return node

    def __len__(self):
        """To support full implementation of Mapping please also support these"""
        return len(self._keys)

    def __iter__(self):
        """To support full implementation of Mapping please also support these"""
        return iter(self._keys)

    def _configstring_to_keys_and_tree(self, string):
        """transform a configstring to a tree object"""
        questions = self._preprocess_configstring(string)
        return self._generate_tree(questions)

    @classmethod
    def get_node(cls, tree, node_name):
        """Parse down the abstraction tree to extract
           a particular node based on its block name
        """
        if node_name is None or node_name.strip() == "":
            return tree

        nodes = node_name.split(cls.seperator)
        for node in nodes:
            tree = cls._get_next_node(tree, node)
            if tree is None:
                return None
        return tree

    @staticmethod
    def _preprocess_string(string):
        """Basic Preprocessor"""
        return string

    @classmethod
    def _preprocess_configstring(cls, string):
        """Prepation setup for the parsing of strings into configs"""
        string = cls._preprocess_string(string)
        # add [DEFAULT] for easier parsing!
        if not string.lstrip().startswith(f'[{cls.default}]'):
            string = f'[{cls.default}]\n' + string
        #
        config = configparser.ConfigParser()
        config.read_string(string)
        return config

    @classmethod
    def _is_branching(cls, node):
        """check if node is a branching node"""
        branch = cls.is_branching_regex.match(node)
        if branch is None:
            return False
        return cls.Branch(branch.group("branch"), branch.group("node"))

    @classmethod
    def _get_next_node(cls, tree, node):
        """Get the next node of the current tree
           using the key to the node!

           Args:
                tree (object):
                    Python object that behaves like tree with
                    only dictionaries inside or objects that
                    behave like dictionaries

                node (string):
                    string to determine the next node
        """

        conditions = cls._is_branching(node)
        if conditions is False:
            return tree.get(node, None)

        node, case = conditions
        tree = tree.get(node, None)
        if tree is not None:
            return tree.get(case, None)
        return tree

    @classmethod
    def _get_parent_node(cls, node, tree):
        """Go iterative through the tree and get
           the final node, one over the selected one
           This is done in case the selected node does not
           exist and should be created.

           Args:
                node (str):
                    String to find the corresponding node in the tree

                tree (object):
                    python object that behaves like a dict of dicts
            Returns:
                final_node (str):
                    identifier of the final node
                tree (object):
                    tree object of the parent node
        """
        #
        nodes = node.split(cls.seperator)
        final_node = nodes[-1]
        #
        for nodename in nodes[:-1]:
            tree = cls._get_next_node(tree, nodename)
            if tree is None:
                return None, None
        return final_node, tree

    def _select_subnode(self, tree, nodeblock):
        """Get a node from the tree creates if it does not exist
           inside the parent node, creates it!
           iterative loop over the nodes till the selected one is reached
           in case the parent node is a branching, create a new one, if
           it is not done yet

        """
        node, tree = self._get_parent_node(nodeblock, tree)
        if node is None:
            return None
        # if is not decission, create the new node as an dict
        conditions = self._is_branching(node)
        if conditions is False:
            if node in tree:
                block, _, _ = nodeblock.rpartition(self.seperator)
                raise KeyError(f"{block} already exists in {nodeblock}")
            tree[node] = self.new_node()
            return tree[node]
        #
        branch_name, node_name = conditions
        branching = tree.get(branch_name, None)
        # insert new branching into tree
        branching = self._new_branching_node(branching, branch_name)
        if node_name not in branching:
            branching[node_name] = self.new_node()
        tree[branch_name] = branching
        return branching[node_name]

    def _new_branching_node(self, branching, branch_name):
        """
        Return a branching node, if the branching does not exist create it!

        Args:
            branching (obj):
                can be None, leaf node, branching

                    None: selected branching does not exist.
                          Create branching and a node
                          with name `node_name` inside the branching

               Leaf Node: selected branching does not exist, but a leaf node at that position
                          Create branching from that leaf node and init a node
                          with name `node_name` inside that branching

               Branching: selected branching does exist, and
                          an empty node will be created in that branching

        """
        if branching is None:
            branching = self.new_branching(branch_name)
        elif isinstance(branching, self.leafnode_type):
            branching = self.new_branching(branch_name, leaf=branching)
        elif isinstance(branching, self.branching_type):
            pass
        else:
            raise TypeError("Branching can only be typ: ",
                            f"'None', '{self.leafnode_type}', '{self.branching_type}'")
        #
        return branching

    @classmethod
    def _is_subblock(cls, block):
        """Check if block is further than one node away from
           the tree root """
        if any(key in block for key in (cls.seperator, '(', ')')):
            return True
        return False

    def _generate_tree(self, config):
        """Generate a new tree from a configparser object

        Args:
            config (dict):
                linear dictionary of the corresponding config

        Returns:
            tree (object):
                parsed tree from the config file
        """
        # list to store keys in the created tree
        keys = set()
        # add starting value
        keys.add("")
        # create starting node
        tree = self.new_node()
        # parse defaults
        for key, value in config[self.default].items():
            tree[key] = self.leaf_from_string(key, value)
        # get subsections
        subsections = [section for section in config.sections() if self._is_subblock(section)]
        # parse main sections
        for section in config.sections():
            if section == self.default:
                continue
            if self._is_subblock(section):
                continue
            # register section
            keys.add(section)
            subnode = self.new_node()
            for key, value in config[section].items():
                subnode[key] = self.leaf_from_string(key, value)
            tree[section] = subnode
        # parse all subsections
        for section in subsections:
            # gets the subnode, if it is a branching
            # and does not exist, creates it
            subnode = self._select_subnode(tree, section)
            # register section
            keys.add(section)
            if subnode is None:
                continue
            for key, value in config[section].items():
                subnode[key] = self.leaf_from_string(key, value)
        #
        return tree, keys

    _join_keys = classmethod(lambda cls, parent, key: f"{parent}{cls.seperator}{key}"
                             if not (parent is None or parent == "")
                             else key)

    _join_case = classmethod(lambda cls, branch, case: f"{branch}({case})")

    def _update_keys(self, keys):
        if isinstance(keys, set):
            self._keys |= keys
        elif isinstance(keys, str):
            self._keys.add(keys)
        else:
            TypeError(f"keys can only be set or str not {type(keys)}")

    def _get_keys(self, iterator, name=None, parentnode=None):
        keys = set()
        if name is not None:
            name = self._join_keys(parentnode, name)
            keys.add(name)
        keys |= set(self._join_keys(name, key) for key in iterator)
        return keys

    def _get_subtree(self, node_name):
        """get the node of a subtree at a given position

           important, it can not return branchings, only subtrees
        """
        subtree = self.get_node(self.tree, node_name)
        # check that subtree is correct!
        if subtree is None:
            raise KeyError(f"Node {node_name} unknown")
        if not isinstance(subtree, self.node_type):
            raise ValueError(f"Node {node_name} has to be of type {self.node_type}")
        return subtree

    def _get_keys_and_subtree(self, configtree, name=None, parentnode=None):
        """update the tree keys and get a particular node"""
        if isinstance(configtree, GeneratorBase):
            keys = self._get_keys(configtree.keys(), name=name, parentnode=parentnode)
            subtree = configtree.tree
        elif isinstance(configtree, str):
            subtree, keys = self._configstring_to_keys_and_tree(configtree)
        else:
            raise TypeError("Generator only accepts type string or GeneratorBase!")
        return subtree, keys


class BranchingNode(MutableMapping):
    """Basic Class that can be used as a Branching Node"""

    def __init__(self, name, leaf, subnodes=OrderedDict()):
        self.name = name
        self.leaf = leaf
        self.subnodes = subnodes

    def __getitem__(self, key):
        return self.subnodes[key]

    def __setitem__(self, key, value):
        self.subnodes[key] = value

    def __delitem__(self, key):
        del self.subnodes[key]

    def __iter__(self):
        return iter(self.subnodes)

    def __len__(self):
        return len(self.subnodes)

    def __str__(self):
        return (f"BranchingNode(name = {self.name},"
                f" leaf = {self.leaf}, subnodes = {self.subnodes}")

    def __repr__(self):
        return (f"BranchingNode(name = {self.name},"
                f" leaf = {self.leaf}, subnodes = {self.subnodes}")
