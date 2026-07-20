# Tier 3 (sketch): a local-LLM assist layer for `valuez`

> **Status: proposal / not implemented.** This document specifies a *suggestion-only*
> extraction tier that would sit on top of the Tier-1 [`Reading`](../valuez/reading.py)
> session. Nothing here adds a runtime dependency yet; it exists so the contract
> (schema, prompt, review flow, guardrails) is agreed before any code is written.

## Why a separate tier, and why suggestion-only

The value proposition of `valuez` is **ground-truthing and traceability**: every
node and edge can be traced to a source. An LLM that silently writes edges into
the graph would directly undermine that — an unattributed hallucination is
exactly the thing the framework exists to prevent.

So the automation boundary is deliberate:

- **Tier 1 automates mechanics** (ids, de-duplication, reference propagation,
  eager validation). No judgment is involved, so it can be fully automatic.
- **Tier 3 automates *drafting*, never *committing*.** The model reads a passage
  and proposes *candidate* concepts/relations/claims. A human accepts, edits, or
  rejects each one. Only accepted items enter the session — and they enter through
  the same validated `Reading` API as hand-authored content, carrying a reference
  whose locator is the cited span and whose metadata records the extractor.

This makes the LLM an accelerator for the honest workflow rather than a
replacement for the judgment that makes the map trustworthy.

## Architecture

```
          passage text + schema + controlled vocabulary
                            │
                            ▼
                 ┌─────────────────────┐
   ollama  ◀────▶│  valuez.assist      │   (optional module, optional dep)
 (local model)   │  extract_candidates │
                 └─────────────────────┘
                            │  Candidate[] (JSON, schema-validated)
                            ▼
                 ┌─────────────────────┐
                 │  human review        │   accept / edit / reject  (CLI/notebook)
                 └─────────────────────┘
                            │  accepted candidates
                            ▼
                 ┌─────────────────────┐
                 │  Reading (Tier 1)    │   eager validation, provenance, ids
                 └─────────────────────┘
```

The extractor is isolated in an **optional** module (mirroring how
`valuez/units.py` degrades gracefully when `pint` is absent, and how the RumbleDB
path in `dots` is optional): importing `valuez` never requires an LLM, and the
assist API raises a clear, actionable error if `ollama`/`httpx` or a running
model is unavailable.

## The candidate schema (contract)

The model is required to return a single JSON object matching this shape. Every
item cites the exact character span it was drawn from, so provenance is
mechanical rather than trusted.

```json
{
  "concepts": [
    {"name": "Space", "type": "universal",
     "definition": "Pure a priori form of outer intuition.",
     "ontological_status": "transcendental", "span": [1200, 1265]}
  ],
  "relations": [
    {"source": "Space", "predicate": "is-form-of", "target": "Intuition",
     "modality": null, "strength": 0.9, "span": [1266, 1330]}
  ],
  "claims": [
    {"statement": "Space and time are pure a priori forms of intuition.",
     "truth_value": true, "span": [1200, 1330]}
  ]
}
```

Field rules enforced by a JSON-schema validator *before* anything reaches the
review step:

- `type` ∈ {`concept`, `individual`, `universal`}.
- `predicate` **must** be a member of the caller-supplied controlled
  `Vocabulary` — the same one the `Reading` session validates against. The list
  of allowed predicates is injected into the prompt; any other value is dropped
  and surfaced as a review warning.
- `span` is `[start, end]` character offsets into the *provided passage*; the
  extractor verifies the span resolves to real text and attaches the quoted
  substring to the candidate.
- `strength` ∈ `[0, 1]` or `null`; `truth_value` is a bool or `null`.
- Unknown fields are rejected; unresolvable spans downgrade the candidate to
  "needs manual citation".

## The prompt contract

A strict, low-temperature system prompt keeps output inside the schema and the
vocabulary. Sketch:

```
You are an ontology extraction assistant for the valuez framework.
You will be given (a) a passage of text and (b) the ONLY relation predicates
you may use: {predicates}.

Extract concepts, relations, and claims that are EXPLICITLY supported by the
passage. Do NOT infer beyond the text. Do NOT invent predicates. If unsure,
omit the item.

For every item, include "span": [start, end] character offsets into the passage
delimiting the exact text that supports it.

Return ONLY a JSON object with keys "concepts", "relations", "claims" matching
the given schema. No prose.

PASSAGE (offsets are 0-based into this string):
<<<
{passage}
>>>
```

Recommended call settings: `temperature≈0`, `format="json"` (ollama's structured
mode), a modest `num_ctx`, and a capable local instruct model
(e.g. `llama3.1`, `qwen2.5`, `mistral`). The model name is a caller argument, not
a default, so the choice stays explicit.

## Proposed API (not yet implemented)

```python
from valuez import Reading, Vocabulary
from valuez.assist import extract_candidates, OllamaClient   # optional module

book = Reading(source="Critique of Pure Reason", predicates=PREDICATES)

passage = load_passage("cpr.txt", 1200, 1330)
candidates = extract_candidates(
    passage,
    predicates=PREDICATES,          # constrains the model + validates output
    client=OllamaClient(model="llama3.1"),
    base_offset=1200,               # so spans map back into the whole text
)

for c in candidates:                 # human-in-the-loop review
    if review(c):                    # accept / edit / reject (CLI or notebook)
        c.apply(book, reviewed_by="acj")   # routes through the Tier-1 session
```

`Candidate.apply(book, ...)` is the only path into the graph. It calls
`book.universal(...)` / `book.relate(...)` / `book.claim(...)` under a
`book.at(locator=span_citation, source=..., confidence=strength, metadata={...})`
context, so accepted items are **indistinguishable in kind** from hand-authored
ones — same validation, same ids, same provenance — except that their reference
metadata records the origin:

```json
{
  "source": "Critique of Pure Reason",
  "locator": "chars 1266-1330",
  "confidence": 0.9,
  "metadata": {
    "extractor": "ollama:llama3.1",
    "reviewed_by": "acj",
    "quote": "space is nothing other than merely the form of ...",
    "candidate_status": "accepted"
  }
}
```

## Guardrails (summary)

1. **Suggestion-only.** No candidate is ever auto-committed; the review step is
   mandatory and the default answer is "reject".
2. **Constrained predicates.** The controlled `Vocabulary` bounds the relation
   space both in the prompt and in post-validation.
3. **Schema-validated output.** Malformed or over-reaching JSON is discarded, not
   coerced.
4. **Mandatory span citations.** Every accepted item points back into the real
   text; items whose spans don't resolve are flagged for manual citation.
5. **De-duplication for free.** Candidates flow through the Tier-1 create-or-reuse
   logic, so re-extracting an already-known concept merges rather than duplicates.
6. **Attribution in metadata.** `extractor`, `reviewed_by`, and the quoted span
   are recorded, so an LLM-assisted map remains auditable and can be filtered
   (e.g. "show only human-authored edges").
7. **Optional dependency.** The assist module never loads at `import valuez`
   time and fails loudly with install/run guidance when the model is missing.

## Explicitly out of scope for the first cut

- No autonomous multi-passage "read the whole book" agent loop.
- No fine-tuning; rely on prompt + schema + a general instruct model.
- No writing back into `ontologies/*.json` without the human review gate.
- No remote/hosted LLM providers — local ollama only, to keep authored ontologies
  private and reproducible.
