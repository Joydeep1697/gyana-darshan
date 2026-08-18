"""
Generate catalog for 214 categorized PDFs without uploading full content
Run: python catalog_category.py /path/to/extracted/Category/folder
This creates a small CSV (few KB) you can upload to Meta AI
"""
import os, csv
from pathlib import Path
import hashlib

def catalog_pdfs(root_folder):
    root = Path(root_folder)
    output = root.parent / f"{root.name}_catalog.csv"
    
    with open(output, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(["file_path", "category", "filename", "size_kb", "act_tag", "section_hint", "needs_validation"])
        
        for pdf_file in root.rglob("*.pdf"):
            rel_path = pdf_file.relative_to(root)
            category = str(rel_path.parent) if len(rel_path.parts) > 1 else "root"
            size_kb = round(pdf_file.stat().st_size / 1024, 1)
            
            # Auto-tag based on filename/folder
            name_lower = pdf_file.name.lower()
            act_tag = ""
            if "bns" in name_lower or "nyaya sanhita" in name_lower:
                act_tag = "BNS"
            elif "bnss" in name_lower or "nagarik suraksha" in name_lower or "crpc" in name_lower:
                act_tag = "BNSS"
            elif "bsa" in name_lower or "sakshya" in name_lower or "evidence" in name_lower:
                act_tag = "BSA"
            elif "ipc" in name_lower:
                act_tag = "IPC->BNS"
            elif "constitution" in name_lower:
                act_tag = "Constitution"
            
            # Section hint
            section_hint = ""
            # Look for numbers like 302, 103 etc in filename
            import re
            nums = re.findall(r'\b\d{1,3}[A-Z]?\b', pdf_file.stem)
            if nums:
                section_hint = ",".join(nums[:5])
            
            w.writerow([str(rel_path), category, pdf_file.name, size_kb, act_tag, section_hint, "PENDING"])
    
    print(f"Catalog created: {output}")
    print(f"Size: {output.stat().st_size / 1024:.1f} KB - safe to upload!")
    print("\nUpload this CSV to Meta AI, I can then:")
    print("1. Build Master Corpus mapping without needing 100MB+ PDFs")
    print("2. Tell you which files are Category A (statutory), B (case law), C, D (reject)")
    print("3. Create RAG chunk plan")

if __name__ == "__main__":
    import sys
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    catalog_pdfs(folder)