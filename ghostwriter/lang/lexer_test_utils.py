from .lexer import Lexer, Token


class FormattedError(Exception):
    __attrs__ = []

    def __repr__(self):
        return "{}({})".format(
            type(self).__name__,
            ", ".join("{}={}".format(a, repr(getattr(self, a))) for a in self.__attrs__)
        )

    def __str__(self):
        return self.__repr__()


class TokenError(FormattedError):
    pass


class TokenComparisonError(TokenError):
    __attrs__ = ['actual', 'expected', 'message', 'index', 'fields']

    def __init__(self, expected, actual, index, fields=None, message="actual token does not match expected token"):
        self.actual = actual
        self.expected = expected
        self.index = index
        self.message = message
        self.fields = fields or []
        super().__init__(message)


class ExtraTokensError(TokenError):
    __attrs__ = ['expected', 'actual', 'num_expected', 'num_extra']

    def __init__(self, expected, actual, message="received more tokens than expected"):
        self.expected = expected
        self.actual = actual
        self.num_expected = len(expected)
        self.num_extra = len(actual) - len(expected)


class MissingTokensError(TokenError):
    __attrs__ = ['expected', 'actual', 'num_missing', 'message']

    def __init__(self, expected, actual, message="received less tokens than expected"):
        assert len(expected) > len(actual), "'expected' must have more elements than 'actual'"
        self.expected = expected
        self.actual = actual
        self.num_missing = expected[len(actual):]
        self.message = message
        super().__init__(message)


def cmp_token_seqs(expected_seq, actual_seq, cmp_type=True, cmp_literal=True, cmp_startpos=False):
    for ndx, expected in enumerate(expected_seq):
        try:
            actual = actual_seq[ndx]
            err_fields = []
            if cmp_type and actual.type != expected.type:
                err_fields.append('type')
            if cmp_literal and actual.literal != expected.literal:
                err_fields.append('literal')
            if cmp_startpos and actual.startpos != expected.startpos:
                err_fields.append('startpos')

            if err_fields:
                raise TokenComparisonError(expected, actual, ndx, err_fields)
        except IndexError:
            raise MissingTokensError(expected, actual)
    if len(actual_seq) > len(expected_seq):
        raise ExtraTokensError(actual_seq, len(expected_seq))
