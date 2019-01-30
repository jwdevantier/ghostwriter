import pytest
from ghostwriter.lang import lexer
from io import StringIO

# TODO: test pos + ignore
# TODO: test rewind + pos

## ---
## NEW TODO
## 2) overhaul: pos => startpos
##  pos can be computed as a property
##      startpos + buflen

PANGRAM = "the quick brown fox jumps over the lazy dog"

PROG = """\
def foo(a, b):
    return 30
"""


def test_next1():
    """
    Test reading string in pieces of 1.

    Successive calls to next() to return the successive character
    in the string.
    """
    msg = "hello, world"
    lf = lexer.Lexer(StringIO(msg))
    for ndx, val in enumerate(list(msg)):
        actual = lf.next()
        assert actual == val, "failed @ {} - exp: {}, got: {}".format(ndx, val, actual)


@pytest.mark.parametrize("txt, readsiz, reads", [
    ("", 2, [""]),
    ("one", 2, ["on", "e"]),
    ("one", 3, ["one", ""]),

    ("hello, world", 2, ["he", "ll", "o,", " w", "or", "ld"]),
    ("hello, world", 3, ["hel", "lo,", " wo", "rld"]),
    ("hello, world", 4, ["hell", "o, w", "orld"]),
    ("hello, world", 5, ["hello", ", wor", "ld"]),

])
def next_chunks(txt, readsiz, reads):
    """
    Read multiple chunks of text, also in chunks where less than n chars come back (EOF)
    """
    lf = lexer.Lexer(StringIO(txt))
    for ndx, exp in enumerate(reads):
        act = lf.next(readsiz)
        assert act == exp, "read[{}] failed, exp: '{}', got: '{}'".format(
            ndx, exp, act
        )

    res = lf.next()
    assert res == "", "expected EOF, got a value"
    assert lf.eof, "expected EOF to be true"


@pytest.mark.parametrize("txt, peek_siz, exp_res", [
    ("hello, world", 1, "h"),
    ("hello, world", 2, "he"),
    ("hello, world", 3, "hel"),
    ("hello, world", 4, "hell"),
    ("hello, world", 5, "hello"),
    ("hello, world", 6, "hello,"),
    ("hello, world", 7, "hello, "),
    ("hello, world", 8, "hello, w"),
    ("hello, world", 9, "hello, wo"),
    ("hello, world", 10, "hello, wor"),
    ("hello, world", 11, "hello, worl"),
    ("hello, world", 12, "hello, world"),
    ("hello, world", 13, "hello, world"),
])
def test_peek_start(txt, peek_siz, exp_res):
    """
    Test peeking from the start of a string
    """
    lf = lexer.Lexer(StringIO(txt))
    res = lf.peek(peek_siz)
    assert res == exp_res, f"peek(n={peek_siz}) error, exp: '{exp_res}', got: {res}"
    assert not lf.eof, f"peek(n={peek_siz}) EOF value error, exp: '{exp_res}', got: '{lf.eof}'"


@pytest.mark.parametrize("description, commands", [
    # reads 4 chars into buffer via peek
    # two successive calls to next consumes that content
    ("reads 4 chars into buffer, 2 calls to next should consume it",
     [
         ("p", 4, "the "),
         ("n", 2, "th"),
         ("n", 2, "e "), ]),
    ("shows how the position is advanced for peek() as next is called",
     [
         ("p", 4, "the "),
         ("n", 5, "the q"),
         ("p", 8, "uick bro"),
         ("n", 2, "ui"),
         ("n", 2, "ck"), ]),
])
def test_peek_next_mix(description, commands):
    lf = lexer.Lexer(StringIO(PANGRAM))
    for ndx, command in enumerate(commands):
        op, n, exp_res = command
        assert op in ['p', 'n'], "test error - unknown command (p/n)"
        op = lf.peek if op == 'p' else lf.next
        act_res = op(n)
        assert act_res == exp_res, "{}: {}(n={}) failed, expected '{}'\n\tCase: {}".format(
            ndx,
            "peek" if op == lf.peek else "next",
            n, exp_res, description)


def test_pos_peek():
    lf = lexer.Lexer(StringIO(PANGRAM))
    assert lf.pos == 0, "initial position must be 0"

    lf.peek(3)
    assert lf.pos == 0, "peek() should not alter position"

    lf.next(2)
    assert lf.pos == 2, "next() should alter position"

    lf.next(len(PANGRAM))
    assert lf.pos == len(PANGRAM), "position should advance to EOF"


def test_current():
    lf = lexer.Lexer(StringIO(PANGRAM))
    assert lf.current() == "", "initially, current should be an empty string"

    lf.peek(3)
    assert lf.current() == "", "peek should not affect current"

    lf.next(3)
    assert lf.current() == "the", "next() should move character(s) into current"

    lf.next(2)
    assert lf.current() == "the q", "next(2) should've added 2 characters to current"

    lf.peek(3)
    assert lf.current() == "the q", "peek should continue to not affect current"

    lf.next(len(PANGRAM))
    assert lf.current() == PANGRAM, "reading past EOF should produce the entire contents"


def test_rewind():
    lf = lexer.Lexer(StringIO(PANGRAM))

    read = lf.next(9)
    assert read == "the quick", "error in next() abort test"
    assert lf.current() == "the quick", "error in current(), abort test"

    lf.rewind(3)
    assert lf.current() == "the qu", "[1] rewind(3) failed"
    lf.rewind(2)
    assert lf.current() == "the ", "[2] rewind(2) failed"
    lf.next(4)
    lf.rewind(1)
    assert lf.current() == "the qui", "[3] failed where we re-consumed and rewound characters"


def test_rewind_too_far():
    lf = lexer.Lexer(StringIO(PANGRAM))
    with pytest.raises(RuntimeError):
        lf.rewind(1)
    lf.peek(1)
    with pytest.raises(RuntimeError):
        lf.rewind(1)
    lf.next(5)
    with pytest.raises(RuntimeError):
        lf.rewind(6)


def test_ignore_all():
    """
    Test using ignore when the buffer cursor is at the end
    => whole buffer is to be ignore()'ed
    """
    lf = lexer.Lexer(StringIO(PANGRAM))
    lf.next(4)
    assert lf.current() == "the ", "error in current()/next(), abort"
    lf.ignore()
    assert lf.current() == "", "ignore should skip all 'consumed' characters"

    res = lf.next(3)
    assert res == "qui", "error in next()/ignore"


def test_ignore_partial():
    """
    Test using ignore when the buffer isn't fully consumed
    => the unconsumed parts of the buffer has to survive
    """
    lf = lexer.Lexer(StringIO(PANGRAM))
    print("pos_0:", lf.pos)
    lf.next(8)
    pos_8 = lf.pos
    print("pos_8:", pos_8)
    lf.next(3)
    assert lf.current() == "the quick b", "ABORT: error with next()/current()"

    pos_11 = lf.pos
    print("pos_11:", pos_11)
    lf.rewind(3)
    print("pos11 + rewind(3):", lf.pos)
    assert lf.current() == "the quic", "ABORT: error with rewind/current()"

    print("LAST IGNORE")
    lf.ignore()
    print("post-ignore pos:", lf.pos)
    assert lf.current() == "", "ignore should discard all consumed characters"

    assert lf.buf.startswith("k b"), (
        "lexer buffer should start with remaining unconsumed characters\n"
        "\tunconsumed: 'k b'\n"
        "\tactual: {}".format(lf.buf[:+3] + "..."))

    assert lf.pos == pos_8, "stream position number incorrectly inferred"


def test_emit():
    lf = lexer.Lexer(StringIO(PROG))
    res = lf.next(3)
    assert res == "def", "ABORT: next()/test error"

    tok = lf.emit("KW")
    assert tok == lexer.Token(type="KW", literal="def", startpos=0)

    lf.next(1)
    lf.ignore()

    lf.next(3)
    tok = lf.emit("fn")
    assert tok == lexer.Token(type="fn", literal="foo", startpos=4)


ALPHABET_EN = "AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz"


@pytest.mark.parametrize("txt, alphabet, exp", [
    # simple tests, single line => single buffer
    ("the big bad wolf", "eth ", "the "),
    ("the big bad wolf", "thebigbawolf ", "the big ba"),

    # multiple lines => multiple buffers
    (PROG, ALPHABET_EN + "\n (),:", "def foo(a, b):\n    return ")
])
def test_peek_while(txt, alphabet, exp):
    lf = lexer.Lexer(StringIO(txt))

    pos_start = lf.pos
    cur_start = lf.buf_cursor

    res = lf.peek_while(alphabet)
    assert res == exp, "given alphabet '{}', expected result: '{}'".format(alphabet, exp)

    assert pos_start == lf.pos, "position in buffer shouldn't change"
    assert cur_start == lf.buf_cursor, "cursor offset shouldn't change"


###############################################################################
# next_while tests
###############################################################################
@pytest.mark.parametrize("alphabet, expected", [
    (ALPHABET_EN, "hello"),
    (ALPHABET_EN + " ", "hello "),
    (ALPHABET_EN + " {{", "hello {{world"),
    (ALPHABET_EN + " {{}}\n", "hello {{world}}\nhello {{back}}"),
])
def test_next_while_no_buffer(alphabet, expected):
    lf = lexer.Lexer(StringIO("hello {{world}}\nhello {{back}}!"))
    r1 = lf.next_while(alphabet)
    assert r1 == expected, "did not get expected string back"

    assert lf.current() == expected, "lf.current() not yielding the same result"


@pytest.mark.parametrize("alphabet, expected", [
    (ALPHABET_EN, ""),
    (ALPHABET_EN + " ", ""),
    (ALPHABET_EN + " {{", "{{world"),
    (ALPHABET_EN + " {{}}", "{{world}}"),
    (ALPHABET_EN + " {{}}\n", "{{world}}\nhello {{back}}"),
])
def test_next_while_partially_consumed_buffer(alphabet, expected):
    lf = lexer.Lexer(StringIO("hello {{world}}\nhello {{back}}!"))
    # ensure we start with:
    # (1) a line in buffer
    # (2) an non-zero offset within that buffer
    assert lf.next(6) == "hello ", "error with next() call"
    r1 = lf.next_while(alphabet)
    assert r1 == expected, "did not get expected string back"

    assert lf.current() == 'hello ' + expected, "lf.current() not yielding same result"


def test_next_while_idempotent():
    lf = lexer.Lexer(StringIO("hello {{world}}"))
    r1 = lf.next_while(ALPHABET_EN + " ")
    assert r1 == "hello ", "sanity-check - next_while is broken"
    assert lf.current() == "hello ", "lf.current() should yield 'hello '"
    r2 = lf.next_while(ALPHABET_EN + " ")
    assert r2 == "", "should match nothing more the second time"

    assert lf.current() == "hello ", "lf.current() should still yield 'hello '"


@pytest.mark.parametrize("alphabet, expected, exp_eof", [
    ("1", "1111", False),
    ("1\n", "1111\n1", False),
    ("21\n", "1111\n1212\n", False),
    ("21\nx", "1111\n1212\nx", True)
])
def test_next_while_eof(alphabet, expected, exp_eof):
    lf = lexer.Lexer(StringIO("1111\n1212\nx"))
    assert lf.next_while(alphabet) == expected, "test failure or next_while broken"
    assert lf.eof == exp_eof, "next_while does not set EOF as appropriate"


###############################################################################
# next_until tests
###############################################################################
@pytest.mark.parametrize("alphabet, expected", [
    ("!", "hello {{world}}\nhello {{back}}"),
    ("\n", "hello {{world}}"),
    ("}!", "hello {{world")
])
def test_next_until_no_buffer(alphabet, expected):
    lf = lexer.Lexer(StringIO("hello {{world}}\nhello {{back}}!"))
    r1 = lf.next_until(alphabet)
    assert r1 == expected, "did not get expected string back"
    assert lf.current() == expected, "lf.current() should be the same as what's just read"


@pytest.mark.parametrize("alphabet, expected", [
    ("!", "{{world}}\nhello {{back}}"),
    ("\n", "{{world}}"),
    ("}!", "{{world")
])
def test_next_until_partially_consumed_buffer(alphabet, expected):
    lf = lexer.Lexer(StringIO("hello {{world}}\nhello {{back}}!"))
    # ensure we start with:
    # (1) a line in buffer
    # (2) an non-zero offset within that buffer
    assert lf.next(6) == "hello ", "error with next() call"
    r1 = lf.next_until(alphabet)
    assert r1 == expected, "did not get expected string back"
    assert lf.current() == "hello " + expected, "lf.current() not returning the aggregate result read"


def test_next_until_idempotent():
    lf = lexer.Lexer(StringIO("hello {{world}}"))
    r1 = lf.next_until("w")
    assert r1 == "hello {{", "sanity-check - next_until is broken"
    assert lf.current() == "hello {{", "lf.current() should return same result as read"
    r2 = lf.next_until("w")
    assert r2 == "", "should match nothing more the second time"
    assert lf.current() == "hello {{", "lf.current() should return 'hello {{' still"


@pytest.mark.parametrize("alphabet, expected, exp_eof", [
    ("21", "", False),
    ("\n", "1111", False),
    ("x", "1111\n1212\n", False),
    ("", "1111\n1212\nx", True)
])
def test_next_until_eof(alphabet, expected, exp_eof):
    lf = lexer.Lexer(StringIO("1111\n1212\nx"))
    assert lf.next_until(alphabet) == expected, "test failure or next_until broken"
    assert lf.eof == exp_eof, "next_until does not set EOF as appropriate"


###############################################################################
# peek_while tests
###############################################################################
@pytest.mark.parametrize("alphabet, expected", [
    (ALPHABET_EN, "hello"),
    (ALPHABET_EN + " ", "hello "),
    (ALPHABET_EN + " {{", "hello {{world"),
    (ALPHABET_EN + " {{}}\n", "hello {{world}}\nhello {{back}}"),
])
def test_peek_while_no_buffer(alphabet, expected):
    lf = lexer.Lexer(StringIO("hello {{world}}\nhello {{back}}!"))
    r1 = lf.peek_while(alphabet)
    assert r1 == expected, "did not get expected string back"

    assert lf.current() == "", "lf.current() should be empty, still"


@pytest.mark.parametrize("alphabet, expected", [
    (ALPHABET_EN, ""),
    (ALPHABET_EN + " ", ""),
    (ALPHABET_EN + " {{", "{{world"),
    (ALPHABET_EN + " {{}}", "{{world}}"),
    (ALPHABET_EN + " {{}}\n", "{{world}}\nhello {{back}}"),
])
def test_peek_while_partially_consumed_buffer(alphabet, expected):
    lf = lexer.Lexer(StringIO("hello {{world}}\nhello {{back}}!"))
    # ensure we start with:
    # (1) a line in buffer
    # (2) an non-zero offset within that buffer
    assert lf.next(6) == "hello ", "error with next() call"
    old_current = lf.current()
    r1 = lf.peek_while(alphabet)
    assert r1 == expected, "did not get expected string back"

    assert lf.current() == old_current, "lf.current() not yielding same result"


def test_peek_while_idempotent():
    lf = lexer.Lexer(StringIO("hello {{world}}"))
    old_current = lf.current()

    r1 = lf.peek_while(ALPHABET_EN + " ")
    assert r1 == "hello ", "sanity-check - peek_while is broken"
    assert lf.current() == old_current, "lf.current() should not have changed"

    r2 = lf.peek_while(ALPHABET_EN + " ")
    assert r2 == "hello ", "should match same string the second time"
    assert lf.current() == old_current, "lf.current() should not have changed"


###############################################################################
# peek_until tests
###############################################################################
@pytest.mark.parametrize("alphabet, expected", [
    ("!", "hello {{world}}\nhello {{back}}"),
    ("\n", "hello {{world}}"),
    ("}!", "hello {{world")
])
def test_peek_until_no_buffer(alphabet, expected):
    lf = lexer.Lexer(StringIO("hello {{world}}\nhello {{back}}!"))
    r1 = lf.peek_until(alphabet)
    assert r1 == expected, "did not get expected string back"
    assert lf.current() == "", "lf.current() should be empty"


@pytest.mark.parametrize("alphabet, expected", [
    ("!", "{{world}}\nhello {{back}}"),
    ("\n", "{{world}}"),
    ("}!", "{{world")
])
def test_peek_until_partially_consumed_buffer(alphabet, expected):
    lf = lexer.Lexer(StringIO("hello {{world}}\nhello {{back}}!"))
    # ensure we start with:
    # (1) a line in buffer
    # (2) an non-zero offset within that buffer
    assert lf.next(6) == "hello ", "error with next() call"
    old_current = lf.current()
    r1 = lf.peek_until(alphabet)
    assert r1 == expected, "did not get expected string back"
    assert lf.current() == old_current, "lf.current() should not change because of peeking"


def test_peek_until_idempotent():
    lf = lexer.Lexer(StringIO("hello {{world}}"))
    r1 = lf.peek_until("w")
    assert r1 == "hello {{", "sanity-check - peek_until is broken"
    assert lf.current() == "", "lf.current() should yield ''"
    r2 = lf.peek_until("w")
    assert r2 == "hello {{", "should match nothing more the second time"
    assert lf.current() == "", "lf.current() should yield ''"


@pytest.mark.parametrize("alphabet, expected", [
    ("21", ""),
    ("\n", "1111"),
    ("x", "1111\n1212\n"),
    ("", "1111\n1212\nx")
])
def test_peek_until_eof(alphabet, expected):
    lf = lexer.Lexer(StringIO("1111\n1212\nx"))
    assert lf.peek_until(alphabet) == expected, "test failure or peek_until broken"
    assert not lf.eof, "peek_until should not set EOF"


###############################################################################
# expect_next tests
###############################################################################
@pytest.mark.parametrize("offset, expected", [
    (0, "hello"),
    (6, "{{world"),
    (22, "{{back}}!"),
])
def test_expect_next_ok(offset, expected):
    lf = lexer.Lexer(StringIO("hello {{world}}\nhello {{back}}!"))
    lf.next(offset)
    # We rely on this call NOT raising an exception as sufficient testing
    # (expect should not raise an exception if the expectation is met)
    lf.expect_next(expected)


@pytest.mark.parametrize("offset, expected", [
    (0, "hellO"),
    (6, "{{{world"),
    (22, "{{back}!"),
])
def test_expect_next_err(offset, expected):
    lf = lexer.Lexer(StringIO("hello {{world}}\nhello {{back}}!"))
    lf.next(offset)
    with pytest.raises(lexer.LexerExpectError):
        lf.expect_next(expected)


@pytest.mark.parametrize("offset, results", [
    (0, ["hello", " {{", "world", "}}\n"]),
    (6, ["{{world}}", "\n", "hello"]),
    (22, ["{{", "back", "}}!"]),
])
def test_expect_next_multiple(offset, results):
    lf = lexer.Lexer(StringIO("hello {{world}}\nhello {{back}}!"))
    lf.next(offset)
    # We rely on this call NOT raising an exception as sufficient testing
    # (expect should not raise an exception if the expectation is met)
    for ndx, expected in enumerate(results):
        print("{}: expecting '{}'".format(ndx, expected))
        lf.expect_next(expected)


###############################################################################
# expect_peek tests
###############################################################################
@pytest.mark.parametrize("offset, expected", [
    (0, "hello"),
    (6, "{{world"),
    (22, "{{back}}!"),
])
def test_expect_peek_ok(offset, expected):
    lf = lexer.Lexer(StringIO("hello {{world}}\nhello {{back}}!"))
    lf.next(offset)
    # We rely on this call NOT raising an exception as sufficient testing
    # (expect should not raise an exception if the expectation is met)
    lf.expect_peek(expected)


@pytest.mark.parametrize("offset, expected", [
    (0, "hellO"),
    (6, "{{{world"),
    (22, "{{back}!"),
])
def test_expect_peek_err(offset, expected):
    lf = lexer.Lexer(StringIO("hello {{world}}\nhello {{back}}!"))
    lf.next(offset)
    with pytest.raises(lexer.LexerExpectError):
        lf.expect_peek(expected)


@pytest.mark.parametrize("offset, expected", [
    (0, "hello"),
    (6, "{{world"),
    (22, "{{back}}!"),
])
def test_expect_peek_idempotent(offset, expected):
    lf = lexer.Lexer(StringIO("hello {{world}}\nhello {{back}}!"))
    lf.next(offset)
    # We rely on this call NOT raising an exception as sufficient testing
    # (expect should not raise an exception if the expectation is met)
    lf.expect_peek(expected)

    lf.expect_peek(expected)  # called again, should be the same


###############################################################################
# next_until_seq tests
###############################################################################
@pytest.mark.parametrize("seq, expected", [
    ("{{", "hello "),
    ("{{#", "hello {{world}}\n"),
])
def test_next_until_seq(seq, expected):
    lf = lexer.Lexer(StringIO("hello {{world}}\n{{#names}}{{> user}}{{/names}}"))
    print("-new-test-")
    res = lf.next_until_seq(seq)
    assert res == expected, "did not get expected string back"


# TODO: next_until_seq EOF test
