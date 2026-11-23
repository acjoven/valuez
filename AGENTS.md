# AGENTS.md

## Cursor Cloud specific instructions

`valuez` is a pure-Python **library** (no web server / long-running service) for
traceable semantic exploration. It is built on the sibling toolkit `dotz`
(storage / query / graph) and adds a typed value system (`Scalar`/`Range`,
qualitative primitives, `Concept`/`Relation`, `Individual`/`Universal`,
`DataSet`/`Function`), a fluent `Reading` authoring session, BibTeX-backed
`ReferenceRepository`, and committed ontology maps under `ontologies/`. See
`README.md` for the overview, `docs/tour.md` for the full API tour, and
`examples/README.md` for runnable demos.

Dependencies install into a gitignored virtualenv at `.venv`. The committed
bootstrap script [`scripts/setup_env.sh`](scripts/setup_env.sh) (re)creates it and
is wired into [`.cursor/environment.json`](.cursor/environment.json) as both the
`install` step (full build-time setup) and the `start` step (`ensure` mode, a
fast per-boot self-heal that rebuilds `.venv` only if it is missing/broken). Call
binaries directly, e.g. `.venv/bin/python -m pytest`. To rebuild by hand after a
fresh VM wipes `.venv`, run `bash scripts/setup_env.sh`.

> Cursor Cloud note: this repo-file `.cursor/environment.json` is honored when the
> environment includes the `valuez` repo. Because `valuez` imports the sibling
> `dotz` toolkit, add **both** repos to the environment (they are cloned as
> siblings, so `../dotz` resolves; a legacy `../dots` clone dir also works);
> otherwise set `DOTZ_DIR` to the `dotz` checkout for `setup_env.sh` to find it.

### Dependency: the sibling `dotz` toolkit

`valuez` imports the sibling toolkit directly as **`dotz`** (e.g.
`from dotz.storage import JsonStorage` in `valuez/repository.py`, and
`import dotz.graph` in the ontology examples). `scripts/setup_env.sh` installs it
editable from the sibling checkout, so `valuez.repository` and the graph-rendering
examples work out of the box. If you see `ModuleNotFoundError: No module named
'dotz'`, the sibling repo was not found — re-run `bash scripts/setup_env.sh` (set
`DOTZ_DIR` if the checkout is not a sibling of this repo).

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
