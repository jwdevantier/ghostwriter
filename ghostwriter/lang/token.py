import attr

TokenType = str


@attr.s(slots=True)
class Token:
    type = attr.ib(type=TokenType)
    literal = attr.ib(type=str, default="")
    startpos = attr.ib(type=int, default=0, cmp=False)
