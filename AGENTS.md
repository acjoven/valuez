# AGENTS.md

## Cursor Cloud specific instructions

`valuez` is a pure-Python **library** (no web server / long-running service) for
traceable semantic exploration. It is built on the sibling toolkit in `../dots`
(storage / query / graph) and adds a typed value system (`Scalar`/`Range`,
qualitative primitives, `Concept`/`Relation`, `Individual`/`Universal`,
`DataSet`/`Function`), a fluent `Reading` authoring session, BibTeX-backed
`ReferenceRepository`, and committed ontology maps under `ontologies/`. See
`README.md` for the full API tour and `examples/README.md` for runnable demos.

Dependencies install into a gitignored virtualenv at `.venv`. The committed
bootstrap script [`scripts/setup_env.sh`](scripts/setup_env.sh) (re)creates it and
is wired into [`.cursor/environment.json`](.cursor/environment.json) as both the
`install` step (full build-time setup) and the `start` step (`ensure` mode, a
fast per-boot self-heal that rebuilds `.venv` only if it is missing/broken). Call
binaries directly, e.g. `.venv/bin/python -m pytest`. To rebuild by hand after a
fresh VM wipes `.venv`, run `bash scripts/setup_env.sh`.

> Cursor Cloud note: this repo-file `.cursor/environment.json` is honored when the
> environment includes the `valuez` repo. Because `valuez` needs its sibling
> `dots` checkout, add **both** repos to the environment (they are cloned as
> siblings, so `../dots` resolves); otherwise set `DOTS_DIR` to the `dots`
> checkout for `setup_env.sh` to find it.

### Non-obvious gotcha: `dots` vs `dotz`

`valuez` imports the sibling toolkit as **`dots`** (e.g.
`from dots.storage import JsonStorage` in `valuez/repository.py`, and
`import dots.graph` in the ontology examples), but the sibling repo `../dots`
now **packages it as `dotz`** (the package was renamed `dots` -> `dotz`). With
nothing bridging them, `valuez.repository` and ~7 test modules fail with
`ModuleNotFoundError: No module named 'dots'`.

`scripts/setup_env.sh` bridges this by writing a tiny venv-level alias file
(`zz_dots_to_dotz_compat.pth` in site-packages) that maps `dots` -> `dotz`.
Because that alias lives in the venv (not tracked in git), it must be recreated
whenever the venv is rebuilt — which the script handles (and its `ensure` mode
verifies on each boot). If you ever see the `No module named 'dots'` error,
re-run `bash scripts/setup_env.sh`. The proper long-term fix is to update
`valuez`'s imports to `dotz` (or commit a real `dots` shim), but that has not
been done yet.

Also keep `click<8.2`: `typer==0.12.5` (used by the `dotz` CLI extra) is
incompatible with `click>=8.2`.

### Running / testing
- Tests: `.venv/bin/python -m pytest` (all suites live in `tests/`).
- Lint: no linter is configured. For a syntax sanity check use
  `.venv/bin/python -m py_compile valuez/*.py examples/*.py tests/*.py`.
- Examples: `.venv/bin/python examples/<name>.py`. Each writes rendered graphs
  and/or exports to `$VALUEZ_EXAMPLE_OUT` (defaults to a per-example folder in
  the temp dir). No external services are needed.
- Rendering note: `pyvis` drops a `lib/` asset folder into the *current working
  directory*; the examples `chdir` into their output dir to contain it, and
  `lib/` is gitignored.

### Ontologies convention
Canonical ontology maps are committed as single JSON arrays under `ontologies/`
(e.g. `kant.json`, `kierkegaard.json`), produced by
`ValueRepository.export_ontology(...)` and reloaded with
`ValueRepository.from_ontology(...)`. Edit the builder script under `examples/`,
re-run it, and commit the regenerated JSON. See `ontologies/README.md`.
