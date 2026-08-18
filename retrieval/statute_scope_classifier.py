# statute_scope_classifier.py — Nyaya Legal OS Phase 6.15 Statute Scope Classifier
#
# Objective:
# Classify query intent into its governing statutory jurisdiction:
# 1. Substantive Criminal Offences & Penalties -> Bharatiya Nyaya Sanhita, 2023 (BNS)
# 2. Criminal Procedure, Investigation, Remand, Bail, Trials -> Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)
# 3. Law of Evidence & Electronic Records -> Bharatiya Sakshya Adhiniyam, 2023 (BSA)
# 4. Special Statutes -> POCSO Act, 2012 (Unrepealed independent statute)

from typing import Dict, List, Any, Optional

class StatuteScopeClassifier:
    def __init__(self):
        pass

    def classify_statute_scope(self, query: str) -> Optional[Dict[str, Any]]:
        q_lower = query.lower()

        # 1. Substantive Criminal Code
        if any(term in q_lower for term in ["substantive criminal code", "substantive criminal law", "governs offences committed in india", "offences committed on or after july 1"]):
            return {
                "statute_code": "BNS",
                "statute_title": "Bharatiya Nyaya Sanhita, 2023 (BNS)",
                "act_number": "Act 45 of 2023",
                "role": "Substantive Criminal Code",
                "replaced": "Indian Penal Code, 1860 (IPC)",
                "effective_date": "July 1, 2024",
                "standard_statement": "The Bharatiya Nyaya Sanhita, 2023 (BNS, Act 45 of 2023) is the substantive criminal code governing offences committed on or after July 1, 2024, replacing the Indian Penal Code, 1860."
            }

        # 2. Procedural Statute
        if any(term in q_lower for term in ["primary procedural statute", "criminal investigations and trials", "procedural law", "procedure for criminal", "governs criminal procedure"]):
            return {
                "statute_code": "BNSS",
                "statute_title": "Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)",
                "act_number": "Act 46 of 2023",
                "role": "Procedural Criminal Code",
                "replaced": "Code of Criminal Procedure, 1973 (CrPC)",
                "effective_date": "July 1, 2024",
                "standard_statement": "The Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS, Act 46 of 2023) governs criminal procedure, investigations, and trials, replacing the Code of Criminal Procedure, 1973."
            }

        # 3. Evidence & Electronic Records
        if any(term in q_lower for term in ["admissibility and proof of electronic records", "law of evidence", "admissibility of evidence", "governs electronic records", "electronic records in judicial proceedings"]):
            return {
                "statute_code": "BSA",
                "statute_title": "Bharatiya Sakshya Adhiniyam, 2023 (BSA)",
                "act_number": "Act 47 of 2023",
                "role": "Law of Evidence",
                "replaced": "Indian Evidence Act, 1872 (IEA)",
                "effective_date": "July 1, 2024",
                "standard_statement": "The Bharatiya Sakshya Adhiniyam, 2023 (BSA, Act 47 of 2023) governs the admissibility of evidence, including electronic records under Section 63, replacing the Indian Evidence Act, 1872."
            }

        # 4. Special Statute — POCSO
        if any(term in q_lower for term in ["pocso", "protection of children from sexual offences"]):
            return {
                "statute_code": "POCSO",
                "statute_title": "Protection of Children from Sexual Offences Act, 2012 (POCSO)",
                "act_number": "Act 32 of 2012",
                "role": "Special Independent Statute",
                "relationship": "Unrepealed Independent Law",
                "standard_statement": "The Protection of Children from Sexual Offences Act, 2012 (POCSO) remains an active, unrepealed, independent special statute and has NOT been repealed or subsumed by BNS 2023."
            }

        return None
