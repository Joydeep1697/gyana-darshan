# issue_decomposer.py — Legal Query Understanding & Issue Decomposition Engine (Phase 8.2G Experimental)
#
# Objective:
# Decompose complex, multi-issue legal queries and narrative fact patterns into discrete,
# typed legal issues with target candidate statutes and legal concepts.
#
# Rules:
# - Strictly generalizable: Derived from text semantics and legal taxonomy.
# - ZERO hard-coding by Case ID or query hash.
# - Supports issue types: SUBSTANTIVE_OFFENCE, CRIMINAL_PROCEDURE, BAIL, REMAND, ARREST,
#   EVIDENCE, ELECTRONIC_EVIDENCE, POCSO, SPECIAL_STATUTE, PRECEDENT, PENALTY, DEFENCE,
#   LIMITATION, MULTI_STATUTE.

import re
from typing import Dict, List, Any, Set, Optional

# Legal Issue Pattern Taxonomies with Regex Patterns for Robust Stem Matching
ISSUE_PATTERNS = {
    "ELECTRONIC_EVIDENCE": {
        "statutes": ["BSA"],
        "regex_patterns": [
            r"\belectronic\s+records?\b", r"\belectronic\s+evidence\b", r"\bdigital\s+records?\b",
            r"\bcctv\b", r"\bserver\s+logs?\b", r"\bemails?\b", r"\bwhatsapp\b", r"\bhard\s+drives?\b",
            r"\bdigital\s+media\b", r"\bcertificates?\b", r"\bsection\s+63\b", r"\bsection\s+65b\b",
            r"\badmissibility\s+of\s+electronic\b", r"\bcall\s+details?\b", r"\bcdr\b", r"\bmobile\s+phones?\b",
            r"\bextraction\s+reports?\b", r"\bhash\s+values?\b", r"\bdigital\s+data\b", r"\bpen\s+drives?\b"
        ]
    },
    "EVIDENCE": {
        "statutes": ["BSA"],
        "regex_patterns": [
            r"\bburden\s+of\s+proof\b", r"\bexpert\s+opinions?\b", r"\bforensic\s+reports?\b",
            r"\bmedical\s+evidence\b", r"\badmissions?\b", r"\bconfessions?\b", r"\bdying\s+declarations?\b",
            r"\btest\s+identification\b", r"\btip\b", r"\bprimary\s+evidence\b", r"\bsecondary\s+evidence\b",
            r"\boral\s+evidence\b", r"\bdocumentary\s+proof\b", r"\bleading\s+questions?\b", r"\bwitness(?:es)?\b",
            r"\bpresumptions?\b", r"\bcompetency\s+of\s+witness\b", r"\bproof\b", r"\bevidentiary\b"
        ]
    },
    "BAIL": {
        "statutes": ["BNSS"],
        "regex_patterns": [
            r"\bbail\b", r"\banticipatory\s+bail\b", r"\bregular\s+bail\b", r"\bdefault\s+bail\b",
            r"\bstatutory\s+bail\b", r"\bsection\s+479\b", r"\bsection\s+480\b", r"\bsection\s+482\b",
            r"\bsection\s+437\b", r"\bsection\s+438\b", r"\bsection\s+439\b", r"\bundertrial\b",
            r"\bbonds?\b", r"\bsuret(?:y|ies)\b", r"\bcancellation\s+of\s+bail\b", r"\bcustody\s+period\b",
            r"\bhalf\s+the\s+maximum\s+term\b", r"\bone-third\b"
        ]
    },
    "REMAND": {
        "statutes": ["BNSS"],
        "regex_patterns": [
            r"\bpolice\s+custody\b", r"\bremand\b", r"\bmagistrate\s+remand\b", r"\bjudicial\s+custody\b",
            r"\bsection\s+187\b", r"\bsection\s+167\b", r"\b15\s+days\b", r"\b60\s+days\b", r"\b90\s+days\b",
            r"\binitial\s+custody\b", r"\bextension\s+of\s+custody\b"
        ]
    },
    "ARREST": {
        "statutes": ["BNSS"],
        "regex_patterns": [
            r"\barrest(?:ed|ing|s)?\b", r"\bnotice\s+of\s+appearance\b", r"\bsection\s+35\b", r"\bsection\s+41a\b",
            r"\barrest\s+memos?\b", r"\bgrounds\s+of\s+arrest\b", r"\bintimation\s+to\s+relatives?\b",
            r"\bhandcuffing\b", r"\bmedical\s+examination\s+of\s+accused\b", r"\bprocedural\s+arrest\b"
        ]
    },
    "CRIMINAL_PROCEDURE": {
        "statutes": ["BNSS"],
        "regex_patterns": [
            r"\bfir\b", r"\bzero\s+fir\b", r"\bsection\s+173\b", r"\bsection\s+154\b", r"\binvestigat(?:ion|ing|or)\b",
            r"\bchargesheets?\b", r"\bpolice\s+reports?\b", r"\bsearch\s+and\s+seizure\b", r"\bseiz(?:ed|ing|ure)\b",
            r"\bsection\s+105\b", r"\bsection\s+107\b", r"\baudio\s+video\s+electronic\b", r"\bvideograph(?:y|ed)\b",
            r"\bcognizance\b", r"\binquir(?:y|ies)\b", r"\btrial\b", r"\bsummons?\b", r"\bwarrants?\b",
            r"\battachment\s+of\s+property\b", r"\bproceeds\s+of\s+crime\b", r"\bcommittal\b", r"\bdischarge\b",
            r"\bframing\s+of\s+charges?\b", r"\bprocedural\s+safeguards?\b"
        ]
    },
    "POCSO": {
        "statutes": ["POCSO"],
        "regex_patterns": [
            r"\bpocso\b", r"\bchild(?:ren)?\b", r"\bminor(?:s)?\b", r"\bunder\s+18\b", r"\bunder\s+eighteen\b",
            r"\b\d{1,2}-year-old\b", r"\bsexual\s+assault\b", r"\bpenetrative\s+sexual\s+assault\b",
            r"\baggravated\s+penetrative\b", r"\bsexual\s+harassment\s+of\s+child\b", r"\bsection\s+[468]\b",
            r"\bsection\s+1[0129]\b", r"\bsection\s+21\b", r"\bmandatory\s+reporting\b",
            r"\bchild\s+sexual\s+abuse\b", r"\bpornographic\s+material\b", r"\bspecial\s+courts?\b"
        ]
    },
    "DEFENCE": {
        "statutes": ["BNS"],
        "regex_patterns": [
            r"\bprivate\s+defence\b", r"\bself\s+defence\b", r"\bright\s+of\s+private\s+defence\b",
            r"\bsection\s+38\b", r"\bsection\s+41\b", r"\bsection\s+44\b", r"\bsection\s+96\b", r"\bsection\s+100\b",
            r"\breasonable\s+apprehension\b", r"\bcausing\s+death\s+in\s+defence\b", r"\bgeneral\s+exceptions?\b",
            r"\bunsoundness\s+of\s+mind\b", r"\bintoxication\b", r"\baccident\b", r"\binfanc(?:y)?\b", r"\bnecessity\b"
        ]
    },
    "STATUTORY_TRANSITION": {
        "statutes": ["BNS", "BNSS", "BSA"],
        "regex_patterns": [
            r"\breplace(?:d|s|ment)?\b", r"\bsubsumed?\b", r"\brepeal\s+and\s+savings?\b",
            r"\bsection\s+358\b", r"\bsection\s+531\b", r"\bsection\s+170\b",
            r"\btransition\s+law\b", r"\bpending\s+proceedings?\b", r"\bretrospective\b",
            r"\bprospective\b", r"\bcrpc\s+repealed\b", r"\bipc\s+repealed\b", r"\bevidence\s+act\s+replaced\b"
        ]
    },
    "SUBSTANTIVE_OFFENCE": {
        "statutes": ["BNS"],
        "regex_patterns": [
            r"\btheft\b", r"\bsnatching\b", r"\bextort(?:ion|ed|ing)?\b", r"\brobber(?:y|ies)\b", r"\bdacoit(?:y|ies)\b",
            r"\bcheat(?:ing|ed)?\b", r"\bfraud(?:ulent)?\b", r"\bforger(?:y|ies|ed)\b",
            r"\bcriminal\s+breach\s+of\s+trust\b", r"\bmisappropriat(?:ion|ed|ing)\b", r"\bmurder(?:ed)?\b",
            r"\bculpable\s+homicide\b", r"\bgrievous\s+hurt\b", r"\bsimple\s+hurt\b", r"\brash\s+driving\b",
            r"\bdeath\s+by\s+negligence\b", r"\bstalk(?:ing|ed)?\b", r"\bvoyeurism\b", r"\brape\b",
            r"\bgang\s+rape\b", r"\bunlawful\s+assembly\b", r"\bmob\s+lynching\b", r"\brioting\b",
            r"\bcriminal\s+intimidation\b", r"\bdefamat(?:ion|ory)\b", r"\bcounterfeit(?:ing|ed)?\b",
            r"\bmischief\b", r"\btrespass(?:ing)?\b", r"\bhousebreaking\b", r"\bkidnapp(?:ing|ed)\b",
            r"\babduct(?:ion|ed)?\b", r"\borgan\s+trafficking\b", r"\battempt\s+to\s+murder\b",
            r"\bconspirac(?:y)?\b", r"\babetment\b", r"\bsecretly\s+(?:took|pocketed|stole)\b",
            r"\bduplicate\s+invoices\b", r"\bfalsif(?:ied|ication)\b", r"\bunauthorized\s+transfer\b"
        ]
    }
}

class LegalIssueDecomposer:
    """Decomposes legal queries into discrete, typed legal issues with candidate statutes."""

    def __init__(self):
        self.issue_taxonomies = ISSUE_PATTERNS

    def decompose_query(self, query: str) -> Dict[str, Any]:
        """Analyze query text and extract discrete legal issues."""
        text_lower = query.lower()
        decomposed_issues = []
        all_candidate_statutes = set()

        for issue_type, config in self.issue_taxonomies.items():
            matched_keywords = []
            for pat in config["regex_patterns"]:
                m = re.findall(pat, text_lower)
                if m:
                    matched_keywords.extend(m if isinstance(m[0], str) else [item for tup in m for item in tup if item])

            if matched_keywords:
                statutes = config["statutes"]
                all_candidate_statutes.update(statutes)
                decomposed_issues.append({
                    "issue_type": issue_type,
                    "statute_candidates": statutes,
                    "matched_concepts": list(set(matched_keywords))[:5],
                    "weight": len(matched_keywords) * 1.5
                })

        # Fallback if no specific keywords matched
        if not decomposed_issues:
            decomposed_issues.append({
                "issue_type": "SUBSTANTIVE_OFFENCE",
                "statute_candidates": ["BNS"],
                "matched_concepts": ["general_legal_inquiry"],
                "weight": 1.0
            })
            all_candidate_statutes.add("BNS")

        # Classify complexity
        is_multi_statute = len(all_candidate_statutes) > 1
        if is_multi_statute:
            decomposed_issues.insert(0, {
                "issue_type": "MULTI_STATUTE",
                "statute_candidates": list(all_candidate_statutes),
                "matched_concepts": ["cross_statutory_integration"],
                "weight": 2.0
            })

        return {
            "query": query,
            "is_multi_statute": is_multi_statute,
            "statute_candidates": list(all_candidate_statutes),
            "issue_count": len(decomposed_issues),
            "issues": decomposed_issues
        }
