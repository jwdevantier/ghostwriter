"""
"""
import attr
import typing as t
from ghostwriter.lang.lexer import Token

PRECEDENCE_LOWEST = 0
EOF = Token(type="EOF", literal="")

TokenType = str

# TODO: re-enable when recursive type support is implemented
# ASTNode = t.Union[Token, t.List['ASTNode']]
ASTNode = t.Any
TokenStream = t.Generator[Token, None, None]

PrefixFn = t.Callable[["Parser"], ASTNode]
InfixFn = t.Callable[["Parser"], ASTNode]


class ParseError(Exception):
    __attrs__: t.List[str] = []

    def __repr__(self):
        fields = ", ".join("{}={}".format(a, repr(getattr(self, a))) for a in self.__attrs__)
        return f"{type(self).__name__}({fields})"

    def __str__(self):
        return self.__repr__()


class NoPrefixParseFunction(ParseError):
    __attrs__ = ['message', 'token_type']

    def __init__(self, token_type, message=None):
        self.message = message or f"no prefix parse function found for token type '{token_type}'."
        self.token_type = token_type
        super().__init__(self.message)


class ExpectedTokenError(ParseError):
    __attrs__ = ['message', 'expected', 'actual']

    def __init__(self, expected: TokenType, actual: TokenType):
        self.expected = expected
        self.actual = actual
        self.message = f"expected token of type '{expected}', got: '{actual}'"
        super().__init__(self.message)


# TODO: refactor this out into a base Parser
@attr.s(slots=True)
class Parser:
    tokens = attr.ib(type=TokenStream)
    errors = attr.ib(type=t.List[ParseError], init=False)

    curr_token = attr.ib(type=Token, init=False)
    peek_token = attr.ib(type=Token, init=False)

    prefix_parse_fns = attr.ib(type=t.Dict[TokenType, PrefixFn], default={})
    infix_parse_fns = attr.ib(type=t.Dict[TokenType, InfixFn], default={})
    precedences = attr.ib(type=t.Dict[TokenType, int], default={})

    # For the parser to store additional data
    ctx = attr.ib(type=t.Dict[str, t.Any], default={})

    def __attrs_post_init__(self):
        # Initialization - set {curr,peek}_token up so parser is ready for use
        try:
            self.curr_token = next(self.tokens)
        except StopIteration:
            self.curr_token = EOF
            self.peek_token = EOF
            return
        try:
            self.peek_token = next(self.tokens)
        except StopIteration:
            self.peek_token = EOF

    def advance(self) -> Token:
        curr = self.curr_token
        try:
            nxt = next(self.tokens)
            self.curr_token = self.peek_token
            self.peek_token = nxt
        except StopIteration:
            self.curr_token = self.peek_token
            self.peek_token = EOF
        return curr

    def curr_token_is(self, typ: TokenType) -> bool:
        return self.curr_token.type == typ

    def peek_token_is(self, typ: TokenType) -> bool:
        return self.peek_token.type == typ

    def expect_peek(self, typ: TokenType) -> bool:
        if self.peek_token.type == typ:
            self.advance()
            return True
        self.errors.append(ExpectedTokenError(typ, self.peek_token.type))
        return False

    def prefixfn_missing_error(self, typ: TokenType) -> None:
        self.errors.append(NoPrefixParseFunction(typ))

    def curr_precedence(self, typ: TokenType) -> int:
        return self.precedences.get(typ, PRECEDENCE_LOWEST)

    def peek_precedence(self, typ: TokenType) -> int:
        return self.precedences.get(typ, PRECEDENCE_LOWEST)

    def register_prefix_fns(self, m: t.Dict[TokenType, PrefixFn]) -> None:
        self.prefix_parse_fns = {**self.prefix_parse_fns, **m}

    def register_infix_fns(self, m: t.Dict[TokenType, InfixFn]) -> None:
        self.infix_parse_fns = {**self.infix_parse_fns, **m}


def parse(moustache_tokens) -> ASTNode:
    p = Parser(tokens=moustache_tokens)
    section_stack: t.List[ASTNode] = []
    section = []

    while True:
        curr = p.advance()
        if curr == EOF:
            if len(section_stack) != 0:
                raise RuntimeError("unexpected EOF, still haven open sections")
            break
        if curr.type not in ("SECTION_OPEN", "SECTION_CLOSE"):
            section.append(curr)
        elif curr.type == "SECTION_OPEN":
            section_stack.append(section)
            section = [curr]
        else:  # SECTION_CLOSE
            if section[0].literal != curr.literal:
                raise RuntimeError("incorrect section nesting")

            parent_section = section_stack[-1]
            del section_stack[-1]
            parent_section.append(section)
            section = parent_section

    return section


