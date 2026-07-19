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
        "is-form-of", "addresses", "formulation-of",
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
    # formulas of the categorical imperative (Groundwork II)
    ("CategoricalImperativeFormula", "A formulation of the categorical imperative.", "abstract"),
    ("FormulaOfUniversalLaw", "Act only on a maxim you can will to be a universal law.", "abstract"),
    ("FormulaOfHumanity", "Treat humanity always as an end, never merely as a means.", "abstract"),
    ("FormulaOfAutonomy", "The will legislating universal law through its own maxims.", "abstract"),
    ("FormulaOfKingdomOfEnds", "Act as a legislating member of a kingdom of ends.", "abstract"),
    # practical reason: postulates and the highest good (second Critique)
    ("Postulate", "A postulate of pure practical reason.", "transcendental"),
    ("HighestGood", "Summum bonum: virtue united with proportionate happiness.", "abstract"),
    ("Virtue", "Moral strength of will in fulfilling one's duty.", "abstract"),
    ("Happiness", "Satisfaction of the sum of one's inclinations.", "abstract"),
    ("ImmortalityOfSoul", "Endless progress toward holiness; a postulate.", "transcendental"),
    ("ExistenceOfGod", "Ground of the possibility of the highest good; a postulate.", "transcendental"),
    # the four antinomies of pure reason (Dialectic)
    ("FirstAntinomy", "The world's beginning and limits in time and space.", "transcendental"),
    ("SecondAntinomy", "Simple parts versus infinite divisibility of substance.", "transcendental"),
    ("ThirdAntinomy", "Causality through freedom versus universal natural causality.", "transcendental"),
    ("FourthAntinomy", "A necessary being of the world versus none.", "transcendental"),
    # the four paralogisms of rational psychology (Dialectic)
    ("ParalogismOfSubstantiality", "Fallacy: the soul is a substance.", "transcendental"),
    ("ParalogismOfSimplicity", "Fallacy: the soul is simple.", "transcendental"),
    ("ParalogismOfPersonality", "Fallacy: the soul is a person, identical over time.", "transcendental"),
    ("ParalogismOfIdeality", "Fallacy concerning the soul's relation to outer objects.", "transcendental"),
    # further sections of the Analytic
    ("LogicalFunctionsOfJudgment", "The table of the forms of judgment.", "a priori"),
    ("MetaphysicalDeduction", "Derivation of the categories from the logical functions of judgment.", "abstract"),
    ("Schematism", "How categories apply to appearances via transcendental schemata.", "abstract"),
    ("PrinciplesOfPureUnderstanding", "Synthetic a priori principles grounded in the categories.", "abstract"),
    ("RefutationOfIdealism", "Proof that inner experience presupposes outer objects.", "abstract"),
    # third Critique: aesthetic judgment in depth
    ("ReflectingJudgment", "Judgment seeking a universal for a given particular.", "transcendental"),
    ("DeterminingJudgment", "Judgment subsuming a particular under a given universal.", "transcendental"),
    ("MomentOfTaste", "One of the four moments analyzing the judgment of taste.", "abstract"),
    ("Disinterestedness", "First moment: delight in the beautiful is free of interest.", "abstract"),
    ("SubjectiveUniversality", "Second moment: taste claims universal agreement without a concept.", "abstract"),
    ("PurposivenessWithoutPurpose", "Third moment: the form of finality without a determinate end.", "abstract"),
    ("ExemplaryNecessity", "Fourth moment: the necessary, exemplary delight of taste.", "abstract"),
    ("MathematicalSublime", "Sublimity of absolute magnitude overwhelming imagination.", "abstract"),
    ("DynamicalSublime", "Sublimity of nature's might contemplated in safety.", "abstract"),
    ("AestheticIdea", "Representation of imagination prompting much thought beyond any concept.", "abstract"),
    ("CommonSense", "Sensus communis: the shared feeling presupposed by taste.", "abstract"),
    ("FineArt", "Art that is purposive yet appears as free as nature.", "abstract"),
    # third Critique: teleological judgment
    ("TeleologicalJudgment", "Reflecting judgment of nature as if purposive.", "transcendental"),
    ("NaturalPurpose", "A being both cause and effect of itself; an organized end.", "abstract"),
    ("Organism", "A living being judged as a natural purpose.", "phenomenal"),
    # dialectic: the antinomic claims (thesis / antithesis)
    ("AntinomicClaim", "A thesis or antithesis of a cosmological antinomy.", "transcendental"),
    ("FirstAntinomyThesis", "The world has a beginning in time and limits in space.", "transcendental"),
    ("FirstAntinomyAntithesis", "The world is infinite in time and space.", "transcendental"),
    ("SecondAntinomyThesis", "Every composite substance consists of simple parts.", "transcendental"),
    ("SecondAntinomyAntithesis", "Nothing simple exists; substance is infinitely divisible.", "transcendental"),
    ("ThirdAntinomyThesis", "Causality through freedom is required to explain appearances.", "transcendental"),
    ("ThirdAntinomyAntithesis", "There is no freedom; all is by natural causality.", "transcendental"),
    ("FourthAntinomyThesis", "An absolutely necessary being belongs to the world.", "transcendental"),
    ("FourthAntinomyAntithesis", "No absolutely necessary being exists in or out of the world.", "transcendental"),
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

    # -- extension: taxonomy for the newly added concepts (is-a) --
    isa2 = [
        ("CategoricalImperativeFormula", "MoralConcept"),
        ("FormulaOfUniversalLaw", "CategoricalImperativeFormula"),
        ("FormulaOfHumanity", "CategoricalImperativeFormula"),
        ("FormulaOfAutonomy", "CategoricalImperativeFormula"),
        ("FormulaOfKingdomOfEnds", "CategoricalImperativeFormula"),
        ("Postulate", "MoralConcept"), ("HighestGood", "MoralConcept"),
        ("Virtue", "MoralConcept"), ("Happiness", "MoralConcept"),
        ("Freedom", "Postulate"), ("ImmortalityOfSoul", "Postulate"), ("ExistenceOfGod", "Postulate"),
        ("FirstAntinomy", "Antinomy"), ("SecondAntinomy", "Antinomy"),
        ("ThirdAntinomy", "Antinomy"), ("FourthAntinomy", "Antinomy"),
        ("ParalogismOfSubstantiality", "Paralogism"), ("ParalogismOfSimplicity", "Paralogism"),
        ("ParalogismOfPersonality", "Paralogism"), ("ParalogismOfIdeality", "Paralogism"),
        ("MetaphysicalDeduction", "CritiquePart"), ("Schematism", "CritiquePart"),
        ("PrinciplesOfPureUnderstanding", "CritiquePart"), ("RefutationOfIdealism", "CritiquePart"),
    ]
    E += [(s, "is-a", t, GW if "Formula" in s or s in {"Postulate", "Virtue", "Happiness", "HighestGood"} else CPR)
          for s, t in isa2]

    # -- extension: part-of (further sections of the Analytic) --
    part2 = [
        ("MetaphysicalDeduction", "TranscendentalAnalytic"), ("Schematism", "TranscendentalAnalytic"),
        ("PrinciplesOfPureUnderstanding", "TranscendentalAnalytic"), ("RefutationOfIdealism", "TranscendentalAnalytic"),
    ]
    E += [(s, "part-of", t, CPR) for s, t in part2]

    # -- extension: the four formulas as formulations of the categorical imperative --
    E += [
        ("FormulaOfUniversalLaw", "formulation-of", "CategoricalImperative", GW),
        ("FormulaOfHumanity", "formulation-of", "CategoricalImperative", GW),
        ("FormulaOfAutonomy", "formulation-of", "CategoricalImperative", GW),
        ("FormulaOfKingdomOfEnds", "formulation-of", "CategoricalImperative", GW),
        ("FormulaOfUniversalLaw", "requires", "Universalizability", GW),
        ("FormulaOfHumanity", "requires", "EndInItself", GW),
        ("FormulaOfHumanity", "grounds", "Dignity", GW),
        ("FormulaOfAutonomy", "grounds", "Autonomy", GW),
        ("FormulaOfKingdomOfEnds", "requires", "KingdomOfEnds", GW),
    ]

    # -- extension: practical reason, postulates, the highest good --
    E += [
        ("PracticalReason", "produces", "Postulate", CPrR),
        ("HighestGood", "requires", "Virtue", CPrR),
        ("HighestGood", "requires", "Happiness", CPrR),
        ("HighestGood", "presupposes", "ImmortalityOfSoul", CPrR),
        ("HighestGood", "presupposes", "ExistenceOfGod", CPrR),
    ]

    # -- extension: what the antinomies and paralogisms address --
    E += [
        ("FirstAntinomy", "addresses", "Cosmos", CPR), ("SecondAntinomy", "addresses", "Cosmos", CPR),
        ("ThirdAntinomy", "addresses", "Freedom", CPR), ("ThirdAntinomy", "addresses", "Causality", CPR),
        ("FourthAntinomy", "addresses", "Cosmos", CPR),
        ("ParalogismOfSubstantiality", "addresses", "Soul", CPR),
        ("ParalogismOfSimplicity", "addresses", "Soul", CPR),
        ("ParalogismOfPersonality", "addresses", "Soul", CPR),
        ("ParalogismOfIdeality", "addresses", "Soul", CPR),
    ]

    # -- extension: mechanics of the Analytic --
    E += [
        ("MetaphysicalDeduction", "addresses", "LogicalFunctionsOfJudgment", CPR),
        ("MetaphysicalDeduction", "addresses", "Category", CPR),
        ("LogicalFunctionsOfJudgment", "grounds", "Category", CPR),
        ("Schematism", "addresses", "Schema", CPR),
        ("PrinciplesOfPureUnderstanding", "grounds", "Experience", CPR),
        ("RefutationOfIdealism", "addresses", "Time", CPR),
    ]

    # -- pass 3: third Critique (aesthetics + teleology), is-a --
    isa_cj = [
        ("ReflectingJudgment", "PowerOfJudgment"), ("DeterminingJudgment", "PowerOfJudgment"),
        ("JudgmentOfTaste", "ReflectingJudgment"), ("TeleologicalJudgment", "ReflectingJudgment"),
        ("MomentOfTaste", "AestheticConcept"),
        ("Disinterestedness", "MomentOfTaste"), ("SubjectiveUniversality", "MomentOfTaste"),
        ("PurposivenessWithoutPurpose", "MomentOfTaste"), ("ExemplaryNecessity", "MomentOfTaste"),
        ("MathematicalSublime", "Sublime"), ("DynamicalSublime", "Sublime"),
        ("AestheticIdea", "AestheticConcept"), ("CommonSense", "AestheticConcept"), ("FineArt", "AestheticConcept"),
        ("Organism", "NaturalPurpose"),
    ]
    E += [(s, "is-a", t, CJ) for s, t in isa_cj]

    # -- pass 3: third Critique relations --
    E += [
        ("DeterminingJudgment", "contrasts-with", "ReflectingJudgment", CJ),
        ("JudgmentOfTaste", "requires", "Disinterestedness", CJ),
        ("JudgmentOfTaste", "requires", "SubjectiveUniversality", CJ),
        ("JudgmentOfTaste", "requires", "PurposivenessWithoutPurpose", CJ),
        ("JudgmentOfTaste", "requires", "ExemplaryNecessity", CJ),
        ("JudgmentOfTaste", "presupposes", "CommonSense", CJ),
        ("PurposivenessWithoutPurpose", "is-form-of", "Purposiveness", CJ),
        ("Genius", "produces", "AestheticIdea", CJ),
        ("Genius", "produces", "FineArt", CJ),
        ("AestheticIdea", "grounds", "Beautiful", CJ),
        ("TeleologicalJudgment", "applies-to", "NaturalPurpose", CJ),
        ("TeleologicalJudgment", "presupposes", "Purposiveness", CJ),
    ]

    # -- pass 3: the antinomic claims (thesis / antithesis) --
    claims = [
        ("First", "FirstAntinomy"), ("Second", "SecondAntinomy"),
        ("Third", "ThirdAntinomy"), ("Fourth", "FourthAntinomy"),
    ]
    for stem, antinomy in claims:
        thesis, antithesis = f"{stem}AntinomyThesis", f"{stem}AntinomyAntithesis"
        E += [
            (thesis, "is-a", "AntinomicClaim", CPR),
            (antithesis, "is-a", "AntinomicClaim", CPR),
            (thesis, "part-of", antinomy, CPR),
            (antithesis, "part-of", antinomy, CPR),
            (thesis, "contrasts-with", antithesis, CPR),
        ]

    # -- pass 3: cross-Critique bridges --
    E += [
        ("TranscendentalIdealism", "grounds", "Freedom", CPR),
        ("ThirdAntinomy", "addresses", "Cosmos", CPR),
        ("TranscendentalIdealism", "grounds", "ThingInItself", CPR),
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
        Proposition("Nothing can be conceived as good without qualification except a good will.",
                    truth_value=True, label="P-GoodWill", id="k_p_good_will", reference=GW),
        Proposition("Freedom, immortality, and God are postulates of pure practical reason.",
                    truth_value=True, label="P-Postulates", id="k_p_postulates", reference=CPrR),
        Proposition("Freedom and natural necessity are reconcilable under transcendental idealism.",
                    truth_value=True, label="P-FreedomNature", id="k_p_freedom_nature", reference=CPR),
        Proposition("The highest good unites virtue with proportionate happiness.",
                    truth_value=True, label="P-HighestGood", id="k_p_highest_good", reference=CPrR),
        Proposition("The beautiful is the symbol of the morally good.",
                    truth_value=True, label="P-BeautySymbol", id="k_p_beauty_symbol", reference=CJ),
        Proposition("Organized beings must be judged as natural purposes.",
                    truth_value=True, label="P-NaturalPurpose", id="k_p_natural_purpose", reference=CJ),
        Proposition("Every cosmological antinomy is resolved by distinguishing appearances from things in themselves.",
                    truth_value=True, label="P-AntinomyResolution", id="k_p_antinomy_resolution", reference=CPR),
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
        ),
        Argument(
            ["A good will is good through its willing, not through its effects.",
             "Every other good (talents, fortune, even happiness) can be put to bad use.",
             "Only a good will is good without limitation."],
            "Nothing can be conceived as good without qualification except a good will.",
            scheme="analysis of common moral cognition", label="Good-Will-Argument",
            id="k_arg_good_will", reference=GW,
        ),
        Argument(
            ["If appearances were things in themselves, freedom and natural causality would contradict.",
             "Under transcendental idealism, appearances are not things in themselves.",
             "Natural causality then governs appearances, while freedom may govern things in themselves."],
            "Therefore freedom and natural necessity can both hold without contradiction.",
            scheme="resolution of an antinomy", label="Third-Antinomy-Resolution",
            id="k_arg_third_antinomy", reference=CPR,
        ),
        Argument(
            ["Practical reason commands us to promote the highest good.",
             "The highest good (virtue with proportionate happiness) must therefore be possible.",
             "Its possibility requires freedom, the immortality of the soul, and the existence of God."],
            "Therefore we must postulate freedom, immortality, and the existence of God.",
            scheme="moral argument", label="Postulates-Argument",
            id="k_arg_postulates", reference=CPrR,
        ),
        Argument(
            ["A judgment of taste claims the universal agreement of everyone.",
             "It can rest neither on determinate concepts nor on private sensation.",
             "It must therefore presuppose a common sense (sensus communis) shared by all."],
            "Therefore judgments of taste are grounded in a common sense warranting their universal validity.",
            scheme="deduction of taste", label="Deduction-of-Taste",
            id="k_arg_taste", reference=CJ,
        ),
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
