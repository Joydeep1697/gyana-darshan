import sys
from pathlib import Path
BASE_DIR = Path(r"d:\Nova Legal")
sys.path.append(str(BASE_DIR))

from retrieval.hybrid_retriever import AuthoritativeLegalRetriever
from verification.claim_firewall import LegalVerificationFirewall

r = AuthoritativeLegalRetriever()
fw = LegalVerificationFirewall()

for q in ["A user asks 'What replaced 302?' after discussing IPC offences. Which conversion should be considered?",
          "A user asks 'What replaced 167?' after discussing police remand under CrPC. Which conversion should be considered?",
          "A user asks 'What replaced 65B?' while discussing electronic records under the old Evidence Act. Which current provision should be investigated?",
          "The question claims that BNSS is the 'BNS Criminal Procedure Code'. How should the system correct the terminology?",
          "The question states: 'Since BNS is the new criminal code, it replaced CrPC too.' Is the premise correct?",
          "A case involves extortion, police seizure of property, and an electronic threat message. Which legal provisions should be separated?"]:
    ep = r.retrieve_evidence_pack(q)
    raw = f"According to current Indian Statutory Law:\n{r.format_evidence_context(ep)}\nIn response to query, the position is established."
    p, ans, c = fw.verify_and_enforce(raw, ep)
    print(f"\nQuery: {q}")
    print(f"Firewall Passed: {p}")
    print(f"Answer: {ans[:200]}")
