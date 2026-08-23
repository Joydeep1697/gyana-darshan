# legal_concept_expander.py — Legal Concept Expansion & Semantic Bridge Engine (Phase 8.2G Experimental)
#
# Objective:
# Map factual narrative phrases and common-language descriptions to authoritative statutory
# concepts and legal doctrine without benchmark hard-coding.
#
# Examples:
# - "secretly took cash without consent" -> dishonest taking, movable property, without consent, theft (BNS 303)
# - "falsified signature on property deed" -> false document, intent to cause damage, forgery (BNS 336)
# - "sent messages demanding money threatening harm" -> intentional putting in fear of injury, extortion (BNS 308)

import re
from typing import Dict, List, Any, Set, Tuple

CONCEPT_ONTOLOGY = {
    "theft": {
        "patterns": [
            r"secretly\s+(?:took|pocketed|stole|removed|carried\s+away)",
            r"dishonest(?:ly)?\s+(?:taking|removal|misappropriation)",
            r"without\s+(?:the\s+)?owner'?s?\s+consent",
            r"stole\s+(?:money|cash|goods|jewellery|property|vehicle|motorcycle)",
            r"pickpocketing|shoplifting|hot-wiring"
        ],
        "legal_terms": ["theft", "dishonestly takes movable property", "out of possession", "without consent", "section 303"],
        "statute": "BNS"
    },
    "snatching": {
        "patterns": [
            r"suddenly\s+(?:or\s+quickly\s+)?(?:grabbed|seized|snatched|pulled)",
            r"snatched\s+(?:a\s+)?(?:chain|purse|bag|phone|necklace)",
            r"forcibly\s+grabbed\s+and\s+fled"
        ],
        "legal_terms": ["snatching", "theft with sudden or quick seizure", "section 304"],
        "statute": "BNS"
    },
    "extortion": {
        "patterns": [
            r"threatening\s+to\s+(?:burn|harm|kill|expose|leak|ruin)",
            r"demand(?:ed|ing)?\s+(?:money|ransom|cash|protection\s+money)\s+under\s+threat",
            r"extort(?:ed|ion|ing)?",
            r"anonymous\s+(?:letters?|messages?)\s+demanding"
        ],
        "legal_terms": ["extortion", "intentionally puts any person in fear of any injury", "dishonestly induces delivery of property", "section 308"],
        "statute": "BNS"
    },
    "robbery_dacoity": {
        "patterns": [
            r"(?:armed\s+with\s+knives|guns|weapons)\s+broke\s+into",
            r"threatened\s+(?:with\s+instant\s+death|hurt|restraint)",
            r"group\s+home\s+invasion",
            r"five\s+or\s+more\s+persons\s+committing\s+robbery"
        ],
        "legal_terms": ["robbery", "dacoity", "in order to committing theft causes wrongful restraint or hurt", "section 309", "section 310"],
        "statute": "BNS"
    },
    "criminal_breach_of_trust": {
        "patterns": [
            r"entrusted\s+with\s+(?:property|funds|money|goods|inventory)",
            r"(?:accountant|cashier|supervisor|employee|director)\s+(?:diverted|misappropriated|pocketed|sold)",
            r"converted\s+to\s+(?:his\s+own|personal)\s+use",
            r"created\s+duplicate\s+invoices"
        ],
        "legal_terms": ["criminal breach of trust", "dishonest misappropriation by servant", "entrusted with property", "section 316"],
        "statute": "BNS"
    },
    "cheating_fraud": {
        "patterns": [
            r"deceived\s+(?:any\s+person|investors|buyers)",
            r"fraudulent(?:ly)?\s+(?:misrepresented|induced|sold|promised)",
            r"altered\s+(?:birth\s+certificate|pedigree|odometer|documents?)\s+to\s+misrepresent",
            r"fake\s+website|ponzi\s+scheme"
        ],
        "legal_terms": ["cheating", "fraudulent inducement to deliver property", "section 318"],
        "statute": "BNS"
    },
    "forgery": {
        "patterns": [
            r"forged\s+(?:signature|document|will|contract|certificate|seal)",
            r"created\s+(?:a\s+)?false\s+document",
            r"altered\s+(?:a\s+)?material\s+part\s+of\s+a\s+document",
            r"electronic\s+record\s+forgery"
        ],
        "legal_terms": ["forgery", "making false document", "forgery of valuable security", "section 336", "section 340"],
        "statute": "BNS"
    },
    "homicide_rash_driving": {
        "patterns": [
            r"(?:speeding|rash|negligent)\s+(?:driving|operating\s+vehicle)",
            r"fatal(?:ly)?\s+(?:struck|hit|collision|injured)",
            r"causing\s+death\s+by\s+negligence",
            r"hit\s+and\s+run"
        ],
        "legal_terms": ["causing death by negligence", "rash driving on public way", "section 106", "section 281"],
        "statute": "BNS"
    },
    "private_defence": {
        "patterns": [
            r"awakened\s+by\s+an\s+intruder\s+wielding",
            r"struck\s+(?:the\s+)?intruder\s+in\s+defence",
            r"reasonable\s+apprehension\s+of\s+death",
            r"repelling\s+(?:an\s+)?assault\s+or\s+attack"
        ],
        "legal_terms": ["right of private defence of body and property", "causing death in private defence", "section 38", "section 41", "section 44"],
        "statute": "BNS"
    },
    "stalking_voyeurism": {
        "patterns": [
            r"repeatedly\s+followed\s+(?:a\s+)?(?:woman|female|student)",
            r"concealed\s+(?:micro-)?camera|shower\s+cubicles?|changing\s+rooms?",
            r"monitoring\s+(?:the\s+)?internet\s+or\s+electronic\s+communication\s+of\s+a\s+woman",
            r"capturing\s+image\s+of\s+a\s+woman\s+engaging\s+in\s+private\s+act"
        ],
        "legal_terms": ["stalking", "voyeurism", "section 77", "section 78"],
        "statute": "BNS"
    },
    "pocso_offences": {
        "patterns": [
            r"minor|child|14-year-old|under\s+eighteen|school\s+student",
            r"explicit\s+(?:sexual\s+)?messages\s+to\s+a\s+child",
            r"sexual\s+assault\s+on\s+child",
            r"headmaster\s+failed\s+to\s+report\s+abuse"
        ],
        "legal_terms": ["sexual assault on child", "sexual harassment of child", "mandatory reporting of child sexual offence", "POCSO Section 11", "POCSO Section 12", "POCSO Section 19", "POCSO Section 21"],
        "statute": "POCSO"
    },
    "electronic_admissibility": {
        "patterns": [
            r"electronic\s+records?|cctv\s+footage|whatsapp\s+chats?|server\s+logs?",
            r"digital\s+evidence|extraction\s+report|hash\s+value",
            r"certificate\s+under\s+(?:section\s+63|section\s+65b)",
            r"admissibility\s+of\s+electronic\s+records"
        ],
        "legal_terms": ["admissibility of electronic records", "certificate for electronic evidence", "BSA Section 61", "BSA Section 63"],
        "statute": "BSA"
    },
    "arrest_remand_bail": {
        "patterns": [
            r"police\s+custody|magistrate\s+remand|15\s+days\s+remand",
            r"notice\s+of\s+appearance\s+under\s+section\s+35",
            r"undertrial\s+prisoner|maximum\s+period\s+of\s+detention|bail",
            r"search\s+and\s+seizure\s+videography"
        ],
        "legal_terms": ["notice of appearance", "police custody remand", "maximum period of detention for undertrials", "audio video electronic recording of search", "BNSS Section 35", "BNSS Section 105", "BNSS Section 187", "BNSS Section 479"],
        "statute": "BNSS"
    }
}

class LegalConceptExpander:
    """Expands factual narratives into precise statutory concepts and query terms."""

    def __init__(self):
        self.ontology = CONCEPT_ONTOLOGY

    def expand_query(self, query: str) -> Dict[str, Any]:
        """Produce expanded conceptual retrieval queries and detected concepts."""
        text_lower = query.lower()
        detected_concepts = []
        expanded_terms = []

        for concept_name, config in self.ontology.items():
            matched = False
            for pat in config["patterns"]:
                if re.search(pat, text_lower, re.IGNORECASE):
                    matched = True
                    break

            if matched:
                detected_concepts.append({
                    "concept": concept_name,
                    "statute": config["statute"],
                    "legal_terms": config["legal_terms"]
                })
                expanded_terms.extend(config["legal_terms"])

        # Construct expanded queries
        expanded_queries = [query]
        if expanded_terms:
            expanded_queries.append(" ".join(expanded_terms[:8]))

        confidence = min(1.0, len(detected_concepts) * 0.3 + (0.4 if detected_concepts else 0.1))

        return {
            "original_query": query,
            "concepts_detected": [c["concept"] for c in detected_concepts],
            "expanded_retrieval_queries": expanded_queries,
            "statute_hints": list(set(c["statute"] for c in detected_concepts)),
            "confidence": confidence
        }
