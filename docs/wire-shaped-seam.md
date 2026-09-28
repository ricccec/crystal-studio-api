# The seam is already wire-shaped — and the five things that are not

**Measured 2026-09-28.** Not scheduled, and deliberately not built. This exists so
the next person to ask *"could a non-Python client drive this?"* does not have to
re-derive the answer, and so nobody accidentally closes the door.

## The question

`crystal-studio` is a Python TUI. `crystal-studio-desktop` is Electron, so JavaScript.
Nothing bridges those in-process. The options are to reimplement product A in
TypeScript — duplicating `overworld/`, `lz.py` and `coords.py`, which is the worst
code in the repo to have two copies of — or to put a process boundary in and speak a
protocol across it.

The second is only cheap if the seam's *information model* is already free of live
Python objects. It is.

## What already crosses

**Every request argument is a string.** `Action.__init__(**values: str)`, and every
method on the `Reads` protocol takes `str` parameters:

    maps() -> dict[str, str]              parses(const: str) -> bool
    connections(const: str) -> list[Link] tables(label: str) -> MapTables
    attributes(label, const) -> Attributes    geometry(label) -> Blocks
    wild(const) -> dict[str, dict[str, list[WildMon]]]
    roof(const) -> Roof | None            texts(label) -> list[TextRef]
    measure(text, box) -> TextPreview

**Every response is a record tree.** Walked with `dataclasses.fields` over the whole
vocabulary: `Link`, `Attributes`, `WildMon`, `Roof`, `TextRef` and `Field` are
dataclasses of primitives outright. `MapTables`, `Blocks`, `TextPreview`, `Result` and
`Diagnostic` nest only further dataclasses or an enum — `Npc`, `Warp`, `Swatch`,
`Measured`, `Edit`, `Severity`. **No callables, no file handles, no live objects
anywhere in the returned shapes.**

**Writes are already pure, and already previewable.** `shared/edits.py`: *"An editor
never writes as a side effect. It returns a full-file-text Edit that the caller can
diff (dry run), stack with other edits, and apply in one go."* A remote client can ask
for a diff, show it to a human, and commit separately — which is the same code path the
TUI uses, so the preview stays a rehearsal rather than a model of one.

**And B was written for an opaque client.** `contract/action.py` says so:
*"Each action declares its fields, so an IDE builds its own form and its own
autocomplete from that declaration and knows nothing about NPCs or connections."*
`fields_for(values: dict[str, str]) -> tuple[Field, ...]` is already a request/response
pair. The Python `Protocol` classes are a **binding**, not the design.

## The five things that are not

1. **`Ref.handle: Hashable | None`** — the only non-serialisable field in the
   vocabulary, and it is *deliberately* opaque: the adapter mints it, the view carries
   it without looking, the adapter resolves it. That is exactly the shape a wire
   protocol wants, but it needs a server-side handle table, and **handles have to be
   invalidated when the tree changes** or a client holds a pointer at something that
   moved. This is the real engineering, and it is the only item here that is a design
   problem rather than a mechanical one.
2. **`Hack.ctx` is a live `LintContext` with caches.** That makes this a *server with
   sessions*, not stateless RPC — and it is also the only reason it would be fast
   enough to use.
3. **An `Edit` carries the whole file text twice** (`new_text` and `base`, the second
   for the staleness check). Free in-process. Over a socket, a message per edit
   containing an entire `.asm` file is not, so edits stay server-side and the wire
   carries ids plus diffs.
4. **`sketch(action)` takes a live `Action`** — the one signature in the seam that
   passes an object rather than data. It becomes `sketch(name, values)`.
5. **`Edit.data: bytes`** for the files that are not text (a `.blk` is one byte per
   block). Base64, and no more than that.

## Where it would live, and why not yet

**A server would be another consumer of B — a sibling of C, not a layer inside it.**
C drives the seam in-process; an engine would drive it over a socket. Both depend on
A and B and neither needs the other, which the four-product shape already allows
without change.

**Not built, because there is no second client.** A command API whose only consumer is
a Python TUI that does not need one is speculative generality, and Phase 0 measured the
general form of that: *carving early buys the rehearsal, not the repo.* The trigger is
the desktop app actually wanting to read a tree.

**What to do in the meantime is nothing — except not close the door.** Keep the seam's
arguments stringly-typed, keep its returns as records, and keep writes returning an
`Edit` rather than performing one. All three are already house rules for other reasons,
which is why this stayed possible without anyone aiming at it.
