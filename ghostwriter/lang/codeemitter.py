class CodeEmitter(object):
    """Conveniently generate and evaluate source code."""
    INDENT_STEP = 3

    def __init__(self, indent=0):
        self.code = []
        self.indent_level = indent

    def __str__(self):
        """render out the entire code.

        Note: because CodeEmitter may contain other CodeEmitter instances
              (as extensible sections), this call may recursively
              render many objects."""
        return "".join(str(line) for line in self.code)

    def add_line(self, line):
        """Add a line of code.

        NOTE: indentation and newline is automatically handled.
              Do not add this yourself."""
        self.code.extend([" " * self.indent_level, line, '\n'])

    def add_section(self):
        """Add a section. An extensible placeholder for additional code.

        Adds a new CodeEmitter instance to this point in the code generator.
        The CodeEmitter instance effectively works as an extensible placeholder.
        Good for adding bodies to control-blocks or functions."""
        section = CodeEmitter(self.indent_level)
        self.code.append(section)
        return section

    def indent(self):
        """Increase indentation level for subsequently added lines by one.

        Increases the indentation level for subsequently added lines.
        Calling this after adding code after which follows a block of
        code (for/while/with/def) is essential."""
        self.indent_level += self.INDENT_STEP

    def dedent(self):
        """Decrease indentation level for subsequently added lines by one.

        The opposite of `indent`. Used to mark the end of a code block
        pertaining to a for/while/with/def/... block."""
        self.indent_level -= self.INDENT_STEP

    def evaluate(self):
        """Evaluate the code (and sub-sections), returns the env as a dict.

        Evaluates the code contained in this instance (and its sub-sections)
        and returns the resulting environment as a dictionary.
        The environment essentially captures the global values defined by
        evaluating the code and its entries may have data or code values.
        """
        assert self.indent_level == 0, "CodeEmitter instance have unfinished blocks (indent_level == {})".format(
            self.indent_level)

        source_code = str(self)

        # execute the code, return the defined global values
        env = {}
        exec(source_code, env)
        return env
