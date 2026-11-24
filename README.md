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
pip install git+https://github.com/ricccec/pret-toolkit \
            git+https://github.com/ricccec/crystal-studio-plugin-api
```

Not on PyPI yet. Every dependency in this family is named by URL in the
same command, which is how pip finds the ones PyPI does not have.

Requires Python 3.11 or newer. Its only dependency is `pret-toolkit`.

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
pret-test               # the whole suite, against the pinned game trees
pret-test --worktree    # the same, against your own checkouts, edits and all
```

Plain scripts, not pytest: each prints `ok`/`FAIL` lines and exits non-zero.
`pret-test` ships with `pret-toolkit`, so it is on `$PATH` once this repo is
installed; run it from anywhere inside the repo.

The protocol half runs anywhere. The half that mounts real game trees reads
the pinned ones, and finds no plugin for them unless an adapter is installed
alongside.
Each tree is pinned to the one commit the tests were written against, in
`pyproject.toml` under `[tool.pret-test.upstreams]`:

- `pokecrystal` — [pret/pokecrystal](https://github.com/pret/pokecrystal) at `31880ea`

`pret-test` checks out a clean copy of each pinned commit into
`~/.cache/pretkit/` — taken from your own checkout when it has the commit, from
the URL otherwise — so neither your edits nor your branch change the result.
Your checkout is found the way every command here finds one: `$<NAME>_TREE`
(`$POKECRYSTAL_TREE`, say), or a conventional place such as `~/code/<name>`.
`pret-test --fetch` fetches them and prints where they are. The copies hold no
build output, so checks that need a ROM skip until you run `make` in one. A
skipped check is counted and reported rather than passed, and `--strict` fails
the run on one.

`--worktree` is for seeing what your own edits do. A test that fails there
because of an edit in *your* tree is a fact about your checkout: record it in
`.known-red.json`, which is git-ignored and counts only in `--worktree` runs.

## Disclaimer

Not affiliated with or endorsed by Nintendo, Game Freak, Creatures or The
Pokémon Company. Pokémon is a trademark of Nintendo.

## Licence

MIT. See `LICENSE`.
