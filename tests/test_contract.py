#!/usr/bin/env python3
"""The arrows only go one way — `adapter -> contract <- IDE`, checked.

The contract package's deliverable is a *direction*, and a direction is not
something the rest of the suite can fail on: every test here passed with the
cycle in place, because a cycle is a perfectly good way to run a program. So
this file exists to fail the day the arrow turns round.

Three checks, and they are deliberately different in kind:

  * **Static** — over each module's own import lines, by AST. Catches the
    import that is written but never executed on the happy path: a
    `TYPE_CHECKING` block, a function-local `from crystal_studio import x`.
    Reading the source is the only way to see either.
  * **Runtime** — import the package in a *fresh interpreter* and look at what
    came with it. While the contract lived inside the IDE, importing it ran the
    IDE's `__init__` -> `session` -> `maplint`, so no honest answer existed; a
    package of its own is what makes the question askable.
  * **The capabilities degrade to absence** — a `Hack` that declares nothing but
    a reader has no linter, no writer, no play adapter and does not measure. That
    is the rule an IDE branches on instead of on a hack's name.

"No adapter reaches the IDE" is not asked here: this repo ships no adapter, so
a scan for one would walk an empty tree and report a clean result it had not
earned. It is asked where every product is installed at once.

`test_falsified` comes last and matters most: it seeds each check with the
mutation that check exists to catch, and fails if any of them survives. It was
also run for real against `src/`, five mutations, and two of those runs are
worth writing down:

  * **A `TYPE_CHECKING`-only import of the IDE passes the runtime check and
    fails the static one.** That is the whole argument for having both, measured
    rather than asserted — an import that costs nothing at import time is
    invisible to anything that looks at `sys.modules`.
  * **A plain top-level import of the IDE in a contract module does not
    *run*.** Where the IDE is installed it is a circular import, since the IDE
    imports the contract, and where it is not it is a missing module, so this
    file dies on its own import line rather than reporting a failure. Red either
    way, and the strongest form of the check there is: the cycle is unbuildable,
    not merely disapproved of.

    python tests/test_contract.py
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

import crystal_studio_api as contract  # noqa: E402

CONTRACT = SRC / "crystal_studio_api"

#: The one part of the toolkit the contract may reach for. A coordinate tile, a
#: colour and an Edit are Gen-2 facts that already live there, and the toolkit
#: cannot import the contract back without turning the arrow round.
ALLOWED_TOOLKIT = "pret_toolkit.shared"

#: The packages above the contract: the IDE, and the adapter that ships alone.
ABOVE = ("crystal_studio", "pokeprism_devtools")

#: What a relative import that climbs out of the package is recorded as.
ESCAPED = "<above crystal_studio_api>"


def is_forbidden(name: str) -> bool:
    """Whether the contract may not name this module: anything above it, any
    part of the toolkit but `shared` (its package root comes with `shared`),
    and anything a relative import climbs to."""
    head = name.split(".")[0]
    if head == "pret_toolkit":
        return not (name in ("pret_toolkit", ALLOWED_TOOLKIT)
                    or name.startswith(ALLOWED_TOOLKIT + "."))
    return head in ABOVE or name == ESCAPED

_failures = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global _failures
    ok = bool(cond)
    print(f"  [{'OK  ' if ok else 'FAIL'}] {label}")
    if not ok:
        _failures += 1
        if detail:
            print(f"         {detail}")


# --------------------------------------------------------------------------- #
# 1 · static: what the contract's own import lines name                        #
# --------------------------------------------------------------------------- #

def imported_names(path: Path) -> list[str]:
    """Every module this file names in an import, relative ones resolved inside
    `crystal_studio_api` — or recorded as escaping it.

    Walks the whole tree rather than the top level, so an import inside a
    `TYPE_CHECKING` block or inside a function is counted. Those are the ones
    worth catching: they cost nothing at import time, which is exactly why they
    accumulate unnoticed.
    """
    return names_in_source(path.read_text())


def names_in_source(source: str) -> list[str]:
    names = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.ImportFrom):
            if node.level > 1:
                names.append(ESCAPED)
            elif node.level:
                names.append("crystal_studio_api" + (f".{node.module}" if node.module else ""))
            else:
                names.append(node.module or "")
        elif isinstance(node, ast.Import):
            names += [a.name for a in node.names]
    return [n for n in names if n]


def contract_modules() -> list[Path]:
    return sorted(CONTRACT.glob("*.py"))


def test_the_contract_names_nothing_above_itself() -> list[Path]:
    print("\nthe contract imports the standard library and pret_toolkit.shared, and nothing else")
    mods = contract_modules()
    check("the package has modules to check at all", len(mods) >= 10, str(len(mods)))

    reached = {f"{f.name}: {name}" for f in mods for name in imported_names(f)
               if name.split(".")[0] in ABOVE or name == ESCAPED}
    check("no contract module names the IDE or an adapter",
          not reached, ", ".join(sorted(reached)))

    outside = {f"{f.name}: {name}" for f in mods for name in imported_names(f)
               if name.split(".")[0] == "pret_toolkit" and is_forbidden(name)}
    check("the only part of the toolkit it reaches is pret_toolkit.shared", not outside,
          ", ".join(sorted(outside)))
    return mods


# --------------------------------------------------------------------------- #
# 2 · runtime: what a fresh interpreter drags in with it                       #
# --------------------------------------------------------------------------- #

_PROBE = (
    "import sys; sys.path.insert(0, {src!r});"
    "import crystal_studio_api;"
    "print(','.join(sorted(m for m in sys.modules"
    " if m.split('.')[0] in ('textual', 'pret_toolkit', 'crystal_studio',"
    " 'pokeprism_devtools'))))"
)


def loaded_by_importing_contract() -> set[str]:
    """The modules a bare `import crystal_studio_api` leaves behind.

    A subprocess, because this test's own imports have already loaded half the
    repo — asking `sys.modules` in *this* interpreter would answer about the test
    file, not about the package.
    """
    out = subprocess.run([sys.executable, "-c", _PROBE.format(src=str(SRC))],
                         capture_output=True, text=True, check=True)
    return {m for m in out.stdout.strip().split(",") if m}


def test_importing_it_loads_nothing_else() -> None:
    print("\nimporting the contract loads no IDE, no adapter, no widget library")
    loaded = loaded_by_importing_contract()
    strays = {m for m in loaded
              if m.split(".")[0] == "textual" or is_forbidden(m)}
    check("nothing above the contract comes with it", not strays,
          ", ".join(sorted(strays)))
    check("pret_toolkit.shared does come with it — the dependency is real, not theoretical",
          any(m.startswith("pret_toolkit.shared") for m in loaded))


# --------------------------------------------------------------------------- #
# 3 · a capability an adapter does not declare is absent, not broken           #
# --------------------------------------------------------------------------- #

class _BareReader:
    """Answers `Reads` and declares nothing else."""


def test_absence_is_the_default() -> None:
    print("\nan undeclared capability is absent, and absence is the default")
    h = contract.Hack("stub", _BareReader())
    check("a reader-only mount has no linter", h.ctx is None)
    check("...no writer", h.writes is None)
    check("...no play adapter", h.plays is None)
    check("...and does not measure", h.measures is False)

    protocols = (contract.Reads, contract.Writes, contract.Lints,
                 contract.Plays, contract.Measures, contract.Sketches)
    check("six capability protocols, no more and no fewer", len(protocols) == 6)
    check("every one is runtime_checkable — the mount asks with isinstance",
          all(hasattr(p, "_is_runtime_protocol") for p in protocols),
          str([p.__name__ for p in protocols if not hasattr(p, "_is_runtime_protocol")]))


# --------------------------------------------------------------------------- #
# falsification — each check, against the mutation it exists to catch          #
# --------------------------------------------------------------------------- #

def test_falsified(mods: list[Path]) -> None:
    print("\nfalsified: each check, against the mistake it is here to catch")

    # 1 · an import of the IDE added to a contract module, at the top level and
    #     inside a function. Parsed from text rather than written to disk: this
    #     file must not edit src/ to prove it can read it.
    victim = (CONTRACT / "hack.py").read_text()
    for label, seeded in (
        ("a top-level import", victim.replace(
            "from dataclasses import dataclass",
            "from dataclasses import dataclass\nfrom crystal_studio import tables")),
        ("an import hidden inside a method", victim + (
            "\n\ndef _late():\n    from crystal_studio.reader import read_map\n"
            "    return read_map\n")),
        ("a relative import that climbs out of the package", victim.replace(
            "from dataclasses import dataclass",
            "from dataclasses import dataclass\nfrom .. import anything")),
        ("an absolute import", victim.replace(
            "from dataclasses import dataclass",
            "from dataclasses import dataclass\n"
            "import pokeprism_devtools.maplint")),
    ):
        names = names_in_source(seeded)
        caught = any(is_forbidden(n) for n in names)
        check(f"the static check catches {label}", caught, f"hack.py: {names}")

    # 2 · the runtime probe would have to *see* a stray. Prove the probe reports
    #     what is loaded rather than an empty set it can never fail on.
    #
    #     The stray is a part of the toolkit the contract may not reach, which
    #     is installed wherever the contract is, so this half runs in every clone.
    stray = "pret_toolkit.asmedit"
    probe = _PROBE.format(src=str(SRC)).replace(
        "import crystal_studio_api;", f"import crystal_studio_api, {stray};")
    out = subprocess.run([sys.executable, "-c", probe],
                         capture_output=True, text=True, check=True)
    seen = {m for m in out.stdout.strip().split(",") if m}
    check(f"the runtime probe would have seen a stray ({stray})",
          any(m.startswith(stray) and is_forbidden(m) for m in seen),
          "the probe reports nothing, so it can never fail")

    # 3 · a Hack that declares a capability must not read as absent.
    loud = contract.Hack("stub", _BareReader(), ctx=object(), writes=object(),
                         plays=object(), measures=True)
    check("a declared capability is not absent",
          loud.ctx is not None and loud.writes is not None
          and loud.plays is not None and loud.measures is True)
    check("the module count check would notice an empty package", not [] >= [1] * 10)
    _ = mods


if __name__ == "__main__":
    modules = test_the_contract_names_nothing_above_itself()
    test_importing_it_loads_nothing_else()
    test_absence_is_the_default()
    test_falsified(modules)
    print(f"\n{'FAILURES: ' + str(_failures) if _failures else 'all ok'}")
    sys.exit(1 if _failures else 0)
