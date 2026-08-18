# build_pocso_corpus.py — Parse Official POCSO Act 2012 Gazette into Corpus JSONL

import fitz
import re
import json
from pathlib import Path

PDF_PATH = Path(r"d:\Nova Legal\Indian Legal\raw\AA2012-32.pdf")
OUT_JSONL = Path(r"d:\Nova Legal\corpus_integrity\pocso_2012_corpus.jsonl")

def extract_pocso_sections():
    doc = fitz.open(str(PDF_PATH))
    
    # Extract text from page 3 onward (where main body starts after arrangement of sections)
    body_text = "\n".join(doc[i].get_text("text") for i in range(2, len(doc)))
    
    # Split by section headers e.g. "\n1. ", "\n2. ", ... "\n46. "
    # Regex to find section starts
    pattern = r'\n(?=(\d+[A-Z]?)\.\s+([A-Z][^\n]+))'
    splits = re.split(pattern, body_text)
    
    # We can iterate through sections 1 to 46
    sections = []
    
    # Explicit section search using regex
    sec_matches = list(re.finditer(r'\n\s*(\d+[A-Z]?)\.\s+([^\n—\-]+(?:—|[.\-]))', body_text))
    
    for i, m in enumerate(sec_matches):
        sec_num = m.group(1)
        heading = m.group(2).strip(" .—-")
        start_idx = m.start()
        end_idx = sec_matches[i+1].start() if i+1 < len(sec_matches) else len(body_text)
        sec_content = body_text[start_idx:end_idx].strip()
        
        # Determine chapter based on section number
        s_int = int(re.sub(r'\D', '', sec_num)) if re.sub(r'\D', '', sec_num) else 1
        if s_int <= 2:
            chapter = "Chapter I: Preliminary"
        elif s_int <= 12:
            chapter = "Chapter II: Sexual Offences Against Children"
        elif s_int <= 15:
            chapter = "Chapter III: Using Child for Pornographic Purposes"
        elif s_int <= 18:
            chapter = "Chapter IV: Abetment of and Attempt to Commit an Offence"
        elif s_int <= 23:
            chapter = "Chapter V: Procedure for Reporting of Cases"
        elif s_int <= 27:
            chapter = "Chapter VI: Procedures for Recording Statement of the Child"
        elif s_int <= 32:
            chapter = "Chapter VII: Special Courts"
        elif s_int <= 42:
            chapter = "Chapter VIII: Procedure and Powers of Special Courts and Recording of Evidence"
        else:
            chapter = "Chapter IX: Miscellaneous"
            
        entry = {
            "id": f"POCSO_SEC_{sec_num}",
            "statute": "Protection of Children from Sexual Offences Act, 2012 (POCSO)",
            "short_name": "POCSO",
            "act_number": "Act 32 of 2012",
            "predecessor": "None (Special Child Protection Statute)",
            "chapter": chapter,
            "section": sec_num,
            "heading": heading,
            "text": sec_content[:3000],
            "source": "Official Gazette of India (Act 32 of 2012)",
            "status": "active"
        }
        sections.append(entry)
        
    print(f"[+] Extracted {len(sections)} POCSO sections.")
    
    # Save to JSONL
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for s in sections:
            f.write(json.dumps(s) + "\n")
            
    print(f"[+] Saved POCSO corpus to: {OUT_JSONL.name}")

if __name__ == "__main__":
    extract_pocso_sections()
