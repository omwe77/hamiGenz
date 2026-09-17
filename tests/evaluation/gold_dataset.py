"""
hamigenz — Gold evaluation dataset (PR-014).

Each case pairs difficult input text with HUMAN-VERIFIED evaluation data:
  - key_facts: facts a correct explanation MUST preserve (substring match
    on normalized text)
  - forbidden_facts: claims that would indicate hallucination/drift
  - acceptable_langs: languages the explanation may be written in
  - category: what the case exercises
  - level: explanation level requested

Key facts are checked on normalized text (casefolded, whitespace folded).
Expected facts were written by hand against the source text — the dataset
is small deliberately: coverage matters less than reliability.

For English→Nepali cases, expected English key_facts are mapped to their
Nepali renderings; to keep checking deterministic, those cases specify
`check_language: False` for facts that would require translation judgment,
and rely on numeric facts (fees, dates) which are language-independent.
"""
import re

from dataclasses import dataclass, field


@dataclass
class GoldCase:
    case_id: str
    category: str
    level: str            # original | simple | very_simple
    input_text: str
    key_facts: list  # str, or [alt1, alt2] alternatives (any one matches)
    forbidden_facts: list[str] = field(default_factory=list)
    # (noun_phrase, [negation_markers]) pairs: every sentence containing the
    # noun phrase must also contain one of the negation markers, otherwise
    # a negation was likely dropped. Nepali negation has many grammatical
    # forms (छैन / हुँदैन / पाइँदैन / गरिँदैन …), so markers are a set.
    negation_guards: list[tuple] = field(default_factory=list)
    expected_lang: str = "any"      # nepali | english | romanized | any
    language_independent_facts: bool = False  # digits checked across languages
    notes: str = ""


GOLD_CASES: list[GoldCase] = [
    # ── Formal Nepali → Simple ────────────────────────────────────
    GoldCase(
        case_id="np_simple_001",
        category="formal_nepali",
        level="simple",
        input_text=(
            "नेपाल सरकार, गृह मन्त्रालयको २०८१/०४/१५ गतेको सूचना अनुसार "
            "नागरिकता प्रमाणपत्र नवीकरण गर्न चाहने आवेदकले निवेदनको साथ "
            "नागरिकताको मूल प्रति तथा रु. ५०० प्रति जम्मा गर्नुपर्नेछ। "
            "उक्त व्यवस्था तत्काल प्रभावात्मक हुनेछ।"
        ),
        key_facts=[["500", "५००"], "नवीकरण", "नागरिकता"],
        forbidden_facts=["1000", "म्याद सकिएपछि", "passport", "राहदानी"],
        expected_lang="nepali",
        notes="Fee + effective-immediately notice; tests fee preservation.",
    ),
    GoldCase(
        case_id="np_simple_002",
        category="legal_nepali",
        level="simple",
        input_text=(
            "देहायबमोजिमका व्यक्तिहरूले मात्र यस योजनाको लाभ लिन सक्नेछन्: "
            "(क) नेपालको अति विपन्न वर्गमा पर्ने नागरिक, (ख) पूर्ण अपाङ्गता "
            "भएका व्यक्ति, (ग) सत्तरी वर्ष उमेर पूरा भई एकल जीवनयापन गर्ने "
            "व्यक्ति। अन्य व्यक्तिले लाभ लिएको पाइएमा उपलब्ध रकम असुल गरिनेछ।"
        ),
        key_facts=[["७०", "सत्तरी", "सत्तर", "70"], "अपाङ्ग"],
        forbidden_facts=["६५", "सबै नागरिक"],
        expected_lang="nepali",
        notes="Eligibility conditions; negation (others excluded) matters.",
    ),
    GoldCase(
        case_id="np_verysimple_001",
        category="formal_nepali",
        level="very_simple",
        input_text=(
            "आवेदन पत्र बुझाएको मितिले पन्ध्र (१५) दिनभित्र निर्णय गरी "
            "आवेदकलाई जानकारी गराइनेछ। तोकिएको अवधिमा निर्णय नभएमा "
            "आवेदकले निवेदन फिर्ता गर्न सक्नेछ।"
        ),
        key_facts=["१५", "दिन", "निर्णय"],
        forbidden_facts=["३०", "महिना"],
        expected_lang="nepali",
        notes="Deadline number must survive simplification.",
    ),
    GoldCase(
        case_id="np_negation_001",
        category="negation",
        level="simple",
        input_text=(
            "यस योजनाअन्तर्गत सहुलियत कर्जा मात्र उपलब्ध हुने व्यवस्था छ, "
            "अनुदान उपलब्ध हुने छैन। साथै कर्जा चुक्ता नगरेमा थप "
            "सहुलियत पाइने छैन।"
        ),
        key_facts=["कर्जा"],
        negation_guards=[
            ("अनुदान", ["छैन", "हुँदैन", "पाइँदैन", "गरिँदैन", "मिल्दैन", "बाहेक", "सकिँदैन"]),
        ],
        forbidden_facts=["अनुदान पाइने छ", "अनुदान दिइनेछ"],
        expected_lang="nepali",
        notes=(
            "Double negation — classic meaning flip risk. Affirmative "
            "inversions are caught by sentence-level negation_guards "
            "(phrase must co-occur with its negated form), not bare "
            "substrings, so correct negated wording never false-positives."),
    ),
    GoldCase(
        case_id="np_conditions_001",
        category="conditions",
        level="simple",
        input_text=(
            "विद्यार्थी भिसामा बसेका विद्यार्थीले समयपत्र लिएको अवस्थामा "
            "मात्र अंशकालीन काम गर्न पाउने छन्, तर सप्ताहमा बीस घण्टाभन्दा "
            "बढी काम गर्न पाउने छैनन्।"
        ),
        key_facts=[["२०", "बीस", "20"], "घण्टा"],
        negation_guards=[
            ("बढी काम", ["छैन", "हुँदैन", "पाइँदैन", "सक्दैन", "सकिँदैन", "मिल्दैन", "भन्दा बढी"]),
        ],
        forbidden_facts=["४०", "40"],
        expected_lang="nepali",
        notes="Conditional + numeric limit; affirmative inversion caught via negation_guards.",
    ),
    GoldCase(
        case_id="np_exception_001",
        category="exceptions",
        level="simple",
        input_text=(
            "सबै आवेदकले तोकिएको शुल्क बुझाउनुपर्नेछ। तर, पूर्ण अपाङ्गता "
            "भएका व्यक्तिहरूले भने शुल्क मिनाहा पाउनेछन्।"
        ),
        key_facts=["मिनाहा", "अपाङ्ग"],
        forbidden_facts=["सबैले शुल्क तिर्नुपर्छ"],
        expected_lang="nepali",
        notes="Exception clause — must survive simplification.",
    ),
    # ── Dates & fees ──────────────────────────────────────────────
    GoldCase(
        case_id="np_dates_001",
        category="dates",
        level="simple",
        input_text=(
            "यस आवेदनको अन्तिम मिति २०८२/०१/०१ रहेको छ। मिति पछि प्राप्त "
            "आवेदन स्वीकार गरिने छैन।"
        ),
        key_facts=["२०८२", "०१", ["अन्तिम", "म्याद", "ढिलो", "स्वीकार गरिँदैन", "स्वीकार गरिने छैन"]],
        forbidden_facts=["२०८१", "म्याद थप"],
        expected_lang="nepali",
        notes="BS date preservation.",
    ),
    GoldCase(
        case_id="np_fees_001",
        category="fees",
        level="simple",
        input_text=(
            "नयाँ मोटरसाइकल दर्ता शुल्क घरेलु उत्पादनका लागि रु. २,५०० र "
            "आयातित मोटरसाइकलका लागि रु. ७,००० कायम गरिएको छ।"
        ),
        key_facts=["2,500", "7,000"],
        forbidden_facts=["5,000", "10,000"],
        expected_lang="nepali",
        language_independent_facts=True,
        notes="Two distinct fees — swap detection via forbidden facts.",
    ),
    # ── English → Nepali ──────────────────────────────────────────
    GoldCase(
        case_id="en_np_001",
        category="english_to_nepali",
        level="simple",
        input_text=(
            "The applicant must submit the completed form within 30 days "
            "of arrival. A fee of Rs. 1,000 applies for late submission. "
            "Forms submitted after 90 days will be rejected."
        ),
        key_facts=["30", "1,000", "90"],
        forbidden_facts=["60", "2,000"],
        expected_lang="any",
        language_independent_facts=True,
        notes="Numbers are language-independent truth anchors.",
    ),
    # ── Terminology ───────────────────────────────────────────────
    GoldCase(
        case_id="np_terminology_001",
        category="terminology",
        level="very_simple",
        input_text=(
            "आवेदकले स्वघोषित विवरण (self-declaration) बमोजिम आफ्नो "
            "वार्षिक आय उल्लेख गर्नुपर्नेछ। झूटो विवरण दिएमा दिइेको "
            "सहुलियत खारेज हुनेछ।"
        ),
        key_facts=["आय", "खारेज"],
        forbidden_facts=["कर मिनाहा"],
        expected_lang="nepali",
        notes="Technical term स्वघोषित must be explained, not dropped.",
    ),
    # ── Romanized & mixed ─────────────────────────────────────────
    GoldCase(
        case_id="np_original_001",
        category="legal_nepali",
        level="original",
        input_text=(
            "यस ऐनको दफा १२ बमोजिम अपील गर्न चाहने व्यक्तिले निर्णय "
            "भएको मितिले पैंतीस (३५) दिनभित्र अपील दर्ता गर्नुपर्नेछ।"
        ),
        key_facts=["३५", "अपील", "दर्ता"],
        forbidden_facts=["३०", "२१"],
        expected_lang="nepali",
        notes="Original-level: legal section + appeal window must be preserved verbatim.",
    ),
    GoldCase(
        case_id="np_original_002",
        category="fees",
        level="original",
        input_text=(
            "प्रतिलिपि प्रमाणीकरण शुल्क प्रति पृष्ठ रु. १० र प्रतिलिपि "
            "उपलब्ध गराउने कार्य पाँच कार्यदिनभित्र सम्पन्न गरिनेछ।"
        ),
        key_facts=["१०", "पाँच"],
        forbidden_facts=["२०", "सात"],
        expected_lang="nepali",
        notes="Original-level: per-page fee + turnaround days.",
    ),
    GoldCase(
        case_id="np_verysimple_002",
        category="formal_nepali",
        level="very_simple",
        input_text=(
            "उक्त व्यवस्था मिति २०८२/०५/०१ गतेदेखि कार्यान्वयनमा आउनेछ "
            "र यसअघि बुझाइएका निवेदनहरू तत्सम्म स्थगित गरिनेछन्।"
        ),
        key_facts=["२०८२", "०५", "०१"],
        forbidden_facts=["२०८१", "२०८३"],
        expected_lang="nepali",
        notes="Implementation date must survive very-simple compression.",
    ),
    GoldCase(
        case_id="romanized_002",
        category="romanized_nepali",
        level="simple",
        input_text=(
            "Malai yo notice bujhaidiu — license renew garna kati "
            "jhulkiyeko chha? Fine ekchin ma tirne ho ki mahina ma "
            "hisab huncha?"
        ),
        key_facts=[["महिना", "mahina", "month", "monthly", "मासिक"], ["एक", "1", "ek"]],
        forbidden_facts=["हप्ता", "बर्ष"],
        expected_lang="any",
        notes=(
            "Romanized question about a per-month penalty; the fee/unit "
            "anchor (महिना) must be preserved whatever the answer language."),
    ),
    GoldCase(
        case_id="en_np_002",
        category="english_to_nepali",
        level="simple",
        input_text=(
            "Only the district office accepts walk-in applications on "
            "Sundays. Online applicants must book an appointment at "
            "least 3 days in advance."
        ),
        key_facts=["3", "Sundays", ["आइत", "Sunday"]],
        forbidden_facts=["7", "Saturdays"],
        expected_lang="any",
        language_independent_facts=True,
        notes="Exception day + numeric lead time in English source.",
    ),
    GoldCase(
        case_id="romanized_001",
        category="romanized_nepali",
        level="simple",
        input_text=(
            "Yo form bharaufharka lagi citizenship certificate ra "
            "Rs. 300 tirnu parcha. Form haru sadharantah jethi din "
            "bhitra process huncha."
        ),
        key_facts=["300", "citizenship"],
        forbidden_facts=["500", "1500"],
        expected_lang="any",
        language_independent_facts=True,
        notes="Romanized question with embedded fee.",
    ),
    GoldCase(
        case_id="mixed_001",
        category="mixed",
        level="simple",
        input_text=(
            "ट्राफिक नियम उल्लंघनमा जरिवाना Rs. 500 देखि Rs. 2,000 सम्म "
            "हुनसक्नेछ, depending on the violation type. बारम्बार "
            "उल्लंघन गर्ने चालकको लाइसेन्स खारेज हुनसक्छ।"
        ),
        key_facts=["500", "2,000", ["खारेज", "कब्जा", "रद्द", "सस्पेन्ड", "cancelled", "revoked", "suspend"]],
        forbidden_facts=["5,000"],
        expected_lang="any",
        language_independent_facts=True,
        notes="Mixed-script penalty range + consequence.",
    ),
]


def normalized(text: str) -> str:
    """Normalize for fact checking: casefold + whitespace fold."""
    import re
    return re.sub(r"\s+", " ", text).casefold()


def check_case_facts(output: str, case: GoldCase) -> dict:
    """Deterministic fact checking of an explanation against gold data.

    Returns {missing_facts, forbidden_found, passed}.
    Language-independent numeric facts are checked on ASCII-normalized
    digits so Devanagari renderings still count.
    """
    from action_extractor import normalize_digits

    out_norm = normalized(output)
    out_digits = normalized(normalize_digits(output))

    missing = []
    for fact in case.key_facts:
        alternatives = fact if isinstance(fact, (list, tuple)) else [fact]
        ok = False
        for alt in alternatives:
            a = normalized(alt)
            if a in out_norm:
                ok = True
                break
            if case.language_independent_facts:
                a_digits = normalized(normalize_digits(alt))
                if a_digits in out_digits:
                    ok = True
                    break
        if not ok:
            missing.append("/".join(str(a) for a in alternatives))

    forbidden = [f for f in case.forbidden_facts if normalized(f) in out_norm]

    # Sentence-level negation guard: a sentence using the noun phrase must
    # also negate it somehow, or the model flipped the meaning.
    sentences = [s for s in re.split(r"[।\.\!?]+", output) if s.strip()]
    for affirm, markers in case.negation_guards:
        affirm_n = normalized(affirm)
        marker_ns = [normalized(m) for m in markers]
        for sent in sentences:
            if affirm_n not in normalized(sent):
                continue
            if not any(m in normalized(sent) for m in marker_ns):
                forbidden.append(
                    f"[negation dropped] '{affirm}' appears without any of "
                    f"{markers} in: '{sent.strip()[:60]}…'")
                break

    return {
        "missing_facts": missing,
        "forbidden_found": forbidden,
        "passed": not missing and not forbidden,
    }
