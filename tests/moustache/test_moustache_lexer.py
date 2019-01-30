import pytest
from io import StringIO
from ghostwriter.lang.lexer import Lexer, Token
from ghostwriter.moustache.lexer import MoustacheLexer


@pytest.mark.parametrize("inp, expected", [
    # TEXT
    ("hello", [Token(type='TXT', literal='hello')]),
    ("john  ", [Token(type='TXT', literal='john  ')]),
    ("very\nlong multi-line\nmessage",
        [Token(type="TXT", literal="very\nlong multi-line\nmessage")]),

    # Expr
    ("{{name}}", [Token(type='EXPR', literal='name')]),
    ("{{ name}}", [Token(type='EXPR', literal='name')]),
    ("{{name }}", [Token(type='EXPR', literal='name')]),
    ("{{  name   }}", [Token(type='EXPR', literal='name')]),

    # Partial
    ("{{>user}}", [Token(type='PARTIAL', literal='user')]),
    ("{{> user}}", [Token(type='PARTIAL', literal='user')]),
    ("{{>user }}", [Token(type='PARTIAL', literal='user')]),
    ("{{> user }}", [Token(type='PARTIAL', literal='user')]),

    # Section Open
    ("{{#item}}", [Token(type='SECTION_OPEN', literal='item')]),
    ("{{# item}}", [Token(type='SECTION_OPEN', literal='item')]),
    ("{{#item }}", [Token(type='SECTION_OPEN', literal='item')]),
    ("{{# item }}", [Token(type='SECTION_OPEN', literal='item')]),

    # Section Close
    ("{{/item}}", [Token(type='SECTION_CLOSE', literal='item')]),
    ("{{/ item}}", [Token(type='SECTION_CLOSE', literal='item')]),
    ("{{/item }}", [Token(type='SECTION_CLOSE', literal='item')]),
    ("{{/ item }}", [Token(type='SECTION_CLOSE', literal='item')]),

    # Comment
    ("{{! hello, this won't be shown}}", []),

    # Other delimiters
    ("{{=<? ?>=}}hello <? name ?>.", [
        Token(type='TXT', literal='hello '),
        Token(type="EXPR", literal="name"),
        Token(type="TXT", literal=".")]),

    ("hello {{name}}", [
        Token(type="TXT", literal="hello "),
        Token(type="EXPR", literal="name")]),

    ("hello {{! secret }} world.", [
        Token(type="TXT", literal="hello "),
        Token(type="TXT", literal=" world.")]),
])
def test_moustache(inp, expected):
    lf = Lexer(StringIO(inp))
    m = MoustacheLexer(lf)
    toks = list(m.start())
    print(toks)
    assert expected == toks, "did not get expected token sequence"
