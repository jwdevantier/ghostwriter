import attr
import typing as t
from ghostwriter.lang import lexer
from ghostwriter.lang.token import Token

ALPHABET_EN = "AaBbCcDdEeFfGgHhIiJjKkLlMmNnOoPpQqRrSsTtUuVvWwXxYyZz"


@attr.s()
class MoustacheLexer:
    lexer = attr.ib(type=lexer.Lexer)
    seq_open = attr.ib(type=str, default="{{")
    seq_close = attr.ib(type=str, default="}}")

    def lex_ident(self, typ) -> None:
        lex = self.lexer

        lex.next_while(" \t")
        lex.next_while(ALPHABET_EN)
        lex.next_while(ALPHABET_EN + "_0123456789")
        lex.next_while(" \t")

        if lex.peek(2) != self.seq_close:
            raise lexer.LexerError(lex, "not a valid close tag, did not find close seq")

        # remove whitespace from token name literal...
        tok = lex.emit(typ)
        tok.literal = tok.literal.strip()
        yield (tok)

        lex.next(len(self.seq_close))
        lex.ignore()

    def delimiter_set(self) -> None:
        lex = self.lexer
        delim_set_close = "=" + self.seq_close
        delims = lex.next_until_seq(delim_set_close).split()
        if len(delims) != 2:
            raise lexer.LexerError(lex, f"failed to parse delimiter instruction, got '{lex.current()}'")
        self.seq_open = delims[0]
        self.seq_close = delims[1]
        lex.expect_next(delim_set_close)
        lex.ignore()

    def comment(self) -> None:
        lex = self.lexer
        lex.next_until_seq(self.seq_close)
        lex.expect_next(self.seq_close)
        lex.ignore()

    def start(self) -> t.Generator[Token, None, None]:
        lex = self.lexer
        while True:
            lex.next_until_seq(self.seq_open)
            if lex.current() != "":
                yield lex.emit("TXT")
            if lex.eof:
                break

            lex.next(len(self.seq_open))  # the opening part of the tag
            tag = lex.next(1)
            if tag == ">":
                lex.ignore()
                yield from self.lex_ident("PARTIAL")
            elif tag == "#":
                lex.ignore()
                yield from self.lex_ident("SECTION_OPEN")
            elif tag == "/":
                lex.ignore()
                yield from self.lex_ident("SECTION_CLOSE")
            elif tag == "=":
                lex.ignore()
                self.delimiter_set()
            elif tag == "!":
                self.comment()
            elif tag == "":
                raise lexer.LexerError(lex, "unexpected end of file")
            else:
                lex.rewind(1)
                lex.ignore()
                yield from self.lex_ident("EXPR")
