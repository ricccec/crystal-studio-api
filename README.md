# crystal-studio-plugin-api

Write a [Crystal Studio](https://github.com/ricccec/crystal-studio) plugin for
your own Pokémon Gen-2 hack.

Crystal Studio is a terminal IDE for pret/RGBDS disassemblies. It ships adapters
for pokecrystal and Polished Crystal; this package is what you implement to teach
it a *third* tree — yours — without forking it or patching it.

## What is in here

The noun list and the question list, and nothing else. Nothing in this package
parses a file, opens one, or draws anything: it exists to be *pointed at*, so the
IDE and an adapter depend on it instead of on each other.

- **The nouns** — what a Gen-2 map is made of: the six lists of things standing on
  it, the header and its edges, its shape, its encounters, its dialogue, and the
  opaque handle that names any one of them.
- **The questions** — the capabilities an adapter declares: `Reads`, `Writes`,
  `Lints`, `Plays`.

A capability you do not implement degrades to **absence** on the other side — no
lint panel, no boot key, no edit forms. Never a crash, and never an `if <hack
name>`. The mount point is the only module allowed to know that hacks exist at
all, and it knows them as a registry of names it asks in turn.

It is about 1,400 lines across 17 modules, and the package docstring says to read
it in one sitting. That is the intended size.

## Install

```bash
pip install crystal-studio-plugin-api
```

Requires Python 3.10 or newer. Its only dependency is `pret-toolkit`.

## Registering an adapter

An adapter is an ordinary distribution that advertises one entry point:

```toml
[project.entry-points."crystal_studio.plugins"]
mygame = "mygame.claim"
```

The module it names exposes `claims(root)`, which returns a built adapter when it
recognises the tree, nothing when it does not, or a `NearMiss` carrying a reason.
Recognition is inverted on purpose: each hack answers for itself, and the mount
only counts the answers. The three in-tree adapters register through this exact
path, which is the only way to know the seam works before someone depends on it.

## Checking your adapter

`conformance.py` checks an adapter against the protocols without the IDE in the
room — and compares *signatures*, not just method names, because
`isinstance` against a `runtime_checkable` Protocol passes an adapter that
renamed a parameter and then fails at whichever pane asks third:

```python
from pretkit.contract import Reads
from pretkit.contract.conformance import check_protocol

problems = check_protocol(MyReader(root), Reads)
assert not problems, problems
```

Return annotations are deliberately not compared; the module docstring says why.

## The namespace

The import name is `pretkit`, a [PEP 420][pep420] namespace package shared with
`pret-toolkit` and the other Crystal Studio distributions. This package imports
`pret-toolkit` and nothing above it.

[pep420]: https://peps.python.org/pep-0420/

## Tests

```bash
python scripts/run-tests.py
```

Plain scripts, not pytest. The protocol half runs anywhere; the half that mounts
real game trees skips, and says which tree it wanted, when you have none.

## Licence

MIT. See `LICENSE`.
