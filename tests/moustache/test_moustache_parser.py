import pytest
from io import StringIO
from ghostwriter.lang.lexer import Lexer, Token
from ghostwriter.moustache.lexer import MoustacheLexer
from ghostwriter.moustache.parser import parse


@pytest.mark.parametrize("template, ast", [
    ("hello", [Token(type='TXT', literal='hello')]),
    ("hello {{world}}", [Token('TXT', 'hello '), Token('EXPR', 'world')]),
    ("details: {{#user}}name: {{name}}\nage: {{age}}{{/user}}", [
        Token('TXT', 'details: '), [
            Token('SECTION_OPEN', 'user'),
            Token('TXT', 'name: '), Token('EXPR', 'name'),
            Token('TXT', '\nage: '), Token('EXPR', 'age')]]),
    ("""\
Hello, World.
I am {{name}} and I have a great offer, just for you!""", [
        Token('TXT', 'Hello, World.\nI am '),
        Token('EXPR', 'name'),
        Token('TXT', ' and I have a great offer, just for you!')])
])
def test_moustache(template, ast):
    lf = Lexer(StringIO(template))
    m = MoustacheLexer(lf)
    actual_ast = parse(m.start())

    print(ast)
    assert actual_ast == ast
