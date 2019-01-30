"""

Implement a Lexer.

Note the lexer has considerable code duplication in favour of remaining as
fast as I can reasonably make it.
"""
import attr
from .token import Token, TokenType


# TODO
# 0) test existing methods
#   DONE
# 1) implement [peek,next]while(<alphabet>)
#   DONE
# 2) implement [peek,next]until(<alphabet>)
#   DONE
# 3) try out Cython - and test the result
# 4) implement expectNext and expect_peek (just wrap next/peek and raise if appropriate)
#   DONE
# Overhaul 'pos' variable - should be startpos and should NOT be
# changed before emit()/ignore()

class LexerError(Exception):
    __attrs__ = ['pos', 'eof', 'buf', 'bufcursor', 'message']

    def __init__(self, lexer, message):
        self.pos = lexer.pos
        self.eof = lexer.eof
        self.buf = lexer.buf
        self.buf_cursor = lexer.buf_cursor

        self.message = message
        super().__init__(message)

    def __repr__(self):
        return "{}({})".format(
            type(self).__name__,
            ", ".join("{}={}".format(a, repr(getattr(self, a))) for a in self.__attrs__)
        )

    def __str__(self):
        return self.__repr__()


class LexerExpectError(LexerError):
    def __init__(self, lexer, expected, actual, message="did not match expected sequence"):
        super().__init__(lexer, message)
        self.expected = expected
        self.actual = actual
        assert actual != expected, "attempting to raise a LexerExpectError with matching expected/actual is nonsense"

        # lots of code to cover corner-cases and to decide where the point
        # of divergence starts.
        if len(actual) > len(expected):
            longest = actual
            shortest = expected
        else:
            longest = expected
            shortest = actual
        for n, c in enumerate(longest):
            try:
                if c != shortest[n]:
                    self.diverges_at = n
                    break
            except IndexError:
                self.diverges_at = n
                break

        self.__attrs__ = [*self.__attrs__, 'expected', 'actual', 'diverges_at']


def lex_file(fname):
    stream = open(fname, 'r+', 32768)
    return Lexer(stream=stream)


def seekable_stream(_, attribute, val):
    if not hasattr(val, 'seekable') or not callable(val.seekable):
        raise ValueError(f"'{attribute.name}' not a stream object!")
    if not val.seekable():
        raise ValueError(f"'{attribute.name}' is not a seekable stream!")


@attr.s(slots=True)
class Lexer:
    stream = attr.ib(validator=seekable_stream, repr=False)

    # the buffer (`buf`), its size (`buf_len`) and the current offset within it (`buf_cursor`)
    buf = attr.ib(init=False, type=str, default="")
    buf_len = attr.ib(init=False, type=int, default=0)
    buf_cursor = attr.ib(init=False, type=int, default=0)
    eof = attr.ib(init=False, type=bool, default=False)

    # offset within underlying buffer (uses stream.tell() )
    pos = attr.ib(init=False)

    def __attrs_post_init__(self):
        self.pos = 0
        self.eof = False

    def close(self) -> None:
        self.stream.close()

    def error(self, message: str) -> None:
        raise LexerError(self, message)

    def expect_next(self, seq: str, message: str = "contents did not match expected sequence") -> str:
        actual = self.next(len(seq))
        if actual != seq:
            raise LexerExpectError(self, seq, actual, message)
        return seq

    def expect_peek(self, seq: str, message: str = "contents did not match expected sequence") -> str:
        actual = self.peek(len(seq))
        if actual != seq:
            raise LexerExpectError(self, seq, actual, message)
        return seq

    def next(self, n: int = 1) -> str:
        cur = self.buf_cursor

        buffered = self.buf_len - cur
        if buffered >= n:
            # can satisfy request from buffer
            result = self.buf[cur:cur + n]
            self.buf_cursor += n
            self.pos += n
            return result

        # only partial or nothing in buffer
        chunks = [self.buf]
        while buffered < n:
            line = self.stream.readline()
            if line == "":  # EOF
                self.eof = True
                break
            buffered += len(line)
            chunks.append(line)
        self.buf = "".join(chunks)
        self.buf_len = buffered + cur

        to_read = min(buffered, n)
        self.buf_cursor += to_read
        self.pos += to_read
        return self.buf[cur:cur + to_read]

    def next_while(self, alphabet: str) -> str:
        if isinstance(alphabet, str):
            alphabet = list(alphabet)

        # first try using just what is buffered
        buf1 = self.buf[self.buf_cursor:]
        for n, c in enumerate(buf1):
            if c not in alphabet:
                self.buf_cursor += n
                self.pos += n
                return buf1[:n]

        # ... then go through the stream, building up an ever larger buffer as
        # we do. => need to write the new buffer back into the lex object.
        bufs = []
        while True:
            buf = self.stream.readline()
            if buf == "":
                break
            for n, c in enumerate(buf):
                if c not in alphabet:
                    self.buf = "".join([self.buf, *bufs, buf])
                    self.buf_len = len(self.buf)
                    result = "".join([buf1, *bufs, buf[:n]])
                    consumed = len(result)

                    self.buf_cursor += consumed
                    self.pos += consumed
                    return result
            bufs.append(buf)

        # Finally, handle EOF scenarios where our pattern matched
        # everything until the end of the stream (EOF)
        self.eof = True
        self.buf = "".join([self.buf, *bufs])
        self.buf_len = len(self.buf)
        result = "".join([buf1, *bufs])
        consumed = len(result)

        self.buf_cursor += consumed
        self.pos += consumed
        return result

    def next_until(self, alphabet: str) -> str:
        # IDENTICAL to nextWhile except the breaking condition
        # 'not c in alphabet' (while) => 'c in alphabet' (until)
        if isinstance(alphabet, str):
            alphabet = list(alphabet)

        # first try using just what is buffered
        buf1 = self.buf[self.buf_cursor:]
        for n, c in enumerate(buf1):
            if c in alphabet:
                self.buf_cursor += n
                self.pos += n
                return buf1[:n]

        # ... then go through the stream, building up an ever larger buffer as
        # we do. => need to write the new buffer back into the lex object.
        bufs = []
        while True:
            buf = self.stream.readline()
            if buf == "":
                break
            for n, c in enumerate(buf):
                if c in alphabet:
                    self.buf = "".join([self.buf, *bufs, buf])
                    self.buf_len = len(self.buf)
                    result = "".join([buf1, *bufs, buf[:n]])
                    consumed = len(result)

                    self.buf_cursor += consumed
                    self.pos += consumed
                    return result
            bufs.append(buf)

        # Finally, handle EOF scenarios where our pattern matched
        # everything until the end of the stream (EOF)
        self.eof = True
        self.buf = "".join([self.buf, *bufs])
        self.buf_len = len(self.buf)
        result = "".join([buf1, *bufs])
        consumed = len(result)

        self.buf_cursor += consumed
        self.pos += consumed
        return result

    def next_until_seq(self, seq: str) -> str:
        first = seq[0]
        seq_len = len(seq)
        out = []
        while True:
            out.append(self.next_until(first))
            if self.peek(seq_len) == seq:
                return "".join(out)
            out.append(self.next(1))
            if self.eof:
                return "".join(out)

    def peek(self, n: int = 1) -> str:
        cur = self.buf_cursor

        buffered = self.buf_len - cur
        if buffered >= n:
            return self.buf[cur:cur + n]

        chunks = [self.buf]
        while buffered < n:
            line = self.stream.readline()
            if line == "":  # EOF
                break
            buffered += len(line)
            chunks.append(line)
        self.buf = "".join(chunks)
        self.buf_len = buffered + cur  # == len(self.buf)

        if buffered < n:
            return self.buf[cur:]
        # not EOF, only return subsection fitting requested amount
        return self.buf[cur:cur + n]

    def peek_while(self, alphabet: str) -> str:
        if isinstance(alphabet, str):
            alphabet = list(alphabet)

        # first try using just what is buffered
        buf1 = self.buf[self.buf_cursor:]
        for n, c in enumerate(buf1):
            if c not in alphabet:
                return buf1[:n]

        # ... then go through the stream, building up an ever larger buffer as
        # we do. => need to write the new buffer back into the lex object.
        bufs = []
        while True:
            buf = self.stream.readline()
            if buf == "":
                break
            for n, c in enumerate(buf):
                if c not in alphabet:
                    self.buf = "".join([self.buf, *bufs, buf])
                    self.buf_len = len(self.buf)
                    result = "".join([buf1, *bufs, buf[:n]])

                    return result
            bufs.append(buf)

        # Finally, handle EOF scenarios where our pattern matched
        # everything until the end of the stream (EOF)
        # (But do NOT set EOF, we are peeking)
        self.buf = "".join([self.buf, *bufs])
        self.buf_len = len(self.buf)
        result = "".join([buf1, *bufs])

        return result

    def peek_until(self, alphabet: str) -> str:
        # IDENTICAL to peekWhile except the breaking condition
        # 'not c in alphabet' (while) => 'c in alphabet' (until)
        if isinstance(alphabet, str):
            alphabet = list(alphabet)

        # first try using just what is buffered
        buf1 = self.buf[self.buf_cursor:]
        for n, c in enumerate(buf1):
            if c in alphabet:
                return buf1[:n]

        # ... then go through the stream, building up an ever larger buffer as
        # we do. => need to write the new buffer back into the lex object.
        bufs = []
        while True:
            buf = self.stream.readline()
            if buf == "":
                break
            for n, c in enumerate(buf):
                if c in alphabet:
                    self.buf = "".join([self.buf, *bufs, buf])
                    self.buf_len = len(self.buf)
                    result = "".join([buf1, *bufs, buf[:n]])

                    return result
            bufs.append(buf)

        # Finally, handle EOF scenarios where our pattern matched
        # everything until the end of the stream (EOF)
        # (But do NOT set EOF, we are peeking)
        self.buf = "".join([self.buf, *bufs])
        self.buf_len = len(self.buf)
        result = "".join([buf1, *bufs])

        return result

    def current(self) -> str:
        """
        Return literal value of token if one was emitted right now
        """
        return self.buf[:self.buf_cursor]

    def rewind(self, n=1) -> None:
        """
        Rewind/"unconsume" `n` characters.

        NOTE: cannot revert beyond point of last call to emit()/ignore()
        """
        if n > self.buf_cursor:
            raise RuntimeError("cannot rewind beyond what is buffered!")
        self.buf_cursor -= n
        self.pos -= n

    def ignore(self) -> None:
        """
        Discard everything read since last emitting a token/calling ignore()
        """
        unread = self.buf_len - self.buf_cursor
        if unread == 0:
            self.buf = ""
            self.buf_len = 0
            self.buf_cursor = 0
        else:
            new_buf = self.buf[-unread:]
            self.buf = new_buf
            self.buf_len = unread
            self.buf_cursor = 0

    def emit(self, typ: TokenType) -> Token:
        """
        Emit new token using currently read literal value.
        """
        unread = self.buf_len - self.buf_cursor
        if unread != 0:
            literal = self.buf[:self.buf_cursor]
            tok = Token(type=typ, literal=literal, startpos=self.pos - len(literal))

            new_buf = self.buf[-unread:]
            self.buf = new_buf
            self.buf_len = unread
            self.buf_cursor = 0
        else:
            tok = Token(type=typ, literal=self.buf, startpos=self.pos - len(self.buf))

            self.buf = ""
            self.buf_len = 0
            self.buf_cursor = 0
        return tok
