"""Does this object answer a protocol, with the same parameters?

`isinstance` against a `runtime_checkable` Protocol only checks that the names
exist, so an adapter that renamed a parameter passes it and then fails at
whichever pane asks the question third. This compares signatures instead:
every method the protocol declares, and for each one the parameter names, kinds
and which of them have defaults.

Return annotations are deliberately **not** compared. Under
`from __future__ import annotations` they are strings, and two adapters spell
the same type differently — one declares none at all. Comparing that text fails
on agreement and passes on a lie. Calling the method and looking at what comes
back is the check that means something, and it belongs to whoever owns the
records.

It ships here rather than in a test file because the people who need it most are
outside this tree: an adapter is written against these protocols, and the battery
that proves one conforms is the same battery every in-tree adapter is held to.

    problems = check_protocol(MyReader(root), Reads)
    assert not problems, problems
"""

from __future__ import annotations

import inspect
from dataclasses import dataclass

#: A parameter reduced to what has to agree between a protocol and an
#: implementation: its name, its kind, and whether it may be omitted.
Shape = list[tuple[str, str, bool]]


@dataclass(frozen=True)
class Problem:
    """One way an object fails a protocol. `declared` is None when the method is
    absent altogether, which is a different fault from a signature that drifted
    and reads better when the report says so."""
    method: str
    detail: str
    declared: Shape | None = None
    found: Shape | None = None

    def __str__(self) -> str:
        if self.declared is None:
            return f"{self.method}: {self.detail}"
        return (f"{self.method}: {self.detail} — "
                f"declared {self.declared}, found {self.found}")


def protocol_methods(proto: type) -> list[str]:
    """The public method names a protocol declares."""
    return sorted(n for n, _ in inspect.getmembers(proto, inspect.isfunction)
                  if not n.startswith("_"))


def parameter_shape(fn) -> Shape:
    """`self` is dropped: the protocol declares it and a bound method does not."""
    params = list(inspect.signature(fn).parameters.values())
    return [(p.name, str(p.kind), p.default is not inspect.Parameter.empty)
            for p in params if p.name != "self"]


def check_protocol(obj: object, proto: type) -> list[Problem]:
    """Every way `obj` fails to answer `proto` — empty when it conforms."""
    problems: list[Problem] = []
    for name in protocol_methods(proto):
        have = getattr(type(obj), name, None)
        if have is None:
            problems.append(Problem(f"{proto.__name__}.{name}",
                                    "the method is missing entirely"))
            continue
        declared = parameter_shape(getattr(proto, name))
        found = parameter_shape(have)
        if declared != found:
            problems.append(Problem(f"{proto.__name__}.{name}",
                                    "parameters do not match", declared, found))
    return problems
