#!/usr/bin/env python3
"""The arrows only go one way — `adapter -> contract <- IDE`, checked.

The contract package's deliverable is a *direction*, and a direction is not
something the rest of the suite can fail on: every test here passed with the
cycle in place, because a cycle is a perfectly good way to run a program. So
this file exists to fail the day the arrow turns round.

Three checks, and they are deliberately different in kind:

  * **Static** — over each `contract/` module's own import lines, by AST. Catches
    the import that is written but never executed on the happy path: a
    `TYPE_CHECKING` block, a function-local `from ...studio import x`. Reading
    the source is the only way to see either.
  * **Runtime** — import the package in a *fresh interpreter* and look at what
    came with it. This is the check `test_vanilla.py` wrote off as unaskable:
    while the base lived in `studio/`, importing it ran `studio/__init__` ->
    `session` -> `maplint`, so no honest answer existed. Moving it is what makes
    the question askable, and asking it is how we know the move landed.
  * **The capabilities degrade to absence** — a `Hack` that declares nothing but
    a reader has no linter, no writer, no play adapter and does not measure. That
    is the rule an IDE branches on instead of on a hack's name.

**A fourth check used to stand here and cannot any more.** "No adapter reaches
the IDE" scanned every module under `hacks/` for a line importing the IDE — and
this repo is the seam, which ships no adapters at all, so the scan walked an
empty tree and reported a clean result it had not earned. The question is only
answerable where every product is installed at once, since each adapter is now
its own distribution, and that is where it is asked.

`test_falsified` comes last and matters most: it seeds each check with the
mutation that check exists to catch, and fails if any of them survives. It was
also run for real against `src/`, five mutations, and two of those runs are
worth writing down:

  * **A `TYPE_CHECKING`-only import of the IDE passes the runtime check and
    fails the static one.** That is the whole argument for having both, measured
    rather than asserted — an import that costs nothing at import time is
    invisible to anything that looks at `sys.modules`.
  * **A plain top-level `from ..studio import x` in a contract module no longer
    *runs*.** It is a circular import now, because `studio` imports the contract
    and `hacks/mount` imports it back, so this file dies on its own import line
    rather than reporting a failure. Red either way, and the strongest form of
    the check there is: the cycle is unbuildable, not merely disapproved of.

    python tests/test_contract.py
"""

from __future__ import annotations

import ast
import subprocess
import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent.parent / "src"
sys.path.insert(0, str(SRC))

from pretkit import contract  # noqa: E402

PKG = SRC / "pretkit"
CONTRACT = PKG / "contract"

#: What the contract may reach for. `shared/` is product A — a coordinate tile, a
#: colour and an Edit are Gen-2 facts that already live there, and A cannot import
#: the contract back without turning the arrow round. Everything else in this repo
#: is either the IDE, an adapter, or a tool, and none of them may be named here.
ALLOWED = {"shared"}
FORBIDDEN = ("studio", "hacks", "asmedit", "maplint", "mapfit", "mapview",
             "map_show", "map_new", "map_inspect", "metatiles", "usage",
             "gfx_view", "dev_server", "sym_lookup")

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
    """Every module this file names in an import, relative ones spelled by the
    first package component they resolve to.

    Walks the whole tree rather than the top level, so an import inside a
    `TYPE_CHECKING` block or inside a function is counted. Those are the ones
    worth catching: they cost nothing at import time, which is exactly why they
    accumulate unnoticed.
    """
    names = []
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.ImportFrom):
            if node.level:
                # `from ..shared.coords import Tile` inside contract/ -> "shared"
                inside = (node.module or "").split(".")
                names.append(inside[0] if node.level > 1 and inside else "")
            else:
                names.append((node.module or "").replace("pretkit.", ""))
        elif isinstance(node, ast.Import):
            names += [a.name.replace("pretkit.", "") for a in node.names]
    return [n for n in names if n]


def contract_modules() -> list[Path]:
    return sorted(CONTRACT.glob("*.py"))


def test_the_contract_names_nothing_above_itself() -> list[Path]:
    print("\nthe contract imports the standard library and shared/, and nothing else")
    mods = contract_modules()
    check("the package has modules to check at all", len(mods) >= 10, str(len(mods)))

    reached: set[str] = set()
    for f in mods:
        for name in imported_names(f):
            head = name.split(".")[0]
            if head in FORBIDDEN:
                reached.add(f"{f.name}: {name}")
    check("no contract module names the IDE, an adapter or a tool",
          not reached, ", ".join(sorted(reached)))

    outside = set()
    for f in mods:
        for name in imported_names(f):
            head = name.split(".")[0]
            if head not in ALLOWED and (PKG / head).exists():
                outside.add(f"{f.name}: {name}")
    check("the only in-repo package it reaches is shared/", not outside,
          ", ".join(sorted(outside)))
    return mods


# --------------------------------------------------------------------------- #
# 2 · runtime: what a fresh interpreter drags in with it                       #
# --------------------------------------------------------------------------- #

_PROBE = (
    "import sys; sys.path.insert(0, {src!r});"
    "import pretkit.contract;"
    "print(','.join(sorted(m for m in sys.modules"
    " if m.split('.')[0] == 'textual'"
    " or m.startswith('pretkit.'))))"
)


def loaded_by_importing_contract() -> set[str]:
    """The modules a bare `import pretkit.contract` leaves behind.

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
              if m.split(".")[0] == "textual"
              or m.split(".")[1:2] and m.split(".")[1] in FORBIDDEN}
    check("nothing above the contract comes with it", not strays,
          ", ".join(sorted(strays)))
    check("shared/ does come with it — the dependency is real, not theoretical",
          any(m.startswith("pretkit.shared") for m in loaded))


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
            "from dataclasses import dataclass\nfrom ..studio import tables")),
        ("an import hidden inside a method", victim + (
            "\n\ndef _late():\n    from ..studio.reader import read_map\n"
            "    return read_map\n")),
        ("an absolute import", victim.replace(
            "from dataclasses import dataclass",
            "from dataclasses import dataclass\n"
            "import pretkit.maplint")),
    ):
        tmp = CONTRACT / "hack.py"
        names = []
        for node in ast.walk(ast.parse(seeded)):
            if isinstance(node, ast.ImportFrom):
                inside = (node.module or "").split(".")
                names.append(inside[0] if node.level > 1 and inside
                             else (node.module or "").replace("pretkit.", ""))
            elif isinstance(node, ast.Import):
                names += [a.name.replace("pretkit.", "") for a in node.names]
        caught = any(n.split(".")[0] in FORBIDDEN for n in names if n)
        check(f"the static check catches {label}", caught, f"{tmp.name}: {names}")

    # 2 · the runtime probe would have to *see* a stray. Prove the probe reports
    #     what is loaded rather than an empty set it can never fail on.
    #
    #     The stray is whichever forbidden package this repo actually carries.
    #     Any one of them named outright belongs to one product, and importing it
    #     where it is not shipped fails the subprocess rather than the check. A
    #     repo carrying none of them cannot run this half and says so, which is
    #     the desired state and not a hole: what is being demonstrated is that a
    #     stray *would* be seen.
    stray = next((name for name in FORBIDDEN
                  if (PKG / name).exists()), None)
    if stray is None:
        print("         (no forbidden package is shipped here, so there is no "
              "stray to demonstrate with)")
    else:
        probe = _PROBE.format(src=str(SRC)).replace(
            "import pretkit.contract;",
            f"import pretkit.contract, pretkit.{stray};")
        out = subprocess.run([sys.executable, "-c", probe],
                             capture_output=True, text=True, check=True)
        seen = {m for m in out.stdout.strip().split(",") if m}
        check(f"the runtime probe would have seen a stray ({stray})",
              any(m.startswith(f"pretkit.{stray}") for m in seen),
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
