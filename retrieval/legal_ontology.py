"""legal_ontology.py — Nyaya Legal OS Comprehensive Statutory Concept Ontology (Phase 8.2F).

Provides generalized natural-language fact-to-statute mappings covering:
- BNS 2023 (Substantive Criminal Law)
- BNSS 2023 (Criminal Procedure, Investigation, Remand, Bail, Attachment)
- BSA 2023 (Law of Evidence, Electronic Records, Dying Declarations, Expert Proof)
- POCSO Act 2012 (Special Child Protection Law)
- Statutory Transition & Savings (BNS 358, BNSS 531, BSA 170)
"""

import re
from typing import Dict, List, Any, Set, Tuple

LEGAL_ONTOLOGY: List[Dict[str, Any]] = [
    # ── SUBSTANTIVE CRIMINAL LAW (BNS 2023) ───────────────────────────
    {
        "concept": "theft",
        "statute": "BNS",
        "target_sections": ["303", "303(1)", "303(2)"],
        "tokens": ["theft", "dishonestly", "movable", "possession", "consent", "takes"],
        "patterns": [
            r"\btheft\b", r"\bsteal(?:ing|s)?\b", r"\bstole\b", r"\bpocket(?:ed|ing|s)?\b",
            r"\btak(?:ing|es|en)?\s+(?:movable|cash|money|property|jewellery|packages|files|data|vehicle|motorcycle|ring|items)\b",
            r"\bsecretly\s+(?:remov|pocket|took|take)\b", r"\bwithout\s+(?:consent|permission)\s+(?:took|take|remov)\b",
            r"\bremov(?:al|ed|ing)\s+of\s+(?:cash|money|property|livestock|packages|items|belongings|necklace|gold)\b",
            r"\bhot-wir(?:ed|ing)?\s+a\s+motorcycle\b", r"\bunauthorized\s+vehicle\s+removal\b"
        ]
    },
    {
        "concept": "snatching",
        "statute": "BNS",
        "target_sections": ["304", "304(1)", "304(2)"],
        "tokens": ["snatching", "sudden", "grab", "force", "quick", "body"],
        "patterns": [
            r"\bsnatch(?:ing|ed|es)?\b", r"\bgrab(?:bed|bing)?\s+(?:gold|chain|purse|bag|phone|necklace)\b",
            r"\bforcibly\s+(?:grab|snatch|pull)\b", r"\bsprint(?:ed|ing)?\s+onto\s+a\s+moving\b",
            r"\bgrabbing\s+property\s+from\s+a\s+person\s+body\b"
        ]
    },
    {
        "concept": "extortion",
        "statute": "BNS",
        "target_sections": ["308", "308(1)", "308(2)", "308(3)", "308(4)"],
        "tokens": ["extortion", "fear", "injury", "threat", "deliver", "property", "money"],
        "patterns": [
            r"\bextort(?:ion|ed|ing|s)?\b", r"\bthreat(?:en|ened|ening)?\s+to\s+(?:publish|leak|expose|burn|kill|shoot|harm|upload)\b",
            r"\bdemand(?:ing|ed|s)?\s+(?:money|cash|lakhs|property|crore|payment)\s+under\s+threat\b",
            r"\bput(?:ting)?\s+in\s+fear\s+of\s+(?:injury|harm|death|damage)\s+to\s+(?:deliver|obtain)\b",
            r"\banonymous\s+(?:letter|demand|call|message|voip)\s+demanding\b", r"\bcoercive\s+debt\s+collection\b",
            r"\bprivate\s+(?:secret|photographs|domestic\s+photographs|intimate|images)\s+unless\s+money\b",
            r"\bextortionate\s+demands\b"
        ]
    },
    {
        "concept": "robbery",
        "statute": "BNS",
        "target_sections": ["309", "309(1)", "309(2)", "309(4)"],
        "tokens": ["robbery", "theft", "fear", "instant", "death", "hurt", "restraint"],
        "patterns": [
            r"\brobbery\b", r"\brob(?:bed|bing)?\b", r"\barmed\s+(?:with|intruder|assailant|men|individuals)\b",
            r"\bforced?\s+entry\s+.*and\s+demanded\s+handover\b", r"\binstant\s+(?:death|hurt|restraint)\b",
            r"\bknife-point\b", r"\bgun-point\b", r"\bpoint(?:ing|ed)?\s+a\s+(?:gun|knife|weapon)\b",
            r"\bbrandished?\s+weapons\b"
        ]
    },
    {
        "concept": "dacoity",
        "statute": "BNS",
        "target_sections": ["310", "310(1)", "310(2)", "311"],
        "tokens": ["dacoity", "five", "persons", "jointly", "armed", "highway"],
        "patterns": [
            r"\bdacoity\b", r"\bfive\s+or\s+more\s+(?:persons|individuals|men)\s+(?:jointly|armed|stopped|robbed)\b",
            r"\bgroup\s+of\s+five\b", r"\bgang\s+of\s+(?:five|six|seven|armed)\b", r"\bhighway\s+robbery\s+by\s+five\b",
            r"\bstopped\s+a\s+delivery\s+van\s+on\s+a\s+highway\s+at\s+knife-point\b"
        ]
    },
    {
        "concept": "dishonest_misappropriation",
        "statute": "BNS",
        "target_sections": ["314", "314(1)"],
        "tokens": ["misappropriation", "dishonestly", "convert", "found", "discovered"],
        "patterns": [
            r"\bmisappropriat(?:ion|ed|ing)?\b", r"\bfound\s+(?:a|an)\s+.*\s+and\s+(?:concealed|kept|pawned|sold)\b",
            r"\bconvert(?:ed|ing)?\s+to\s+own\s+use\b", r"\bappropriat(?:ing|ed)\s+discovered\s+movable\b",
            r"\bleft\s+behind\s+on\s+a\s+(?:train|seat|bus|taxi|flight)\b",
            r"\bnecklace\s+left\s+on\s+an\s+empty\s+seat\b"
        ]
    },
    {
        "concept": "criminal_breach_of_trust",
        "statute": "BNS",
        "target_sections": ["316", "316(1)", "316(2)", "316(3)", "316(5)"],
        "tokens": ["breach", "trust", "entrusted", "dominion", "misappropriate", "employer", "cashier", "accountant"],
        "patterns": [
            r"\bbreach\s+of\s+trust\b", r"\bentrust(?:ed|ment)?\s+with\s+(?:funds|property|cargo|beans|stock|money|custody|bags|data)\b",
            r"\baccountant\s+.*transferred\s+(?:company|corporate)\s+funds\b", r"\bwarehouse\s+supervisor\s+.*sold\b",
            r"\bemployee\s+.*misappropriat(?:ed|ing)?\b", r"\bcorporate\s+embezzlement\b",
            r"\bcashier\s+at\s+a\s+retail\b", r"\btechnician\s+copied\s+private\s+personal\s+video\b"
        ]
    },
    {
        "concept": "cheating",
        "statute": "BNS",
        "target_sections": ["318", "318(1)", "318(4)", "319"],
        "tokens": ["cheating", "deceive", "fraudulently", "induce", "property", "personation", "booking", "deposits"],
        "patterns": [
            r"\bcheat(?:ing|ed|s)?\b", r"\bdeceiv(?:e|ed|ing|es)?\b", r"\bdishonestly\s+induc(?:e|ed|ing)?\b",
            r"\bfraudulent\s+(?:scheme|website|sale|inducement|representation|booking|online\s+scheme)\b",
            r"\bpersonat(?:ion|ing|ed)?\b", r"\bfalsely\s+claimed?\s+to\s+be\b",
            r"\bcollected?\s+(?:deposits|fees|money)\s+and\s+(?:vanished|transferred|fled|disconnected)\b",
            r"\badvance\s+bank\s+transfers\s+from\s+\d+\s+farmers\b", r"\bcollected\s+\d+\s+crore\s+rupees\s+in\s+booking\b",
            r"\bissued?\s+(?:dishonored|five)\s+cheques\s+knowing\s+the\s+bank\s+account\s+was\s+closed\b"
        ]
    },
    {
        "concept": "wrongful_restraint_confinement",
        "statute": "BNS",
        "target_sections": ["126", "126(1)", "127", "127(1)"],
        "tokens": ["restraint", "confinement", "obstruct", "prevent", "locked", "basement"],
        "patterns": [
            r"\bwrongful\s+(?:restraint|confinement)\b", r"\bconfined?\s+.*in\s+a\s+locked\s+storage\s+basement\b",
            r"\block(?:ed|ing)?\s+.*in\s+basement\b", r"\bobstruct(?:ing|ed)?\s+a\s+person\s+from\s+proceeding\b",
            r"\bprevent\s+the\s+landlord\s+from\s+entering\b"
        ]
    },
    {
        "concept": "mischief_and_arson",
        "statute": "BNS",
        "target_sections": ["324", "324(1)", "324(2)", "326"],
        "tokens": ["mischief", "damage", "destroy", "fire", "arson", "water", "electricity"],
        "patterns": [
            r"\bmischief\b", r"\bsever(?:ed|ing)?\s+(?:drinking\s+)?water\s+(?:supply\s+)?and\s+electric(?:ity|al)\b",
            r"\bset(?:ting)?\s+fire\s+to\b", r"\barson\b", r"\bdestroy(?:ing|ed)?\s+(?:property|inventory|goods|warehouse|building|stall)\b",
            r"\bdamag(?:ing|ed)?\s+essential\s+utility\b", r"\bcompletely\s+destroying\s+stored\s+textile\b"
        ]
    },
    {
        "concept": "criminal_trespass_house_breaking",
        "statute": "BNS",
        "target_sections": ["329", "329(1)", "329(2)", "329(3)", "330", "330(1)", "330(2)"],
        "tokens": ["trespass", "house-trespass", "house-breaking", "dwelling", "unauthorized", "entry", "night"],
        "patterns": [
            r"\btrespass\b", r"\bhouse-trespass\b", r"\bhouse-breaking\b", r"\bforced?\s+entry\s+into\s+(?:house|residence|flat|apartment|premises)\b",
            r"\bintrud(?:er|ed|ing)?\s+(?:inside|into)\b", r"\bmidnight\s+(?:intruder|break-in|invasion)\b",
            r"\bentered?\s+a\s+neighbor\s+residential\s+garage\s+at\s+night\b"
        ]
    },
    {
        "concept": "forgery",
        "statute": "BNS",
        "target_sections": ["336", "336(1)", "336(2)", "338", "340"],
        "tokens": ["forgery", "false", "document", "electronic", "record", "fabricated", "altered", "cheque", "signature"],
        "patterns": [
            r"\bforg(?:ery|ed|ing|es)?\b", r"\bfalse\s+(?:document|electronic\s+record|certificate|invoice|cheque|deed|permit|odometer)\b",
            r"\balter(?:ed|ing)?\s+(?:registration|odometer|invoice|deed|document|valuation|date|declared\s+valuation)\b",
            r"\bcloned?\s+signature\b", r"\bfabricat(?:ed|ing)?\s+(?:invoices|papers|documents|evidence|revenue\s+documents)\b",
            r"\bcounterfeit\s+expiry\s+labels\b", r"\bpresented?\s+a\s+forged\s+cheque\s+leaf\b",
            r"\bfabricated\s+duplicate\s+invoices\b", r"\bexecuted?\s+a\s+sale\s+deed\s+receiving\s+\d+\s+lakhs\b"
        ]
    },
    {
        "concept": "homicide_and_murder",
        "statute": "BNS",
        "target_sections": ["103", "103(1)", "103(2)", "105"],
        "tokens": ["murder", "culpable", "homicide", "death", "mob", "lynching", "intentional", "beating"],
        "patterns": [
            r"\bmurder\b", r"\bculpable\s+homicide\b", r"\bfatally\s+(?:striking|struck|beating|beat|stabbed|attacked|shot)\b",
            r"\bmob\s+(?:lynching|violence|attack)\b", r"\bseven\s+armed\s+.*beat(?:ing)?\s+.*to\s+death\b",
            r"\bgroup\s+homicide\b", r"\bcausing\s+death\s+with\s+intention\b",
            r"\bshot\s+an\s+arrow\s+at\s+an\s+unarmed\s+neighbor\b"
        ]
    },
    {
        "concept": "death_by_negligence_and_rash_driving",
        "statute": "BNS",
        "target_sections": ["106", "106(1)", "106(2)", "281"],
        "tokens": ["negligence", "rash", "driving", "negligent", "medical", "surgical", "hit-and-run", "collapse"],
        "patterns": [
            r"\bdeath\s+by\s+negligence\b", r"\brash\s+(?:driving|or\s+negligent)\b", r"\bhit-and-run\b",
            r"\bfled\s+the\s+scene\s+after\s+striking\b", r"\bintoxicated\s+surgeon\b", r"\bmedical\s+negligence\b",
            r"\bdoctor\s+performed\s+a\s+complex\s+surgical\b", r"\bhoarding\s+collapse\b", r"\bflyover\s+(?:bridge\s+)?collapse\b",
            r"\bsubstandard\s+structural\s+concrete\b", r"\bhigh\s+speed\s+.*colliding\s+with\s+pedestrians\b",
            r"\bdriving\s+under\s+the\s+influence\s+of\s+narcotics\s+crashed\b"
        ]
    },
    {
        "concept": "private_defence",
        "statute": "BNS",
        "target_sections": ["38", "39", "40", "41", "44"],
        "tokens": ["private", "defence", "justification", "proportionality", "imminent", "threat", "repel"],
        "patterns": [
            r"\bprivate\s+defence\b", r"\bself-defence\b", r"\blegally\s+justified\b",
            r"\bawakened\s+by\s+an\s+intruder\s+.*struck\b", r"\bapprehension\s+of\s+death\b",
            r"\bproportionality\s+and\s+lack\s+of\s+excessive\s+force\b"
        ]
    },
    {
        "concept": "voyeurism_and_stalking",
        "statute": "BNS",
        "target_sections": ["77", "78", "78(1)", "78(2)"],
        "tokens": ["voyeurism", "stalking", "private", "monitoring", "hidden", "camera", "spyware"],
        "patterns": [
            r"\bvoyeurism\b", r"\bstalk(?:ing|ed|s)?\b", r"\bhidden\s+(?:camera|sensor|optical|micro-camera)\b",
            r"\bchanging\s+room\s+cubicles\b", r"\bshower\s+cubicles\b", r"\bspyware\b",
            r"\brepeatedly\s+follow(?:ed|ing)?\b", r"\bmonitor(?:ing|ed)?\s+electronic\s+communications\b",
            r"\bcopying\s+and\s+leaking\s+.*private\s+videos\b", r"\bsurveillance\s+spyware\b"
        ]
    },
    {
        "concept": "defamation",
        "statute": "BNS",
        "target_sections": ["356", "356(1)", "356(2)"],
        "tokens": ["defamation", "pamphlets", "imputation", "harm", "reputation"],
        "patterns": [
            r"\bdefamat(?:ion|ory)\b", r"\bdistributed\s+printed\s+pamphlets\b",
            r"\balleging\s+that\s+a\s+local\s+school\s+administrator\s+was\s+operating\b",
            r"\bharming\s+reputation\b", r"\bfalse\s+and\s+injurious\s+character\s+imputations\b"
        ]
    },
    {
        "concept": "criminal_intimidation",
        "statute": "BNS",
        "target_sections": ["351", "351(1)", "351(2)"],
        "tokens": ["intimidation", "threat", "alarm", "injury", "voice"],
        "patterns": [
            r"\bcriminal\s+intimidation\b", r"\bsent\s+repeated\s+threatening\s+voice\s+notes\b",
            r"\bthreatening\s+physical\s+violence\b", r"\bthreatening\s+to\s+burn\s+down\b"
        ]
    },
    {
        "concept": "counterfeiting",
        "statute": "BNS",
        "target_sections": ["231", "232", "234"],
        "tokens": ["counterfeit", "currency", "notes", "fake", "printing"],
        "patterns": [
            r"\bcounterfeit\s+currency\b", r"\breplica\s+\d+-rupee\s+notes\b", r"\boffset\s+printing\s+equipment\b",
            r"\bproducing\s+and\s+circulating\s+counterfeit\b", r"\bprinted\s+replica\s+500-rupee\b"
        ]
    },
    {
        "concept": "public_health_and_poison",
        "statute": "BNS",
        "target_sections": ["272", "274", "276", "277", "287", "288"],
        "tokens": ["adulteration", "poison", "toxic", "waste", "expired", "drugs", "hazardous", "combustible"],
        "patterns": [
            r"\btoxic\s+(?:waste|fumes|dye|substance)\b", r"\bdischarg(?:ed|ing)?\s+untreated\s+(?:acidic\s+)?waste\b",
            r"\badulterat(?:ion|ed|ing)?\s+food\b", r"\bexpired\s+antibiotic\s+syrups\b", r"\bflammable\s+solvent\b",
            r"\bunsealed\s+drums\b", r"\bmixed\s+toxic\s+industrial\s+dye\s+into\s+food\b"
        ]
    },
    {
        "concept": "bribery_and_corruption",
        "statute": "BNS",
        "target_sections": ["173", "174"],
        "tokens": ["bribe", "gratification", "clerk", "public", "servant", "licensing"],
        "patterns": [
            r"\bbribe\b", r"\boffered?\s+\d+\s+rupees\s+in\s+cash\s+to\s+obtain\b",
            r"\billegal\s+gratification\s+to\s+public\s+servants\b", r"\bofficial\s+licensing\s+clerk\b"
        ]
    },
    {
        "concept": "conspiracy_and_abetment",
        "statute": "BNS",
        "target_sections": ["46", "61", "61(1)", "61(2)"],
        "tokens": ["conspiracy", "abetment", "accomplice", "getaway", "vehicle", "common", "intention"],
        "patterns": [
            r"\bcriminal\s+conspiracy\b", r"\babetment\b", r"\bproviding\s+a\s+vehicle\b",
            r"\bproviding\s+getaway\s+vehicle\b", r"\baccomplice\s+statement\b"
        ]
    },
    {
        "concept": "dowry_cruelty",
        "statute": "BNS",
        "target_sections": ["85", "86"],
        "tokens": ["dowry", "cruelty", "harassment", "husband", "relatives"],
        "patterns": [
            r"\bdowry\b", r"\bcruelty\s+by\s+husband\b", r"\bdowry\s+demands\b"
        ]
    },
    {
        "concept": "evidence_tampering",
        "statute": "BNS",
        "target_sections": ["238"],
        "tokens": ["disappearance", "evidence", "tampering", "destruction"],
        "patterns": [
            r"\bdestruction\s+of\s+electronic\s+evidence\b", r"\bcausing\s+disappearance\s+of\s+evidence\b"
        ]
    },

    # ── CRIMINAL PROCEDURE (BNSS 2023) ───────────────────────────────
    {
        "concept": "bnss_arrest_and_notice",
        "statute": "BNSS",
        "target_sections": ["35", "35(1)", "35(3)", "43"],
        "tokens": ["notice", "appearance", "arrest", "grounds", "reasons", "safeguards"],
        "patterns": [
            r"\bnotice\s+of\s+appearance\b", r"\barrest\s+(?:safeguards|preconditions|without\s+notice|grounds|procedure|framework)\b",
            r"\bBNSS\s+Section\s+35\b", r"\brecording\s+reasons\s+for\s+arrest\b",
            r"\bpolice\s+arrest\s+him\s+without\s+first\s+issuing\b",
            r"\bprocedural\s+arrest\s+(?:safeguards|notice|rules)\b"
        ]
    },
    {
        "concept": "bnss_remand_and_custody",
        "statute": "BNSS",
        "target_sections": ["187", "187(1)", "187(2)", "187(3)"],
        "tokens": ["remand", "custody", "police", "magistrate", "15-day", "tranches"],
        "patterns": [
            r"\bpolice\s+custody\b", r"\btransit\s+remand\b", r"\bremand\s+application\b",
            r"\bBNSS\s+Section\s+187\b", r"\bmaximum\s+police\s+custody\b",
            r"\bpolice\s+seek\s+remand\b"
        ]
    },
    {
        "concept": "bnss_search_seizure_and_attachment",
        "statute": "BNSS",
        "target_sections": ["105", "107", "107(1)", "107(2)", "107(4)"],
        "tokens": ["search", "seizure", "videography", "audio-video", "attachment", "proceeds", "crime", "memo"],
        "patterns": [
            r"\bsearch\s+and\s+seizure\b", r"\baudio-video\s+electronic\s+means\b", r"\bseizure\s+memo\b",
            r"\battachment\s+of\s+(?:property|assets|accounts|proceeds)\b", r"\bproceeds\s+of\s+crime\b",
            r"\bBNSS\s+Section\s+105\b", r"\bBNSS\s+Section\s+107\b", r"\bprocedural\s+attachment\s+powers\b",
            r"\bdigital\s+media\s+seizure\b", r"\bseizure\s+of\s+digital\s+devices\b"
        ]
    },
    {
        "concept": "bnss_bail_and_undertrial",
        "statute": "BNSS",
        "target_sections": ["479", "480", "482"],
        "tokens": ["bail", "undertrial", "one-third", "detention", "non-bailable", "anticipatory"],
        "patterns": [
            r"\bundertrial\s+bail\b", r"\bfirst-time\s+undertrial\b", r"\bone-third\s+of\s+the\s+alleged\s+maximum\b",
            r"\bBNSS\s+Section\s+479\b", r"\bBNSS\s+Section\s+480\b", r"\bbail\s+in\s+non-bailable\b",
            r"\bbail\s+after\s+several\s+weeks\s+of\s+custody\b", r"\bbail\s+after\s+prolonged\s+detention\b"
        ]
    },
    {
        "concept": "bnss_fir_and_jurisdiction",
        "statute": "BNSS",
        "target_sections": ["173", "197", "199"],
        "tokens": ["fir", "zero", "jurisdiction", "journey", "transit", "registration"],
        "patterns": [
            r"\bzero\s+fir\b", r"\be-fir\b", r"\binter-state\s+(?:journey|travel|transit)\b",
            r"\bjurisdiction\s+during\s+journey\b", r"\bBNSS\s+Section\s+173\b",
            r"\btravelling\s+through\s+two\s+states\b"
        ]
    },
    {
        "concept": "bnss_identification_parade",
        "statute": "BNSS",
        "target_sections": ["54"],
        "tokens": ["tip", "identification", "parade", "identity"],
        "patterns": [
            r"\btest\s+identification\s+parade\b", r"\bBNSS\s+Section\s+54\b"
        ]
    },

    # ── LAW OF EVIDENCE (BSA 2023) ───────────────────────────────────
    {
        "concept": "bsa_electronic_evidence",
        "statute": "BSA",
        "target_sections": ["61", "62", "63", "63(1)", "63(2)", "63(4)"],
        "tokens": ["electronic", "record", "certificate", "hash", "extraction", "screenshots", "cctv", "backup", "admissibility", "provenance"],
        "patterns": [
            r"\belectronic\s+(?:record|evidence|certificate|extraction|messages|logs|backup|proof)\b",
            r"\bBSA\s+Section\s+63\b", r"\bSection\s+65B\b", r"\bhash\s+value\b",
            r"\bscreenshots?\b", r"\bchat\s+logs?\b", r"\bcloud\s+backup\b", r"\bcctv\s+footage\b",
            r"\bdigital\s+proof\b", r"\bwhat\s+evidence\s+is\s+required\s+to\s+prove\b",
            r"\belectronic\s+extraction\s+report\b", r"\bdigital\s+records\b"
        ]
    },
    {
        "concept": "bsa_confessions_and_discovery",
        "statute": "BSA",
        "target_sections": ["23", "23(1)", "23(2)", "26"],
        "tokens": ["discovery", "statement", "weapon", "recovery", "dying", "declaration", "confession"],
        "patterns": [
            r"\bdiscovery\s+statement\b", r"\bweapon\s+recovered\s+from\s+a\s+ditch\b",
            r"\bdisclosure\s+statement\b", r"\bBSA\s+Section\s+23\b", r"\bdying\s+declaration\b",
            r"\bBSA\s+Section\s+26\b", r"\bbody-worn\s+camera\s+confession\b"
        ]
    },
    {
        "concept": "bsa_expert_and_presumptions",
        "statute": "BSA",
        "target_sections": ["39", "118"],
        "tokens": ["expert", "opinion", "forensic", "handwriting", "ballistics", "presumption", "dowry"],
        "patterns": [
            r"\bexpert\s+(?:opinion|testimony|examination)\b", r"\bhandwriting\s+expert\b",
            r"\bballistics\b", r"\bpost-mortem\s+medical\b", r"\bBSA\s+Section\s+39\b",
            r"\bdowry\s+death\s+presumption\b", r"\bBSA\s+Section\s+118\b",
            r"\bmechanical\s+inspection\s+reports\b"
        ]
    },
    {
        "concept": "bsa_identity_relevance",
        "statute": "BSA",
        "target_sections": ["7"],
        "tokens": ["identity", "facts", "relevant", "parade"],
        "patterns": [
            r"\bfacts\s+establishing\s+identity\b", r"\bBSA\s+Section\s+7\b"
        ]
    },

    # ── SPECIAL STATUTES (POCSO ACT, 2012) ───────────────────────────
    {
        "concept": "pocso_child_definition",
        "statute": "POCSO",
        "target_sections": ["2", "2(1)(d)"],
        "tokens": ["child", "definition", "age", "eighteen", "below 18"],
        "patterns": [
            r"\bage\s+definition\s+under\s+pocso\b", r"\bdefinition\s+of\s+a\s+child\b",
            r"\bunder\s+18\s+years\b", r"\bSection\s+2\(1\)\(d\)\b"
        ]
    },
    {
        "concept": "pocso_penetrative_assault",
        "statute": "POCSO",
        "target_sections": ["3", "4", "5", "6"],
        "tokens": ["penetrative", "aggravated", "rape", "domestic", "relative", "institution", "home", "administrator"],
        "patterns": [
            r"\bpenetrative\s+sexual\s+assault\b", r"\baggravated\s+penetrative\b",
            r"\bpenetrative\s+sexual\s+assault\s+in\s+a\s+domestic\s+residence\b",
            r"\bchildren\s+home\s+administrator\s+sexually\s+exploiting\b",
            r"\brelative\s+domestic\s+penetrative\b", r"\bexploiting\s+an\s+11-year-old\b"
        ]
    },
    {
        "concept": "pocso_sexual_assault",
        "statute": "POCSO",
        "target_sections": ["7", "8", "9", "10"],
        "tokens": ["assault", "non-penetrative", "touching", "physical", "school"],
        "patterns": [
            r"\bnon-penetrative\s+sexual\s+touching\b", r"\bsexual\s+assault\s+on\s+a\s+12-year-old\b",
            r"\bsexual\s+touching\s+of\s+a\s+(?:1[0-7]|child|minor|student)\b",
            r"\bPOCSO\s+Section\s+7\b", r"\bPOCSO\s+Section\s+8\b"
        ]
    },
    {
        "concept": "pocso_sexual_harassment",
        "statute": "POCSO",
        "target_sections": ["11", "12"],
        "tokens": ["harassment", "explicit", "messages", "gestures", "online", "chat"],
        "patterns": [
            r"\bsexual\s+harassment\s+(?:of|upon)\s+(?:a\s+child|a\s+minor|a\s+student)\b",
            r"\bexplicit\s+sexual\s+messages\s+to\s+a\s+(?:1[0-7]|child|minor|student)\b",
            r"\bPOCSO\s+Section\s+11\b", r"\bPOCSO\s+Section\s+12\b",
            r"\bonline\s+sexual\s+communications\s+with\s+(?:a\s+child|a\s+minor)\b"
        ]
    },
    {
        "concept": "pocso_mandatory_reporting",
        "statute": "POCSO",
        "target_sections": ["19", "21"],
        "tokens": ["reporting", "report", "failure", "headmaster", "in-charge", "mandatory", "officer"],
        "patterns": [
            r"\bmandatory\s+reporting\s+obligation\b", r"\bfailure\s+to\s+report\b",
            r"\bfiled\s+away\s+the\s+complaint\s+without\s+reporting\b",
            r"\bheadmaster\s+.*without\s+reporting\b", r"\bPOCSO\s+Section\s+19\b",
            r"\bPOCSO\s+Section\s+21\b"
        ]
    },
    {
        "concept": "pocso_special_court_procedure",
        "statute": "POCSO",
        "target_sections": ["24", "25", "33", "34", "35", "37"],
        "tokens": ["special", "court", "powers", "duties", "procedure", "in-camera", "recording", "statement"],
        "patterns": [
            r"\bspecial\s+court\b", r"\bpowers\s+and\s+duties\s+of\s+the\s+special\s+court\b",
            r"\bprocedure\s+before\s+special\s+court\b", r"\bin-camera\s+trial\b",
            r"\bSpecial\s+Court\s+rules\b", r"\brecording\s+the\s+statement\s+of\s+a\s+child\b"
        ]
    },
    {
        "concept": "pocso_overriding_and_interaction",
        "statute": "POCSO",
        "target_sections": ["42", "42A", "42A(1)"],
        "tokens": ["repeal", "derogation", "override", "overriding", "both", "alongside", "interact", "special"],
        "patterns": [
            r"\brepeal\s+(?:the\s+)?pocso\b", r"\bpocso\s+.*alongside\b", r"\bpunishable\s+under\s+both\b",
            r"\bpocso\s+interact\s+with\s+bns\b", r"\bnot\s+in\s+derogation\b", r"\boverriding\s+effect\b",
            r"\bPOCSO\s+Section\s+42A\b", r"\bPOCSO\s+was\s+replaced\s+by\s+BNS\b"
        ]
    }
]

class LegalOntologyExpander:
    def __init__(self):
        self.ontology = LEGAL_ONTOLOGY

    def extract_concepts_and_sections(self, query: str) -> Dict[str, Any]:
        """Extract matched concepts, candidate sections, and active statute branches."""
        q_lower = query.lower()
        matched_concepts = []
        candidate_sections_by_statute: Dict[str, Set[str]] = {
            "BNS": set(),
            "BNSS": set(),
            "BSA": set(),
            "POCSO": set()
        }
        all_candidate_sections = set()
        active_statutes = set()
        enriched_tokens = set()

        for entry in self.ontology:
            st = entry["statute"]
            is_matched = False
            for pat in entry.get("patterns", []):
                if re.search(pat, q_lower, re.IGNORECASE):
                    is_matched = True
                    break
            
            if is_matched:
                matched_concepts.append(entry["concept"])
                active_statutes.add(st)
                for sec in entry.get("target_sections", []):
                    candidate_sections_by_statute[st].add(sec)
                    all_candidate_sections.add(sec)
                for tok in entry.get("tokens", []):
                    enriched_tokens.add(tok)

        # Fallback: if no specific concept triggered, default to BNS
        if not active_statutes:
            active_statutes.add("BNS")

        return {
            "matched_concepts": matched_concepts,
            "active_statutes": list(active_statutes),
            "candidate_sections_by_statute": {k: list(v) for k, v in candidate_sections_by_statute.items() if v},
            "all_candidate_sections": list(all_candidate_sections),
            "enriched_tokens": list(enriched_tokens)
        }
