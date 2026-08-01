#!/usr/bin/env python3
"""An ontology of Søren Kierkegaard's existential philosophy, built with valuez.

This is a *content* example and the deliberate companion to
``kant_ontology.py``. It maps Kierkegaard's authorship as a traceable, queryable
graph:

- **Particulars** (:class:`Individual`) -- Kierkegaard, his pseudonymous
  personae, his major works, and the exemplary figures (Abraham, Don Juan, ...).
- **Universals** (:class:`Universal`) -- the concepts of the system (the three
  stages of existence, the self as synthesis, anxiety/despair, faith and the
  absolute paradox, subjectivity/truth, indirect communication), each with an
  ``ontological_status``.
- **Instantiation** -- typed ``Individual --instantiates--> Universal`` edges.
- **Relations** over a controlled predicate vocabulary: ``is-a`` (kind
  subsumption), ``part-of`` (the self's synthesis), ``contrasts-with``
  (Kierkegaard's dualities), plus ``requires`` / ``grounds`` / ``presupposes`` /
  ``produces`` / ``enables`` / ``addresses`` / ``authored-as`` / ``critiques`` /
  ``exemplifies`` / ``synthesizes`` / ``leads-to`` / ``wrote``.
- **Propositions** -- reified, cited theses; and several **Arguments** (the
  teleological suspension of the ethical, subjectivity-is-truth, the self and
  despair, the case against the system, the paradox and offense).

Why a *second* comprehensive ontology?  To have two rich topologies that overlap
by **name** but were authored independently, so we can later build a *merge*
function that folds many exported files into a single "universe". To make that
exercise meaningful this graph deliberately reuses several universal names from
``kant_ontology.py`` (see ``MERGE_ANCHORS``): some are clean matches
(``Philosopher``, ``PhilosophicalWork``) and some are genuine *semantic
collisions* -- ``Existence``, ``Freedom``, ``Possibility``, ``Necessity``,
``Reason``, ``Understanding``, ``God`` all appear in both systems with different
definitions and ontological status, exactly the hard case a merge must resolve.
Note the id prefixes differ (``kk_`` here vs ``k_`` in Kant), so the two files
never collide *by id*; a merge would have to key on **name**.

It then reasons over the graph (transitive closure of ``is-a``; acyclicity of the
strict orders), persists everything through ``dots``, exports the canonical
``ontologies/kierkegaard.json``, and renders an interactive graph.

Run:  python examples/kierkegaard_ontology.py
"""
from __future__ import annotations

import os
import re
import sys
import tempfile
from pathlib import Path
from typing import List

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
CI = Reference("Kierkegaard, The Concept of Irony (1841)")
EO = Reference("Kierkegaard (Victor Eremita, ed.), Either/Or (1843)")
FT = Reference("Kierkegaard (Johannes de silentio), Fear and Trembling (1843)")
REP = Reference("Kierkegaard (Constantin Constantius), Repetition (1843)")
CA = Reference("Kierkegaard (Vigilius Haufniensis), The Concept of Anxiety (1844)")
PF = Reference("Kierkegaard (Johannes Climacus), Philosophical Fragments (1844)")
SLW = Reference("Kierkegaard, Stages on Life's Way (1845)")
CUP = Reference("Kierkegaard (Johannes Climacus), Concluding Unscientific Postscript (1846)")
UDVS = Reference("Kierkegaard, Upbuilding Discourses in Various Spirits (1847)")
WL = Reference("Kierkegaard, Works of Love (1847)")
SUD = Reference("Kierkegaard (Anti-Climacus), The Sickness unto Death (1849)")
PC = Reference("Kierkegaard (Anti-Climacus), Practice in Christianity (1850)")
POV = Reference("Kierkegaard, The Point of View for My Work as an Author (1859)")
JOUR = Reference("Kierkegaard, Journals and Papers")
SEP = Reference("Stanford Encyclopedia of Philosophy, 'Soren Kierkegaard'")

# Controlled predicate vocabulary for the (non-instantiation) relations. It is a
# superset of the Kantian vocabulary (so the two files share most predicates --
# another axis a merge can union) plus a few Kierkegaard-specific verbs.
PREDICATES = Vocabulary(
    "kierkegaardian_relations",
    [
        # shared with kant_ontology.py
        "is-a", "part-of", "wrote", "instantiates", "contrasts-with", "requires",
        "produces", "grounds", "applies-to", "enables", "presupposes",
        "is-form-of", "addresses", "formulation-of",
        # Kierkegaard-specific
        "authored-as", "critiques", "exemplifies", "synthesizes", "leads-to",
    ],
    reference=Reference("Framework convention", description="Allowed relation types."),
)

# Universal names deliberately shared with kant_ontology.py, as anchors/tests for
# a future cross-file merge. Clean matches + genuine semantic collisions.
MERGE_ANCHORS = [
    "Philosopher", "PhilosophicalWork",       # clean top-kind matches
    "Existence", "Freedom", "Possibility",    # collisions: modal in Kant, existential here
    "Necessity", "Reason", "Understanding", "God",
]


def _slug(name: str) -> str:
    return "kk_" + re.sub(r"[^0-9a-zA-Z]+", "_", name).strip("_").lower()


# --------------------------------------------------------------------------- #
# Individuals (particulars): Kierkegaard, pseudonyms, works, exemplars         #
# --------------------------------------------------------------------------- #
INDIVIDUALS = [
    ("SorenKierkegaard", "Danish philosopher (1813-1855); father of existentialism.", "historical", SEP),
    # works
    ("TheConceptOfIrony", "Kierkegaard's dissertation (1841).", "historical", CI),
    ("EitherOr", "Either/Or (1843), edited by the pseudonym Victor Eremita.", "historical", EO),
    ("FearAndTrembling", "Fear and Trembling (1843), by Johannes de silentio.", "historical", FT),
    ("RepetitionBook", "Repetition (1843), by Constantin Constantius (the *work*; cf. the concept).", "historical", REP),
    ("TheConceptOfAnxiety", "The Concept of Anxiety (1844), by Vigilius Haufniensis.", "historical", CA),
    ("PhilosophicalFragments", "Philosophical Fragments (1844), by Johannes Climacus.", "historical", PF),
    ("StagesOnLifesWay", "Stages on Life's Way (1845).", "historical", SLW),
    ("ConcludingUnscientificPostscript", "Concluding Unscientific Postscript (1846), by Johannes Climacus.", "historical", CUP),
    ("WorksOfLove", "Works of Love (1847), signed.", "historical", WL),
    ("TheSicknessUntoDeath", "The Sickness unto Death (1849), by Anti-Climacus.", "historical", SUD),
    ("PracticeInChristianity", "Practice in Christianity (1850), by Anti-Climacus.", "historical", PC),
    # pseudonymous personae
    ("VictorEremita", "Pseudonymous editor of Either/Or.", "historical", EO),
    ("JohannesDeSilentio", "Pseudonymous author of Fear and Trembling.", "historical", FT),
    ("ConstantinConstantius", "Pseudonymous author of Repetition.", "historical", REP),
    ("VigiliusHaufniensis", "Pseudonymous author of The Concept of Anxiety.", "historical", CA),
    ("JohannesClimacus", "Pseudonymous author of the Fragments and the Postscript.", "historical", CUP),
    ("AntiClimacus", "Pseudonymous author of the higher Christian works.", "historical", SUD),
    # exemplary figures
    ("Abraham", "The biblical patriarch; exemplar of faith in Fear and Trembling.", "historical", FT),
    ("DonJuan", "Mozart's seducer; the immediate-erotic exemplar of the aesthetic.", "historical", EO),
    ("JohannesTheSeducer", "The diarist of 'The Seducer's Diary'; the reflective aesthete.", "historical", EO),
    ("JudgeWilliam", "Assessor Wilhelm; the ethical voice of Either/Or II.", "historical", EO),
]

# --------------------------------------------------------------------------- #
# Universals (kinds/concepts): (name, definition, ontological_status)          #
# --------------------------------------------------------------------------- #
UNIVERSALS = [
    # top kinds used as instantiation targets / subsumption roots
    ("Philosopher", "One who practices philosophy.", "abstract"),                 # MERGE anchor
    ("PhilosophicalWork", "A work of philosophy.", "abstract"),                   # MERGE anchor
    ("Pseudonym", "A fictive authorial persona used to present a life-view.", "abstract"),
    ("Exemplar", "A figure embodying a stage or existential type.", "abstract"),
    ("ExistentialConcept", "A concept of concrete, subjective existence.", "existential"),
    ("PsychologicalConcept", "A determination of the psyche disclosing spirit.", "psychological"),
    ("TheologicalConcept", "A concept of Christian existence-communication.", "theological"),
    ("StageOfExistence", "A sphere of existence: a basic mode of living.", "existential"),
    ("AuthorialMethod", "A mode of communication in the authorship.", "abstract"),
    ("ExistentialType", "A type of existing individual defined by a movement of spirit.", "existential"),
    # existence and the self
    ("Existence", "Concrete individual becoming; a task, not a logical category.", "existential"),   # MERGE (collision)
    ("Subjectivity", "The inward, appropriated relation of a person to truth.", "existential"),
    ("Objectivity", "The disinterested, third-person standpoint of abstract thought.", "abstract"),
    ("Truth", "That which is essentially related to existence ('truth is subjectivity').", "abstract"),
    ("Inwardness", "Passionate, appropriated interior relation to one's existence.", "existential"),
    ("Passion", "The intensity of inward existence; the culmination of subjectivity.", "existential"),
    ("TheSelf", "A relation that relates itself to itself, grounded in the power that posited it.", "existential"),
    ("Spirit", "The self as the synthesis that posits itself before God.", "existential"),
    ("Synthesis", "The self as a union of opposed determinations.", "abstract"),
    ("Freedom", "Possibility disclosed to the self; 'the dizziness of freedom'.", "existential"),     # MERGE (collision)
    ("Possibility", "The open horizon the self must relate to; a term of the synthesis.", "existential"),  # MERGE (collision)
    ("Necessity", "The given, determined term of the synthesis.", "abstract"),    # MERGE (collision)
    ("Finitude", "The limited, temporal term of the synthesis.", "abstract"),
    ("Infinitude", "The unlimited, imaginative term of the synthesis.", "abstract"),
    ("Temporality", "Existence in time and becoming.", "abstract"),
    ("Eternity", "The timeless; that which the moment touches.", "abstract"),
    ("TheMoment", "Oieblikket: the instant where time and eternity touch.", "theological"),
    ("TheSingleIndividual", "Den Enkelte: the responsible individual before God.", "existential"),
    ("TheCrowd", "The anonymous public; 'the crowd is untruth'.", "abstract"),
    ("Reason", "Abstract thought whose claim to comprehend existence is limited.", "abstract"),        # MERGE (collision)
    ("Understanding", "Finite comprehension that founders on the absolute paradox.", "abstract"),      # MERGE (collision)
    # psychological determinations
    ("Anxiety", "Angest: the dizziness of freedom before possibility; the presupposition of sin.", "psychological"),
    ("Despair", "The sickness unto death: the self's misrelation to itself.", "psychological"),
    ("Guilt", "The consciousness of having fallen short before the eternal.", "psychological"),
    # stages of existence
    ("AestheticStage", "Living for immediacy, enjoyment, and possibility.", "existential"),
    ("EthicalStage", "Living by choice, commitment, and the universal.", "existential"),
    ("ReligiousStage", "Living before God in faith and inwardness.", "existential"),
    ("ReligiousnessA", "Immanent religiousness of inward suffering and guilt.", "theological"),
    ("ReligiousnessB", "Paradoxical (Christian) religiousness founded on the paradox.", "theological"),
    ("TheLeap", "The qualitative, unmediated transition into a new sphere or into faith.", "existential"),
    ("InfiniteResignation", "The movement renouncing the finite that precedes faith.", "existential"),
    ("KnightOfFaith", "One who, by virtue of the absurd, receives the finite back after resignation.", "abstract"),
    ("KnightOfInfiniteResignation", "One who renounces the finite but does not make the movement of faith.", "abstract"),
    # faith and Christian categories
    ("Faith", "The passion that grasps the absurd and rests transparently in God.", "theological"),
    ("God", "The eternal power in which the self must rest; the object of faith.", "theological"),     # MERGE (collision)
    ("GodInTime", "The eternal entering existence: God in time.", "theological"),
    ("Incarnation", "The god become an individual human being.", "theological"),
    ("Paradox", "A claim that offends and exceeds the understanding.", "theological"),
    ("AbsoluteParadox", "The eternal truth come into being in time; the god-man.", "theological"),
    ("TheAbsurd", "That the eternal God has existed in time; the object of faith.", "theological"),
    ("Offense", "The understanding's collision with the paradox; the alternative to faith.", "theological"),
    ("Contemporaneity", "Becoming contemporary with Christ in faith, across history.", "theological"),
    ("TeleologicalSuspensionOfTheEthical", "Faith's suspension of the universal for a higher telos.", "theological"),
    ("Sin", "Before God, in despair, not willing to be oneself (or willing to be oneself).", "theological"),
    ("OriginalSin", "Hereditary sin; sinfulness entering by a qualitative leap.", "theological"),
    ("Christianity", "The religion of the paradox, faith, and the god in time.", "theological"),
    ("Christendom", "The established, nominal Christianity Kierkegaard attacks.", "abstract"),
    # communication and method
    ("IndirectCommunication", "Communication that requires the reader's own appropriation.", "abstract"),
    ("Pseudonymity", "Presenting life-views through distinct authored personae.", "abstract"),
    ("Irony", "Infinite absolute negativity; a controlled distance from the finite.", "abstract"),
    ("Repetition", "The forward-looking recovery of existence, opposed to recollection.", "abstract"),
    ("Recollection", "The Platonic backward movement recovering the eternal in memory.", "abstract"),
    ("EdifyingDiscourse", "A signed, upbuilding address to 'that single individual'.", "abstract"),
    # targets of critique
    ("TheSystem", "The Hegelian speculative system that claims to comprehend existence.", "abstract"),
    ("Mediation", "Hegelian reconciliation of opposites, rejected in favor of the leap.", "abstract"),
    # love
    ("Love", "A mode of relating to the neighbor or the beloved.", "abstract"),
    ("NeighborLove", "Kjerlighed: commanded, non-preferential love of the neighbor.", "theological"),
    ("PreferentialLove", "Elskov: erotic or preferential love based on inclination.", "abstract"),
]


# --------------------------------------------------------------------------- #
# Relations: (source, predicate, target[, reference])                         #
# --------------------------------------------------------------------------- #
def _edges() -> List[tuple]:
    E: List[tuple] = []

    # -- is-a (kind subsumption) --
    isa = [
        ("Existence", "ExistentialConcept"), ("Subjectivity", "ExistentialConcept"),
        ("Inwardness", "ExistentialConcept"), ("Passion", "ExistentialConcept"),
        ("TheSelf", "ExistentialConcept"), ("Spirit", "ExistentialConcept"),
        ("Freedom", "ExistentialConcept"), ("Possibility", "ExistentialConcept"),
        ("TheSingleIndividual", "ExistentialConcept"), ("InfiniteResignation", "ExistentialConcept"),
        ("TheLeap", "ExistentialConcept"),
        ("Anxiety", "PsychologicalConcept"), ("Despair", "PsychologicalConcept"),
        ("Guilt", "PsychologicalConcept"),
        ("AestheticStage", "StageOfExistence"), ("EthicalStage", "StageOfExistence"),
        ("ReligiousStage", "StageOfExistence"),
        ("ReligiousnessA", "ReligiousStage"), ("ReligiousnessB", "ReligiousStage"),
        ("Faith", "TheologicalConcept"), ("Sin", "TheologicalConcept"),
        ("OriginalSin", "Sin"),
        ("TheAbsurd", "TheologicalConcept"), ("Paradox", "TheologicalConcept"),
        ("AbsoluteParadox", "Paradox"), ("Offense", "TheologicalConcept"),
        ("Contemporaneity", "TheologicalConcept"), ("GodInTime", "TheologicalConcept"),
        ("Incarnation", "TheologicalConcept"), ("TheMoment", "TheologicalConcept"),
        ("TeleologicalSuspensionOfTheEthical", "TheologicalConcept"),
        ("KnightOfFaith", "ExistentialType"), ("KnightOfInfiniteResignation", "ExistentialType"),
        ("IndirectCommunication", "AuthorialMethod"), ("Pseudonymity", "AuthorialMethod"),
        ("Irony", "AuthorialMethod"), ("EdifyingDiscourse", "AuthorialMethod"),
        ("NeighborLove", "Love"), ("PreferentialLove", "Love"),
    ]
    E += [(s, "is-a", t, SEP) for s, t in isa]

    # -- part-of (the structure of the self's synthesis) --
    part = [
        ("Possibility", "Synthesis"), ("Necessity", "Synthesis"),
        ("Finitude", "Synthesis"), ("Infinitude", "Synthesis"),
        ("Temporality", "Synthesis"), ("Eternity", "Synthesis"),
        ("Synthesis", "TheSelf"),
    ]
    E += [(s, "part-of", t, SUD) for s, t in part]

    # -- contrasts-with (Kierkegaard's dualities) --
    contrast = [
        ("Subjectivity", "Objectivity", CUP), ("Faith", "Reason", PF),
        ("Faith", "Offense", PC), ("Faith", "Despair", SUD), ("Sin", "Faith", SUD),
        ("TheSingleIndividual", "TheCrowd", POV), ("Repetition", "Recollection", REP),
        ("Eternity", "Temporality", CA), ("Possibility", "Necessity", SUD),
        ("Freedom", "Necessity", CA), ("Finitude", "Infinitude", SUD),
        ("NeighborLove", "PreferentialLove", WL), ("InfiniteResignation", "Faith", FT),
        ("AestheticStage", "EthicalStage", EO), ("EthicalStage", "ReligiousStage", FT),
        ("Christianity", "Christendom", PC), ("ReligiousnessA", "ReligiousnessB", CUP),
        ("EdifyingDiscourse", "IndirectCommunication", POV),
    ]
    E += [(s, "contrasts-with", t, r) for s, t, r in contrast]

    # -- requires --
    requires = [
        ("Faith", "TheLeap", FT), ("Faith", "TheAbsurd", FT), ("Faith", "InfiniteResignation", FT),
        ("ReligiousnessB", "AbsoluteParadox", CUP), ("ReligiousnessB", "Contemporaneity", PC),
        ("ReligiousnessB", "Faith", CUP), ("Christianity", "Faith", PF), ("Christianity", "Sin", SUD),
        ("TeleologicalSuspensionOfTheEthical", "Faith", FT), ("KnightOfFaith", "InfiniteResignation", FT),
        ("Truth", "Inwardness", CUP), ("Despair", "TheSelf", SUD), ("Offense", "AbsoluteParadox", PC),
    ]
    E += [(s, "requires", t, r) for s, t, r in requires]

    # -- presupposes --
    presupposes = [
        ("Sin", "Anxiety", CA), ("Sin", "Freedom", CA), ("Anxiety", "Possibility", CA),
        ("AbsoluteParadox", "GodInTime", PF), ("Contemporaneity", "Incarnation", PC),
        ("Subjectivity", "Passion", CUP),
    ]
    E += [(s, "presupposes", t, r) for s, t, r in presupposes]

    # -- produces --
    produces = [
        ("Freedom", "Anxiety", CA), ("Possibility", "Anxiety", CA),
    ]
    E += [(s, "produces", t, r) for s, t, r in produces]

    # -- grounds (a strict order) --
    grounds = [
        ("Subjectivity", "Truth", CUP), ("Faith", "TheSelf", SUD), ("God", "TheSelf", SUD),
        ("GodInTime", "AbsoluteParadox", PF), ("AbsoluteParadox", "Offense", PC),
        ("Despair", "Sin", SUD),
    ]
    E += [(s, "grounds", t, r) for s, t, r in grounds]

    # -- enables --
    enables = [
        ("IndirectCommunication", "Inwardness", CUP), ("TheLeap", "Faith", FT),
    ]
    E += [(s, "enables", t, r) for s, t, r in enables]

    # -- is-form-of --
    form = [
        ("Pseudonymity", "IndirectCommunication", POV), ("Irony", "IndirectCommunication", CI),
    ]
    E += [(s, "is-form-of", t, r) for s, t, r in form]

    # -- applies-to --
    E += [("TeleologicalSuspensionOfTheEthical", "applies-to", "EthicalStage", FT)]

    # -- synthesizes (the self unites its opposed terms) --
    E += [("TheSelf", "synthesizes", t, SUD) for t in
          ("Possibility", "Necessity", "Finitude", "Infinitude", "Temporality", "Eternity")]

    # -- leads-to (stage progression via leaps) --
    leads = [
        ("AestheticStage", "EthicalStage", SLW), ("EthicalStage", "ReligiousStage", SLW),
        ("ReligiousnessA", "ReligiousnessB", CUP), ("InfiniteResignation", "Faith", FT),
    ]
    E += [(s, "leads-to", t, r) for s, t, r in leads]

    # -- authored-as (Kierkegaard wrote under these personae) --
    E += [("SorenKierkegaard", "authored-as", p, r) for p, r in (
        ("VictorEremita", EO), ("JohannesDeSilentio", FT), ("ConstantinConstantius", REP),
        ("VigiliusHaufniensis", CA), ("JohannesClimacus", CUP), ("AntiClimacus", SUD),
    )]

    # -- wrote (persona / author -> work) --
    wrote = [
        ("VictorEremita", "EitherOr", EO), ("JohannesDeSilentio", "FearAndTrembling", FT),
        ("ConstantinConstantius", "RepetitionBook", REP), ("VigiliusHaufniensis", "TheConceptOfAnxiety", CA),
        ("JohannesClimacus", "PhilosophicalFragments", PF), ("JohannesClimacus", "ConcludingUnscientificPostscript", CUP),
        ("AntiClimacus", "TheSicknessUntoDeath", SUD), ("AntiClimacus", "PracticeInChristianity", PC),
        ("SorenKierkegaard", "WorksOfLove", WL), ("SorenKierkegaard", "TheConceptOfIrony", CI),
        ("SorenKierkegaard", "StagesOnLifesWay", SLW),
    ]
    E += [(s, "wrote", t, r) for s, t, r in wrote]

    # -- addresses (work -> concept it treats) --
    addresses = [
        ("FearAndTrembling", "Faith", FT), ("FearAndTrembling", "TeleologicalSuspensionOfTheEthical", FT),
        ("FearAndTrembling", "InfiniteResignation", FT), ("FearAndTrembling", "KnightOfFaith", FT),
        ("TheConceptOfAnxiety", "Anxiety", CA), ("TheConceptOfAnxiety", "Sin", CA),
        ("TheConceptOfAnxiety", "Freedom", CA), ("TheConceptOfAnxiety", "OriginalSin", CA),
        ("TheSicknessUntoDeath", "Despair", SUD), ("TheSicknessUntoDeath", "TheSelf", SUD),
        ("TheSicknessUntoDeath", "Sin", SUD),
        ("PhilosophicalFragments", "AbsoluteParadox", PF), ("PhilosophicalFragments", "GodInTime", PF),
        ("PhilosophicalFragments", "TheMoment", PF),
        ("ConcludingUnscientificPostscript", "Subjectivity", CUP), ("ConcludingUnscientificPostscript", "Truth", CUP),
        ("ConcludingUnscientificPostscript", "TheLeap", CUP), ("ConcludingUnscientificPostscript", "TheSystem", CUP),
        ("ConcludingUnscientificPostscript", "ReligiousnessB", CUP),
        ("EitherOr", "AestheticStage", EO), ("EitherOr", "EthicalStage", EO),
        ("WorksOfLove", "NeighborLove", WL), ("WorksOfLove", "Love", WL),
        ("TheConceptOfIrony", "Irony", CI),
        ("RepetitionBook", "Repetition", REP), ("RepetitionBook", "Recollection", REP),
        ("StagesOnLifesWay", "AestheticStage", SLW), ("StagesOnLifesWay", "EthicalStage", SLW),
        ("StagesOnLifesWay", "ReligiousStage", SLW),
        ("PracticeInChristianity", "Contemporaneity", PC), ("PracticeInChristianity", "Offense", PC),
        ("PracticeInChristianity", "Christendom", PC),
    ]
    E += [(s, "addresses", t, r) for s, t, r in addresses]

    # -- critiques --
    critiques = [
        ("ConcludingUnscientificPostscript", "TheSystem", CUP), ("ConcludingUnscientificPostscript", "Mediation", CUP),
        ("PracticeInChristianity", "Christendom", PC), ("SorenKierkegaard", "Christendom", POV),
        ("SorenKierkegaard", "TheSystem", POV), ("TheSingleIndividual", "TheCrowd", POV),
    ]
    E += [(s, "critiques", t, r) for s, t, r in critiques]

    # -- exemplifies (figure -> stage / type) --
    exemplifies = [
        ("Abraham", "KnightOfFaith", FT), ("Abraham", "Faith", FT),
        ("Abraham", "TeleologicalSuspensionOfTheEthical", FT),
        ("DonJuan", "AestheticStage", EO), ("JohannesTheSeducer", "AestheticStage", EO),
        ("JudgeWilliam", "EthicalStage", EO),
    ]
    E += [(s, "exemplifies", t, r) for s, t, r in exemplifies]

    return E


# --------------------------------------------------------------------------- #
# Propositions (reified, cited theses)                                        #
# --------------------------------------------------------------------------- #
def _propositions() -> List[Proposition]:
    return [
        Proposition("Truth is subjectivity.", truth_value=True,
                    label="P-Subjectivity", id="kk_p_subjectivity", reference=CUP),
        Proposition("Anxiety is the dizziness of freedom.", truth_value=True,
                    label="P-Anxiety", id="kk_p_anxiety", reference=CA),
        Proposition("The self is a relation that relates itself to itself.", truth_value=True,
                    label="P-Self", id="kk_p_self", reference=SUD),
        Proposition("Despair is the sickness unto death.", truth_value=True,
                    label="P-Despair", id="kk_p_despair", reference=SUD),
        Proposition("Faith is the highest passion in a person.", truth_value=True,
                    label="P-FaithPassion", id="kk_p_faith_passion", reference=FT),
        Proposition("Faith requires a leap by virtue of the absurd.", truth_value=True,
                    label="P-Leap", id="kk_p_leap", reference=FT),
        Proposition("The single individual is higher than the universal.", truth_value=True,
                    label="P-SingleIndividual", id="kk_p_single_individual", reference=FT),
        Proposition("The crowd is untruth.", truth_value=True,
                    label="P-Crowd", id="kk_p_crowd", reference=POV),
        Proposition("The opposite of sin is not virtue but faith.", truth_value=True,
                    label="P-SinFaith", id="kk_p_sin_faith", reference=SUD),
        Proposition("Purity of heart is to will one thing.", truth_value=True,
                    label="P-Purity", id="kk_p_purity", reference=UDVS),
        Proposition("Life must be understood backwards but lived forwards.", truth_value=True,
                    label="P-Backwards", id="kk_p_backwards", reference=JOUR),
    ]


# --------------------------------------------------------------------------- #
# Arguments (premises => conclusion)                                          #
# --------------------------------------------------------------------------- #
def _arguments() -> List[Argument]:
    return [
        Argument(
            ["The ethical as the universal forbids a father to kill his son.",
             "Yet Abraham is held justified in his readiness to sacrifice Isaac at God's command.",
             "This is possible only if the single individual can stand, as an individual, in an absolute relation to the absolute."],
            "Therefore faith involves a teleological suspension of the ethical.",
            scheme="faith argument", label="Teleological-Suspension",
            id="kk_arg_suspension", reference=FT,
        ),
        Argument(
            ["For an existing person, truth is a matter of how one relates, not merely what is related.",
             "The highest truth available to an existing individual is an objective uncertainty held fast in inwardness.",
             "Such appropriation is subjectivity raised to passion."],
            "Therefore, for the existing individual, truth is subjectivity.",
            scheme="existential analysis", label="Subjectivity-Is-Truth",
            id="kk_arg_subjectivity", reference=CUP,
        ),
        Argument(
            ["The self is a synthesis that relates itself to itself.",
             "Any misrelation in this self-relating is despair.",
             "The self did not establish itself but rests in the power that posited it."],
            "Therefore despair is healed only when the self, in willing to be itself, rests transparently in God.",
            scheme="dialectical analysis", label="Self-And-Despair",
            id="kk_arg_despair", reference=SUD,
        ),
        Argument(
            ["A logical system is possible, but an existential system is not.",
             "Existence is a continual becoming that abstraction cannot complete.",
             "The existing thinker is therefore never finished as the system pretends to be."],
            "Therefore speculative philosophy cannot comprehend existence, which must be lived in subjectivity.",
            scheme="reductio", label="Against-The-System",
            id="kk_arg_system", reference=CUP,
        ),
        Argument(
            ["The absolute paradox is that the eternal God has come into being in time.",
             "The understanding cannot think this and collides with it.",
             "This collision issues either in offense or in faith."],
            "Therefore faith, not comprehension, is the proper relation to the paradox.",
            scheme="existential dilemma", label="Paradox-And-Offense",
            id="kk_arg_paradox", reference=PF,
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
                                  id=f"kk_rel_{i:03d}", reference=ref))

    instantiations = [
        Instantiation(individuals[0], _u(universals, "Philosopher"), id="kk_inst_kierkegaard", reference=SEP),
    ]
    works = ("TheConceptOfIrony", "EitherOr", "FearAndTrembling", "RepetitionBook",
             "TheConceptOfAnxiety", "PhilosophicalFragments", "StagesOnLifesWay",
             "ConcludingUnscientificPostscript", "WorksOfLove", "TheSicknessUntoDeath",
             "PracticeInChristianity")
    for work in works:
        instantiations.append(
            Instantiation(_u(individuals, work), _u(universals, "PhilosophicalWork"),
                          id=f"kk_inst_{_slug(work)}")
        )
    for persona in ("VictorEremita", "JohannesDeSilentio", "ConstantinConstantius",
                    "VigiliusHaufniensis", "JohannesClimacus", "AntiClimacus"):
        instantiations.append(
            Instantiation(_u(individuals, persona), _u(universals, "Pseudonym"),
                          id=f"kk_inst_{_slug(persona)}")
        )
    for figure in ("Abraham", "DonJuan", "JohannesTheSeducer", "JudgeWilliam"):
        instantiations.append(
            Instantiation(_u(individuals, figure), _u(universals, "Exemplar"),
                          id=f"kk_inst_{_slug(figure)}")
        )

    return {
        "individuals": individuals,
        "universals": universals,
        "relations": relations,
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
                                  Path(tempfile.gettempdir()) / "valuez_kierkegaard"))
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
    print("valuez ontology: the existential philosophy of Soren Kierkegaard")
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

    # Overlap with the Kant ontology -- the anchors for a future merge.
    names = node_names(onto)
    shared = [a for a in MERGE_ANCHORS if a in names]
    print(f"  Deliberate overlap with kant_ontology.py ({len(shared)} shared names):")
    print(f"      {', '.join(shared)}")
    print("      (ids are 'kk_'-prefixed here vs 'k_' in Kant, so a merge must key on name)")
    print()

    # Persist canonical ontology + render graphs.
    canonical = Path(__file__).resolve().parent.parent / "ontologies" / "kierkegaard.json"
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
        return visualize_relations(relations, "kierkegaard_ontology.html").resolve()
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
        return visualize_arguments(arguments, "kierkegaard_arguments.html").resolve()
    finally:
        os.chdir(cwd)


if __name__ == "__main__":
    main()
