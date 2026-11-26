# Writing an adapter

This guide shows you how to teach [Crystal Studio](https://github.com/ricccec/crystal-studio) your own hack repo. For an overview of the API, and of its protocols and records, see the [README](../README.md#whats-in-the-api).

## Do you need one?

Probably not, if your hack started from pokecrystal or Polished Crystal and still lays out its maps the same way. 
Open your repo in Crystal Studio first. You need your own adapter only when:

- Crystal Studio refuses the repo, and its message says what each adapter looked for and didn't find;
- or it opens the repo, but marks some maps as unreadable, with the reason.

> **One catch:** if you wrote a custom adapter but your repo still passes vanilla's or polished's check, Crystal Studio refuses to open the repo because it doesn't know how to choose between two adapters. Today the only way around it is to load yours with [`--hack-path`](#trying-it-without-reinstalling) from a directory named `vanilla` or `polished`: an adapter loaded that way takes its name from the directory, and replaces the `vanilla` or `polished` adapter that ships with Crystal Studio.

If you do need one, **an adapter is just an ordinary Python distribution**. It needs three things.

## 1. An entry point

```toml
# pyproject.toml
[project]
dependencies = ["crystal-studio-api"]

[project.entry-points."crystal_studio.plugins"]
mygame = "mygame.claim"
```

The group name `crystal_studio.plugins` must be spelled exactly like this. Installing the distribution is what registers the adapter.

## 2. A `claims(root)` function

The module the entry point names exposes `claims(root)`. Given the root of a hack repo, it returns:

- a `Hack`, when it recognizes the repo as its own;
- a `NearMiss`, when it doesn't, with the reason in its own words;
- `None`, to say nothing at all.

```python
# mygame/claim.py
from pathlib import Path

from crystal_studio_api import Hack
from crystal_studio_api.mount import NearMiss

from mygame.read import Reader


def claims(root: Path) -> Hack | NearMiss | None:
    if not (root / "mygame.asm").is_file():
        return NearMiss("mygame", "looks for mygame.asm at the root; there is none")
    reader: Reader = Reader(root)
    return Hack("mygame", reader)
```

Recognition is inverted on purpose. Each hack answers for itself, and the mount only counts the answers:

- **One claim:** the repo opens with that adapter.
- **None:** the IDE refuses with an `UnknownTree` that lists every near-miss, so the person sees what each adapter looked for.
- **Two or more:** the mount refuses rather than pick one (see the catch above).

An adapter that raises inside `claims` is reported as a near-miss. It can't take discovery down for the others.

## 3. A reader

`Reads` is the one required capability. A reader is a plain class: the protocols are structural, so nothing needs to inherit from them.

```python
# mygame/read.py
from pathlib import Path

from crystal_studio_api import (Attributes, Blocks, Link, MapTables, Roof,
                                TextRef, Unreadable, WildMon)


class Reader:
    def __init__(self, root: Path) -> None:
        self.root = root

    def maps(self) -> dict[str, str]:
        return {"MyTown": "MY_TOWN"}          # file label -> map constant

    def parses(self, const: str) -> bool:
        return False

    def connections(self, const: str) -> list[Link]:
        return []

    def tables(self, label: str) -> MapTables:
        raise Unreadable(f"{label}: event reading is not written yet")

    def attributes(self, label: str, const: str) -> Attributes:
        return Attributes(label, const, group=0, map_id=0, height=0, width=0)

    def geometry(self, label: str) -> Blocks:
        raise Unreadable(f"{label}: block reading is not written yet")

    def wild(self, const: str) -> dict[str, dict[str, list[WildMon]]]:
        return {}

    def roof(self, const: str) -> Roof | None:
        return None

    def texts(self, label: str) -> list[TextRef]:
        return []
```

This is a skeleton, not a reader: it lists one map and says honestly that it can't read it yet. When a map can't be read, raise `Unreadable` with the reason, and don't return empty tables. The IDE shows the message in place of the tables, but an empty list would claim the map has nothing on it.

Each method's docstring in [`reads.py`](../src/crystal_studio_api/reads.py) says what it must answer.

## Adding capabilities

Pass each extra capability to `Hack` as you write it:

```python
hack: Hack = Hack("mygame", reader, writes=writer, ctx=linter, plays=player, measures=True)
```

`ctx` is the repo's linting context: an object that answers `Lints`, running the hack's own rules. `writes` and `plays` answer `Writes` and `Plays`. `measures=True` promises that `reader` also answers `Measures`.

For complete adapters, read the `claim.py` of the three that exist: [vanilla](https://github.com/ricccec/crystal-studio/blob/main/src/crystal_studio/hacks/vanilla/claim.py), [polished](https://github.com/ricccec/crystal-studio/blob/main/src/crystal_studio/hacks/polished/claim.py) and [prism](https://github.com/ricccec/pokeprism-devtools/blob/main/src/pokeprism_devtools/prism/claim.py).

## Checking your adapter

You can import [`conformance.check_protocol`](../src/crystal_studio_api/conformance.py) to check each part of your adapter against its protocol without Crystal Studio:

```python
from crystal_studio_api import Reads
from crystal_studio_api.conformance import check_protocol

problems = check_protocol(MyReader(root), Reads)
assert not problems, problems
```

It compares **signatures**, not just method names. `isinstance` against a `runtime_checkable` protocol would pass an adapter that renamed a parameter, which then fails at whichever pane asks the question.

Return annotations are deliberately not compared; the [module docstring](../src/crystal_studio_api/conformance.py) says why. Check the returned records by calling the methods on a real repo.

## Trying it without reinstalling

```bash
crystal-studio --root path/to/your/repo --hack-path path/to/mygame
```

`--hack-path` loads a `claim.py` (or the directory holding one) next to the installed adapters, and replaces an installed adapter that has the same name. A file loaded this way has no package around it, so its imports must be absolute (`from mygame.read import …`, not `from .read import …`), and `mygame` must be importable.
