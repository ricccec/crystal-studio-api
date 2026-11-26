# crystal-studio-api

**Write a [Crystal Studio](https://github.com/ricccec/crystal-studio) plugin for your own Pokémon Gen-2 hack.**

Crystal Studio is a terminal IDE for [pret](https://github.com/pret)-style disassemblies built with [RGBDS](https://github.com/gbdev/rgbds). This package is the contract between the IDE and a disassembly repo: implement it in an adapter, and the IDE can work with your custom hack codebase without being forked or patched:

```text
                         Crystal Studio
                            (the IDE)
                                │
                                ▼
                       crystal-studio-api
                                ▲
        ┌───────────────┬───────┴───────┬───────────────┐
        │               │               │               │
     vanilla        polished           ...        your adapter
  (pokecrystal)    (Polished)
```

## Installation

```bash
pip install git+https://github.com/ricccec/pret-toolkit \
            git+https://github.com/ricccec/crystal-studio-api
```

**Requirements:** Python 3.11 or newer. The only dependency is [pret-toolkit](https://github.com/ricccec/pret-toolkit).

The package is not on PyPI yet. Naming every dependency by URL in one command is how pip finds the ones PyPI doesn't have.

> **API stability:** the API is not stable before 1.0. Pin a commit when you depend on it.

## What's in the API

The API is deliberately small and self-contained. Its docstrings are the reference, and the [package docstring](src/crystal_studio_api/__init__.py) is the place to start.

The API is built around three parts:
- **The mount** is the API's only runtime component. It allows Crystal Studio to discover installed adapters and select the one that recognizes the hack repo being opened.
- **The protocols** are the capabilities. Each hack adapter implements (some of) them. `Reads` is the one required, the bare minimum for an adapter to be able to claim a repo.
- **The records** are the shared data types. The adapter builds them and Crystal Studio reads them.

### Protocols are the questions: what an adapter can answer

| Capability | Protocol | When it's absent, the IDE has… |
|---|---|---|
| Read the hack repo (**required**) | [`Reads`](src/crystal_studio_api/reads.py): nine questions, from `maps()` to `texts()` | nothing to open |
| Measure text in tiles | [`Measures`](src/crystal_studio_api/reads.py) | no tile ruler under the text box |
| Edit the hack repo | [`Writes`](src/crystal_studio_api/writes.py) | no edit forms: the repo opens read-only |
| Lint the hack repo | [`Lints`](src/crystal_studio_api/lints.py) | no lint panel |
| Build and boot the ROM | [`Plays`](src/crystal_studio_api/plays.py) | no boot key |

### Records are the nouns: what a Gen-2 map is made of

| Module | Records |
|---|---|
| [`events`](src/crystal_studio_api/events.py) | The six lists of things standing on a map: `Npc`, `Trainer`, `Prop`, `Signpost`, `Warp`, `Trigger`, held together in `MapTables` |
| [`attributes`](src/crystal_studio_api/attributes.py) | The header (`Attributes`), its edges (`Link`), and the roof its group loads (`Roof`) |
| [`blocks`](src/crystal_studio_api/blocks.py) | The map's shape (`Blocks`), and a not-yet-created one (`Sketch`) |
| [`wild`](src/crystal_studio_api/wild.py) | Encounters (`WildMon`) |
| [`dialogue`](src/crystal_studio_api/dialogue.py) | The map's text (`TextRef`), and how it measures in tiles (`TextPreview`, `Measured`) |
| [`ref`](src/crystal_studio_api/ref.py) | `Ref`, the opaque handle that names any one of the above |
| [`action`](src/crystal_studio_api/action.py), [`diagnostic`](src/crystal_studio_api/diagnostic.py) | A staged change and the form fields it declares (`Action`, `Field`), and a lint finding (`Diagnostic`) |

> **Missing capabilities degrade to absence:** Each adapter declares what it can do in one [`Hack`](src/crystal_studio_api/hack.py) record. A capability it leaves out is simply **absent** in Crystal Studio: it never crashes the IDE.

## Writing an adapter

An adapter is an ordinary Python distribution. It needs at least these three things:

1. an entry point in the `crystal_studio.plugins` group;
2. a `claims(root)` function that recognizes your hack repo and returns a `Hack`;
3. a reader that answers `Reads`.

[docs/writing-an-adapter.md](docs/writing-an-adapter.md) walks you through the process of building an adapter, with a minimal scaffold you can copy.

## Existing adapters

There are three adapters today, in two distributions:

| Adapter | For | Ships in |
|---|---|---|
| `vanilla` | [pokecrystal](https://github.com/pret/pokecrystal) | [crystal-studio](https://github.com/ricccec/crystal-studio) |
| `polished` | [Polished Crystal](https://github.com/Rangi42/polishedcrystal) | [crystal-studio](https://github.com/ricccec/crystal-studio) |
| `prism` | [Pokémon Prism](https://github.com/ricccec/pokeprism) | [pokeprism-devtools](https://github.com/ricccec/pokeprism-devtools) |

## Tests

Tests use `pret-test`, which comes with [pret-toolkit](https://github.com/ricccec/pret-toolkit).

```bash
pret-test               # the whole suite, against the pinned game repos
pret-test --worktree    # the same, against your own checkouts
```

The tests are plain scripts, not pytest: each prints `ok`/`FAIL` lines and exits non-zero on failure. Go check [pret-toolkit's README](https://github.com/ricccec/pret-toolkit#testing) for more info.

Keep in mind that these tests check the API itself, and every adapter installed alongside it. To check your own adapter from its own tests, see [Checking your adapter](docs/writing-an-adapter.md#checking-your-adapter).

> **One caveat:** some checks need an adapter. This repository ships none, so they find nothing to mount unless [crystal-studio](https://github.com/ricccec/crystal-studio) or another adapter is installed alongside.

## Disclaimer

This project is not affiliated with or endorsed by Nintendo, Game Freak, Creatures, or The Pokémon Company. Pokémon is a trademark of Nintendo.

## License

MIT. See [LICENSE](LICENSE).
