#!/usr/bin/env python3
"""An ontology of Immanuel Kant's critical philosophy, built with valuez.

This is a *content* example: it uses the semantic + metaphysics primitives to
map Kant's system as a traceable, queryable graph spanning the three Critiques:

- **Particulars** (:class:`Individual`) -- Kant and his major works.
- **Universals** (:class:`Universal`) -- the concepts of the system (faculties,
  representations, the table of categories, phenomena/noumena, the moral
  concepts, the aesthetic concepts), each with an ``ontological_status``.
- **Instantiation** -- typed ``Individual --instantiates--> Universal`` edges.
- **Relations** over a controlled predicate vocabulary: ``is-a`` (kind
  subsumption), ``part-of`` (structure of the first Critique), ``contrasts-with``
  (Kant's great dichotomies), ``grounds`` / ``requires`` / ``produces`` /
  ``enables`` / ``presupposes`` / ``applies-to`` / ``addresses`` / ``is-form-of``.
- **Propositions** -- reified, cited theses; and one **Argument** sketching the
  Transcendental Deduction.

It then reasons over the graph (transitive closure of ``is-a``; acyclicity of the
strict orders), persists everything through ``dots``, exports the canonical
``ontologies/kant.json``, and renders an interactive graph.

Run:  python examples/kant_ontology.py
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from valuez import (  # noqa: E402
    Argument,
    Individual,
    Instantiation,
    Proposition,
    Reference,
    Relation,
    Universal,
    Value,
    Vocabulary,
    reasoning,
    visualize_arguments,
    visualize_relations,
)
from valuez.repository import ValueRepository  # noqa: E402

# --------------------------------------------------------------------------- #
# References (sources the ontology is ground-truthed against)                  #
# --------------------------------------------------------------------------- #
CPR = Reference("Kant, Critique of Pure Reason (1781/1787)")
GW = Reference("Kant, Groundwork of the Metaphysics of Morals (1785)")
CPrR = Reference("Kant, Critique of Practical Reason (1788)")
CJ = Reference("Kant, Critique of the Power of Judgment (1790)")
PROL = Reference("Kant, Prolegomena to Any Future Metaphysics (1783)")
SEP = Reference("Stanford Encyclopedia of Philosophy, 'Immanuel Kant'")

# Controlled predicate vocabulary for the (non-instantiation) relations.
PREDICATES = Vocabulary(
    "kantian_relations",
    [
        "is-a", "part-of", "wrote", "instantiates", "contrasts-with", "requires",
        "produces", "grounds", "applies-to", "enables", "presupposes",
        "is-form-of", "addresses",
    ],
    reference=Reference("Framework convention", description="Allowed relation types."),
)


def _slug(name: str) -> str:
    return "k_" + re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()


# --------------------------------------------------------------------------- #
# Individuals (particulars): Kant + works                                      #
# --------------------------------------------------------------------------- #
INDIVIDUALS = [
    ("ImmanuelKant", "Prussian philosopher (1724-1804); founder of critical philosophy.", "historical", SEP),
    ("CritiqueOfPureReason", "Kant's first Critique (1781/1787).", "historical", CPR),
    ("CritiqueOfPracticalReason", "Kant's second Critique (1788).", "historical", CPrR),
    ("CritiqueOfJudgment", "Kant's third Critique (1790).", "historical", CJ),
    ("Groundwork", "Groundwork of the Metaphysics of Morals (1785).", "historical", GW),
    ("Prolegomena", "Prolegomena to Any Future Metaphysics (1783).", "historical", PROL),
]

# --------------------------------------------------------------------------- #
# Universals (kinds/concepts): (name, definition, ontological_status)          #
# --------------------------------------------------------------------------- #
UNIVERSALS = [
    # top kinds used as instantiation targets
    ("Philosopher", "One who practices philosophy.", "abstract"),
    ("PhilosophicalWork", "A work of philosophy.", "abstract"),
    # representations
    ("Representation", "Vorstellung: any mental content.", "transcendental"),
    ("Intuition", "Anschauung: singular, immediate representation via sensibility.", "transcendental"),
    ("Concept", "Begriff: general, mediate representation via the understanding.", "transcendental"),
    ("Category", "Pure concept of the understanding.", "a priori"),
    ("Idea", "Concept of reason to which no experience is adequate.", "transcendental"),
    ("TranscendentalIdea", "Idea of the unconditioned (soul, world, God).", "transcendental"),
    ("Schema", "Transcendental schema mediating category and intuition.", "a priori"),
    # faculties
    ("Faculty", "Vermoegen: a power of the mind.", "transcendental"),
    ("Sensibility", "Faculty of receptivity yielding intuitions.", "transcendental"),
    ("Understanding", "Verstand: faculty of concepts and rules.", "transcendental"),
    ("Reason", "Vernunft: faculty of inference and ideas.", "transcendental"),
    ("TheoreticalReason", "Reason in its cognitive (speculative) use.", "transcendental"),
    ("PracticalReason", "Reason in its moral (legislative) use.", "transcendental"),
    ("Imagination", "Einbildungskraft: faculty of synthesis and schemata.", "transcendental"),
    ("PowerOfJudgment", "Urteilskraft: faculty subsuming particulars under universals.", "transcendental"),
    # cognition / objects
    ("Cognition", "Erkenntnis: objectively valid representation of an object.", "transcendental"),
    ("Experience", "Empirical cognition; the unity of appearances under categories.", "phenomenal"),
    ("Object", "That toward which a representation is directed.", "abstract"),
    ("Appearance", "Phenomenon: object as it appears under space, time, categories.", "phenomenal"),
    ("ThingInItself", "Noumenon: object as it is in itself, independent of cognition.", "noumenal"),
    # forms of intuition
    ("FormOfIntuition", "A priori form structuring sensibility.", "a priori"),
    ("Space", "A priori form of outer intuition.", "a priori"),
    ("Time", "A priori form of inner intuition.", "a priori"),
    # judgments and distinctions
    ("Judgment", "A logical combination of representations in one consciousness.", "abstract"),
    ("AnalyticJudgment", "Predicate is contained in the subject (explicative).", "abstract"),
    ("SyntheticJudgment", "Predicate adds to the subject (ampliative).", "abstract"),
    ("SyntheticAPriori", "Ampliative yet necessary and universal judgment.", "a priori"),
    ("EpistemicDistinction", "A fundamental Kantian contrast.", "abstract"),
    ("APriori", "Independent of experience (necessary, universal).", "a priori"),
    ("APosteriori", "Derived from experience (contingent).", "a posteriori"),
    ("Analytic", "True by containment / conceptual analysis.", "abstract"),
    ("Synthetic", "True by adding content beyond the concept.", "abstract"),
    # table of categories (four titles + twelve)
    ("CategoriesOfQuantity", "Title: unity, plurality, totality.", "a priori"),
    ("CategoriesOfQuality", "Title: reality, negation, limitation.", "a priori"),
    ("CategoriesOfRelation", "Title: substance, causality, community.", "a priori"),
    ("CategoriesOfModality", "Title: possibility, existence, necessity.", "a priori"),
    ("Unity", "Category of quantity.", "a priori"),
    ("Plurality", "Category of quantity.", "a priori"),
    ("Totality", "Category of quantity.", "a priori"),
    ("Reality", "Category of quality.", "a priori"),
    ("Negation", "Category of quality.", "a priori"),
    ("Limitation", "Category of quality.", "a priori"),
    ("Substance", "Category of relation (substance/accident).", "a priori"),
    ("Causality", "Category of relation (cause/effect).", "a priori"),
    ("Community", "Category of relation (reciprocity).", "a priori"),
    ("Possibility", "Category of modality.", "a priori"),
    ("Existence", "Category of modality.", "a priori"),
    ("Necessity", "Category of modality.", "a priori"),
    # ideas of reason
    ("Soul", "Transcendental idea of the thinking subject.", "transcendental"),
    ("Cosmos", "Transcendental idea of the world-whole.", "transcendental"),
    ("God", "Transcendental idea of the unconditioned ground.", "transcendental"),
    # doctrines
    ("Doctrine", "A systematic philosophical position.", "abstract"),
    ("TranscendentalIdealism", "Objects of experience are appearances, not things in themselves.", "abstract"),
    ("CopernicanRevolution", "Objects conform to cognition, not cognition to objects.", "abstract"),
    # structure of the first Critique
    ("CritiquePart", "A division of the Critique of Pure Reason.", "abstract"),
    ("TranscendentalAesthetic", "Doctrine of sensibility (space and time).", "abstract"),
    ("TranscendentalLogic", "Doctrine of the understanding and reason.", "abstract"),
    ("TranscendentalAnalytic", "Logic of truth: categories and principles.", "abstract"),
    ("TranscendentalDialectic", "Logic of illusion: the ideas of reason.", "abstract"),
    ("TranscendentalDeduction", "Justification that categories apply to experience.", "abstract"),
    ("Antinomy", "Contradiction reason falls into about the world-whole.", "abstract"),
    ("Paralogism", "Fallacious inference of rational psychology about the soul.", "abstract"),
    ("IdealOfPureReason", "Dialectical treatment of the idea of God.", "abstract"),
    # ethics
    ("Imperative", "A command of practical reason.", "abstract"),
    ("CategoricalImperative", "Unconditional moral command.", "abstract"),
    ("HypotheticalImperative", "Conditional command of means to ends.", "abstract"),
    ("MoralConcept", "A concept of Kantian moral philosophy.", "abstract"),
    ("Maxim", "Subjective principle of volition.", "abstract"),
    ("Duty", "Necessity of an action from respect for the law.", "abstract"),
    ("GoodWill", "A will good in itself, without qualification.", "abstract"),
    ("Autonomy", "Self-legislation of the rational will.", "abstract"),
    ("Heteronomy", "Determination of the will by external ends.", "abstract"),
    ("MoralLaw", "The universal law binding rational agents.", "abstract"),
    ("KingdomOfEnds", "Systematic union of ends-in-themselves under common law.", "abstract"),
    ("Freedom", "Autonomy of the will; a postulate of practical reason.", "abstract"),
    ("Universalizability", "Test of a maxim's fitness to be a universal law.", "abstract"),
    ("EndInItself", "A rational being with unconditional worth.", "abstract"),
    ("Dignity", "The unconditional, incomparable worth of a person.", "abstract"),
    # aesthetics
    ("AestheticConcept", "A concept of Kant's theory of taste.", "abstract"),
    ("Beautiful", "What pleases universally, without a concept.", "abstract"),
    ("Sublime", "What pleases through the mind's response to the formless/immense.", "abstract"),
    ("JudgmentOfTaste", "Aesthetic judgment claiming subjective universality.", "abstract"),
    ("Purposiveness", "Form of finality without a determinate end.", "abstract"),
    ("Genius", "Talent through which nature gives the rule to art.", "abstract"),
]

# --------------------------------------------------------------------------- #
# Relations: (source, predicate, target[, reference])                         #
# --------------------------------------------------------------------------- #
def _edges() -> List[tuple]:
    E: List[tuple] = []

    # -- is-a (kind subsumption) --
    isa = [
        ("Intuition", "Representation"), ("Concept", "Representation"),
        ("Category", "Concept"), ("Idea", "Concept"), ("TranscendentalIdea", "Idea"),
        ("Sensibility", "Faculty"), ("Understanding", "Faculty"), ("Reason", "Faculty"),
        ("Imagination", "Faculty"), ("PowerOfJudgment", "Faculty"),
        ("TheoreticalReason", "Reason"), ("PracticalReason", "Reason"),
        ("Appearance", "Object"), ("ThingInItself", "Object"),
        ("Space", "FormOfIntuition"), ("Time", "FormOfIntuition"),
        ("AnalyticJudgment", "Judgment"), ("SyntheticJudgment", "Judgment"),
        ("SyntheticAPriori", "SyntheticJudgment"),
        ("APriori", "EpistemicDistinction"), ("APosteriori", "EpistemicDistinction"),
        ("Analytic", "EpistemicDistinction"), ("Synthetic", "EpistemicDistinction"),
        ("CategoriesOfQuantity", "Category"), ("CategoriesOfQuality", "Category"),
        ("CategoriesOfRelation", "Category"), ("CategoriesOfModality", "Category"),
        ("Unity", "CategoriesOfQuantity"), ("Plurality", "CategoriesOfQuantity"), ("Totality", "CategoriesOfQuantity"),
        ("Reality", "CategoriesOfQuality"), ("Negation", "CategoriesOfQuality"), ("Limitation", "CategoriesOfQuality"),
        ("Substance", "CategoriesOfRelation"), ("Causality", "CategoriesOfRelation"), ("Community", "CategoriesOfRelation"),
        ("Possibility", "CategoriesOfModality"), ("Existence", "CategoriesOfModality"), ("Necessity", "CategoriesOfModality"),
        ("Soul", "TranscendentalIdea"), ("Cosmos", "TranscendentalIdea"), ("God", "TranscendentalIdea"),
        ("TranscendentalIdealism", "Doctrine"), ("CopernicanRevolution", "Doctrine"),
        ("TranscendentalAesthetic", "CritiquePart"), ("TranscendentalLogic", "CritiquePart"),
        ("TranscendentalAnalytic", "TranscendentalLogic"), ("TranscendentalDialectic", "TranscendentalLogic"),
        ("TranscendentalDeduction", "CritiquePart"),
        ("Antinomy", "CritiquePart"), ("Paralogism", "CritiquePart"), ("IdealOfPureReason", "CritiquePart"),
        ("CategoricalImperative", "Imperative"), ("HypotheticalImperative", "Imperative"),
        ("Maxim", "MoralConcept"), ("Duty", "MoralConcept"), ("GoodWill", "MoralConcept"),
        ("Autonomy", "MoralConcept"), ("Heteronomy", "MoralConcept"), ("MoralLaw", "MoralConcept"),
        ("KingdomOfEnds", "MoralConcept"), ("Freedom", "MoralConcept"),
        ("Universalizability", "MoralConcept"), ("EndInItself", "MoralConcept"), ("Dignity", "MoralConcept"),
        ("Beautiful", "AestheticConcept"), ("Sublime", "AestheticConcept"),
        ("JudgmentOfTaste", "AestheticConcept"), ("Purposiveness", "AestheticConcept"), ("Genius", "AestheticConcept"),
    ]
    E += [(s, "is-a", t, CPR) for s, t in isa]

    # -- part-of (structure of the first Critique) --
    part = [
        ("TranscendentalAesthetic", "CritiqueOfPureReason"), ("TranscendentalLogic", "CritiqueOfPureReason"),
        ("TranscendentalAnalytic", "TranscendentalLogic"), ("TranscendentalDialectic", "TranscendentalLogic"),
        ("TranscendentalDeduction", "TranscendentalAnalytic"),
        ("Space", "TranscendentalAesthetic"), ("Time", "TranscendentalAesthetic"),
        ("CategoriesOfQuantity", "TranscendentalAnalytic"), ("CategoriesOfQuality", "TranscendentalAnalytic"),
        ("CategoriesOfRelation", "TranscendentalAnalytic"), ("CategoriesOfModality", "TranscendentalAnalytic"),
        ("Antinomy", "TranscendentalDialectic"), ("Paralogism", "TranscendentalDialectic"),
        ("IdealOfPureReason", "TranscendentalDialectic"),
    ]
    E += [(s, "part-of", t, CPR) for s, t in part]

    # -- contrasts-with (Kant's dichotomies) --
    contrasts = [
        ("Appearance", "ThingInItself"), ("Analytic", "Synthetic"), ("APriori", "APosteriori"),
        ("CategoricalImperative", "HypotheticalImperative"), ("Autonomy", "Heteronomy"),
        ("Beautiful", "Sublime"), ("Intuition", "Concept"),
    ]
    E += [(s, "contrasts-with", t) for s, t in contrasts]

    # -- epistemology: how cognition is generated --
    E += [
        ("Cognition", "requires", "Intuition", CPR),
        ("Cognition", "requires", "Concept", CPR),
        ("Sensibility", "produces", "Intuition", CPR),
        ("Understanding", "produces", "Concept", CPR),
        ("Understanding", "produces", "Category", CPR),
        ("Reason", "produces", "Idea", CPR),
        ("Imagination", "produces", "Schema", CPR),
        ("Space", "is-form-of", "Intuition", CPR),
        ("Time", "is-form-of", "Intuition", CPR),
        ("Intuition", "applies-to", "Appearance", CPR),
        ("Category", "applies-to", "Appearance", CPR),
        ("Schema", "enables", "Category", CPR),
        ("Category", "enables", "Experience", CPR),
        ("Experience", "presupposes", "Category", CPR),
        ("TranscendentalDeduction", "addresses", "Category", CPR),
        ("TranscendentalAesthetic", "addresses", "Space", CPR),
        ("TranscendentalAesthetic", "addresses", "Time", CPR),
        ("Paralogism", "addresses", "Soul", CPR),
        ("Antinomy", "addresses", "Cosmos", CPR),
        ("IdealOfPureReason", "addresses", "God", CPR),
        ("CopernicanRevolution", "grounds", "TranscendentalIdealism", PROL),
        ("TranscendentalIdealism", "grounds", "Appearance", CPR),
        ("SyntheticAPriori", "enables", "Experience", PROL),
    ]

    # -- ethics --
    E += [
        ("PracticalReason", "produces", "MoralLaw", CPrR),
        ("Autonomy", "grounds", "MoralLaw", GW),
        ("MoralLaw", "grounds", "Duty", GW),
        ("MoralLaw", "presupposes", "Freedom", CPrR),
        ("Autonomy", "requires", "Freedom", GW),
        ("Autonomy", "grounds", "KingdomOfEnds", GW),
        ("CategoricalImperative", "requires", "Universalizability", GW),
        ("CategoricalImperative", "requires", "EndInItself", GW),
        ("CategoricalImperative", "applies-to", "Maxim", GW),
        ("EndInItself", "grounds", "Dignity", GW),
        ("GoodWill", "requires", "Duty", GW),
        ("MoralLaw", "grounds", "CategoricalImperative", GW),
    ]

    # -- aesthetics --
    E += [
        ("PowerOfJudgment", "produces", "JudgmentOfTaste", CJ),
        ("JudgmentOfTaste", "applies-to", "Beautiful", CJ),
        ("JudgmentOfTaste", "presupposes", "Purposiveness", CJ),
        ("Genius", "produces", "Beautiful", CJ),
    ]
    return E


# --------------------------------------------------------------------------- #
# Propositions + one argument                                                  #
# --------------------------------------------------------------------------- #
def _propositions() -> List[Proposition]:
    return [
        Proposition("Synthetic a priori judgments are possible.", truth_value=True,
                    label="P-SAP", id="k_p_synthetic_apriori", reference=CPR),
        Proposition("Space and time are pure a priori forms of intuition.", truth_value=True,
                    label="P-SpaceTime", id="k_p_space_time", reference=CPR),
        Proposition("The categories are conditions of the possibility of experience.", truth_value=True,
                    label="P-Categories", id="k_p_categories", reference=CPR),
        Proposition("We can cognize objects only as appearances, never as things in themselves.",
                    truth_value=True, label="P-Appearances", id="k_p_appearances", reference=CPR),
        Proposition("Act only on that maxim you can will to become a universal law.",
                    truth_value=True, label="P-FUL", id="k_p_ful", reference=GW),
        Proposition("Autonomy of the will is the supreme principle of morality.",
                    truth_value=True, label="P-Autonomy", id="k_p_autonomy", reference=GW),
        Proposition("The beautiful is what pleases universally without a concept.",
                    truth_value=True, label="P-Beautiful", id="k_p_beautiful", reference=CJ),
    ]


def _arguments() -> List[Argument]:
    return [
        Argument(
            ["Experience is actual for us.",
             "Experience requires that intuitions be unified under concepts.",
             "The categories are the a priori concepts that make such unity possible."],
            "Therefore the categories necessarily apply to all objects of experience.",
            scheme="transcendental argument", label="Transcendental-Deduction",
            id="k_arg_deduction", reference=CPR,
        )
    ]


# --------------------------------------------------------------------------- #
# Assembly + integrity                                                         #
# --------------------------------------------------------------------------- #
def build_ontology():
    """Return the ontology as a dict of typed valuez values (plus the vocabulary)."""
    individuals = [
        Individual(n, definition=d, ontological_status=s, id=_slug(n), reference=r)
        for (n, d, s, r) in INDIVIDUALS
    ]
    universals = [
        Universal(n, definition=d, ontological_status=s, id=_slug(n)) for (n, d, s) in UNIVERSALS
    ]

    relations: List[Relation] = []
    for i, edge in enumerate(_edges()):
        src, pred, tgt = edge[0], edge[1], edge[2]
        ref = edge[3] if len(edge) > 3 else None
        relations.append(Relation(src, pred, tgt, vocabulary=PREDICATES,
                                  id=f"k_rel_{i:03d}", reference=ref))

    instantiations = [
        Instantiation(individuals[0], _u(universals, "Philosopher"), id="k_inst_kant", reference=SEP),
    ]
    for work in ("CritiqueOfPureReason", "CritiqueOfPracticalReason", "CritiqueOfJudgment",
                 "Groundwork", "Prolegomena"):
        instantiations.append(
            Instantiation(_u(individuals, work), _u(universals, "PhilosophicalWork"),
                          id=f"k_inst_{_slug(work)}")
        )

    wrote = [
        Relation("ImmanuelKant", "wrote", w, vocabulary=PREDICATES, id=f"k_wrote_{_slug(w)}", reference=SEP)
        for w in ("CritiqueOfPureReason", "CritiqueOfPracticalReason", "CritiqueOfJudgment",
                  "Groundwork", "Prolegomena")
    ]

    return {
        "individuals": individuals,
        "universals": universals,
        "relations": relations + wrote,
        "instantiations": instantiations,
        "propositions": _propositions(),
        "arguments": _arguments(),
        "vocabulary": PREDICATES,
    }


def _u(items, name):
    for it in items:
        if it.name == name:
            return it
    raise KeyError(name)


def node_names(onto) -> set:
    """The set of all concept/individual names that edges may reference."""
    return {c.name for c in onto["individuals"]} | {c.name for c in onto["universals"]}


def validate_integrity(onto) -> List[str]:
    """Return a list of referential-integrity problems (empty means valid)."""
    names = node_names(onto)
    problems: List[str] = []
    all_edges = list(onto["relations"]) + list(onto["instantiations"])
    for r in all_edges:
        if r.source not in names:
            problems.append(f"{r.id}: unknown source {r.source!r}")
        if r.target not in names:
            problems.append(f"{r.id}: unknown target {r.target!r}")
    return problems


# --------------------------------------------------------------------------- #
# Runner                                                                       #
# --------------------------------------------------------------------------- #
def main() -> None:
    out_dir = Path(os.environ.get("VALUEZ_EXAMPLE_OUT",
                                  Path(tempfile.gettempdir()) / "valuez_kant"))
    out_dir.mkdir(parents=True, exist_ok=True)
    onto = build_ontology()

    problems = validate_integrity(onto)
    if problems:
        raise SystemExit("Referential-integrity errors:\n  " + "\n  ".join(problems))

    all_relations = list(onto["relations"]) + list(onto["instantiations"])
    everything: List[Value] = (
        onto["individuals"] + onto["universals"] + all_relations
        + onto["propositions"] + onto["arguments"]
    )

    repo = ValueRepository(data_dir=out_dir / "store")
    repo.add_values(everything)

    line = "-" * 72
    print(line)
    print("valuez ontology: the critical philosophy of Immanuel Kant")
    print(line)
    print(f"Individuals : {len(onto['individuals'])}")
    print(f"Universals  : {len(onto['universals'])}")
    print(f"Relations   : {len(onto['relations'])} (+{len(onto['instantiations'])} instantiations)")
    print(f"Propositions: {len(onto['propositions'])}   Arguments: {len(onto['arguments'])}")
    print(f"Referential integrity: OK ({len(node_names(onto))} nodes)")
    print()

    # Reasoning over the graph.
    for pred in ("is-a", "part-of", "grounds"):
        acyclic = reasoning.is_acyclic(onto["relations"], pred)
        print(f"  '{pred}' acyclic (well-formed order): {acyclic}")
    inferred = reasoning.infer_transitive(onto["relations"], "is-a")
    print(f"  is-a transitive closure adds {len(inferred)} inferred edges, e.g.:")
    for r in inferred[:6]:
        print(f"      {r.source} --is-a[inferred]--> {r.target}")
    print()

    # Persist canonical ontology + render graphs.
    canonical = Path(__file__).resolve().parent.parent / "ontologies" / "kant.json"
    repo.export_ontology(canonical)
    print(f"Canonical ontology written: {canonical}")

    graph_path = _render(all_relations + inferred, out_dir)
    if graph_path:
        print(f"Ontology graph: {graph_path}")
    arg_path = _render_arguments(onto["arguments"], out_dir)
    if arg_path:
        print(f"Argument map  : {arg_path}")
    print(line)


def _render(relations, out_dir: Path):
    try:
        import dots.graph  # noqa: F401
    except Exception:
        return None
    cwd = Path.cwd()
    try:
        os.chdir(out_dir)
        return visualize_relations(relations, "kant_ontology.html").resolve()
    finally:
        os.chdir(cwd)


def _render_arguments(arguments, out_dir: Path):
    try:
        import dots.graph  # noqa: F401
    except Exception:
        return None
    cwd = Path.cwd()
    try:
        os.chdir(out_dir)
        return visualize_arguments(arguments, "kant_arguments.html").resolve()
    finally:
        os.chdir(cwd)


if __name__ == "__main__":
    main()
