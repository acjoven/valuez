# Tier 4 (sketch): interoperability / standards export

> **Status: proposal / not implemented.** This document specifies an
> *interoperability* layer that would let `valuez` ontologies flow into (and back
> from) the wider structured-knowledge ecosystem — RDF/OWL, SKOS, W3C PROV, and
> nanopublications — plus richer bibliographic exchange. Nothing here adds a
> runtime dependency yet; it exists so the mappings and principles are agreed
> before any code is written. It complements the authoring tiers (see
> [`docs/llm_assist.md`](llm_assist.md) for Tier 3).

## Why

`valuez` deliberately occupies an underserved middle ground: **small,
hand-curated, rigorously ground-truthed ontologies.** That is valuable on its
own, but the payoff multiplies if those ontologies can be *published* into, and
*seeded* from, the standards that the rest of the field already speaks. Concretely:

- **Reuse, don't reinvent.** RDF/OWL, SKOS, and PROV already formalize exactly
  the structures `valuez` models (typed edges, controlled vocabularies,
  provenance). Emitting them makes a `valuez` map queryable with SPARQL, loadable
  into Protégé / GraphDB / Wikibase, and linkable to external identifiers.
- **Provenance is the differentiator.** `valuez`'s first-class `Reference` maps
  almost directly onto **W3C PROV** and **nanopublications**, so we can publish
  assertions that stay independently citable and auditable.
- **Round-tripping.** Importing RDF/JSON-LD lets a `valuez` session *start* from
  an existing ontology rather than a blank page.

The guiding principle mirrors the rest of the project: **prefer standard
vocabularies where they exist; fall back to a `valuez` namespace only for
concepts the standards can't express, and never silently drop information.**

## Architecture

```
   valuez values (Concept/Relation/Proposition/Argument/Reference/Vocabulary)
                              │
                              ▼
                 ┌─────────────────────────┐
   rdflib  ◀────▶│  valuez.interop         │   (optional module, optional dep)
  (RDF core)     │  to_rdf / from_rdf      │
                 │  to_skos / to_prov      │
                 │  to_nanopubs            │
                 └─────────────────────────┘
                    │            │            │
                    ▼            ▼            ▼
             Turtle/JSON-LD   SKOS graph   nanopublication set
             (OWL individuals  (vocabularies) (assertion+provenance+pubinfo)
              & classes)
```

The layer would live in an **optional** `valuez.interop` module built on
[`rdflib`](https://rdflib.dev/) (the de-facto Python RDF library), following the
exact graceful-degradation pattern already used for `pint` (`valuez.units`) and
`pybtex` (`valuez.bibliography`): importing `valuez` never requires `rdflib`, and
only the export/import functions raise an actionable error when it is absent.

## IRI strategy

Everything hinges on stable IRIs:

- A configurable **base namespace**, e.g. `https://example.org/valuez/<ontology>#`,
  with each node's IRI minted from its existing `id` (the deterministic,
  prefixed ids from `Reading` are ideal for this).
- **Reuse standard vocabularies** for predicates and types wherever possible
  (`rdf`, `rdfs`, `owl`, `skos`, `prov`, `dcterms`, `schema.org`).
- A small **`valuez:` namespace** for the handful of predicates and fields with
  no clean standard equivalent (e.g. `contrasts-with`, `grounds`, edge
  `strength`/`modality`, `Argument` scheme), so nothing is lost on export.

## Mapping: valuez → standards

| valuez | RDF / OWL / … | Notes |
| --- | --- | --- |
| `Concept` | `owl:Class` or `skos:Concept` | Class in the OWL view; concept in the SKOS view. |
| `Individual` | `owl:NamedIndividual` | A particular. |
| `Universal` | `owl:Class` | A kind/property. |
| `Instantiation` (`instantiates`) | `rdf:type` | Individual → Universal. |
| `Relation` `is-a` | `rdfs:subClassOf` | Between universals. |
| `Relation` `part-of` | `dcterms:isPartOf` / a `valuez:` property | Mereology; PROV/OWL have no single canonical part-of. |
| `Relation` `grounds`, `contrasts-with`, … | `valuez:` properties | Non-standard predicates keep a `valuez` IRI. |
| `Relation` `modality`/`strength` | reified statement + `valuez:` annotations | Needs RDF reification or RDF-star to attach edge metadata. |
| `Concept.definition` | `skos:definition` / `rdfs:comment` | |
| `Vocabulary` | `skos:ConceptScheme` | terms → `skos:Concept` + `skos:inScheme`. |
| `Vocabulary` (ordered) / `Ordinal` | `skos:broader` chain or `owl:Ordinal` pattern | Encodes the ranking. |
| `Proposition` | `rdf:Statement` / nanopub assertion | Reified, truth-apt claim. |
| `Argument` | AIF / `valuez:` premises→conclusion | Optionally the Argument Interchange Format. |
| `Reference` | `prov:Entity` + `prov:wasDerivedFrom` / `prov:wasAttributedTo` | The provenance backbone. |
| `Reference` (bib fields) | BIBFRAME / `dcterms` / CSL-JSON | Complements the existing BibTeX export. |

## Proposed API (not yet implemented)

```python
from valuez import Reading
from valuez.interop import to_rdf, to_jsonld, to_skos, to_prov, to_nanopubs, from_rdf

book = Reading(source="Critique of Pure Reason", id_prefix="cpr_")
# ... build the ontology ...

turtle = to_rdf(book.values(), format="turtle", base="https://ex.org/kant#")
jsonld = to_jsonld(book.values(), base="https://ex.org/kant#")
skos   = to_skos(PREDICATES)                    # a Vocabulary → SKOS scheme
prov   = to_prov(book.values())                 # References → PROV-O graph
nanos  = to_nanopubs(book.relations, base=...)  # each grounded edge → a nanopub

# round-trip: seed a session from existing RDF
values = from_rdf("external_ontology.ttl", base="https://ex.org/kant#")
```

Each function returns an `rdflib.Graph` (or serialized string), so downstream
users can merge, query with SPARQL, or persist to a triple store.

## Nanopublications (the closest kin)

A [nanopublication](https://nanopub.net/) bundles three named graphs: the
**assertion**, its **provenance**, and **publication info**. That is almost
exactly a grounded `valuez` edge:

- *assertion graph* ← the `Relation`/`Proposition` as a triple,
- *provenance graph* ← its `Reference` mapped to PROV-O,
- *pubinfo graph* ← who/when generated the nanopub (creation metadata).

This would let each individually ground-truthed assertion become a first-class,
citable unit — a natural culmination of the ground-truthing goal.

## Bibliographic interchange (extends Tier-3 of the bibliography work)

The existing `ReferenceRepository` already does BibTeX I/O via `pybtex`. Tier 4
would add:

- **CSL-JSON** export and **styled** citations via `citeproc-py` (the deferred
  APA/Chicago/etc. formatting), and
- optional **BIBFRAME** (linked-data bibliographic) output for library-world
  interoperability.

## Guardrails / principles

1. **Lossless where possible.** Round-trip `valuez → RDF → valuez` should
   preserve ids, labels, references, and edge metadata; anything without a
   standard term is kept under the `valuez:` namespace rather than dropped.
2. **Reuse before invent.** Standard vocabularies (rdf/rdfs/owl/skos/prov/dcterms)
   take priority; `valuez:` is the fallback.
3. **Stable, configurable IRIs.** Derived from existing ids under a caller-set
   base namespace.
4. **Provenance preserved.** Every exported assertion keeps its `Reference` via
   PROV-O (or a nanopub provenance graph).
5. **Optional dependency.** `rdflib` (and `citeproc-py` for CSL) never load at
   `import valuez` time and fail loudly with install guidance when missing.
6. **No semantics we can't back.** Export the structures we actually model; do
   **not** claim a particular OWL DL profile or run a reasoner as part of export
   (leave OWL reasoning to downstream tools like Protégé / a DL reasoner).

## Explicitly out of scope for the first cut

- A hosted SPARQL endpoint or live triple-store synchronization.
- OWL reasoning / DL-profile guarantees (delegate to external reasoners).
- Full RDF-star adoption for edge metadata if `rdflib` support is immature —
  start with standard reification.
- Automatic IRI minting against external authorities (Wikidata/DBpedia linking)
  — leave entity linking to a later pass.
