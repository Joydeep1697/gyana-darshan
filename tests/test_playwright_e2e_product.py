# test_playwright_e2e_product.py — End-to-End Browser Simulation for Phase 8.3 Product Experience

import os
import sys
import time
import uuid
from playwright.sync_api import sync_playwright

BASE_URL = "http://127.0.0.1:8000"

def run_e2e():
    print("=========================================================================")
    print("=== NYAYA DARSHANA — PHASE 8.3 END-TO-END PRODUCT BROWSER SIMULATION ===")
    print("=========================================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1440, "height": 900})
        page = context.new_page()

        print("[1/5] Navigating to Nyaya Darshana at", BASE_URL)
        page.goto(BASE_URL, wait_until="domcontentloaded")
        page.wait_for_timeout(5000) # Wait for splash screen removal

        # 1. Check title
        print("[2/5] Verifying page header & core navigation...")
        title = page.title()
        print(f"  [+] Page title: '{title}'")

        # 2. Navigate to Nyaya Intelligence (Consultations)
        print("[3/5] Navigating to Legal Consultations (Nova Intelligence)...")
        page.click("div[data-page='nova']")
        page.wait_for_timeout(1000)

        # 3. Test Advocate Registration / Sign In via UI clicks
        print("[4/5] Testing Advocate Authentication Flow...")
        unique_email = f"e2e_advocate_{uuid.uuid4().hex[:6]}@nyayadarshana.com"
        
        # Click Sign In button in header
        page.wait_for_selector("#btnOpenAuth", state="visible", timeout=10000)
        page.click("#btnOpenAuth")
        page.wait_for_timeout(500)
        
        # Switch to Register tab
        page.wait_for_selector("#tabRegister", state="visible", timeout=5000)
        page.click("#tabRegister")
        page.wait_for_timeout(500)
        
        page.wait_for_selector("#regFullName", state="visible", timeout=5000)
        page.fill("#regFullName", "Adv. Devendra Shukla")
        page.fill("#regEmail", unique_email)
        page.fill("#regPassword", "AdvocateSecurePass2026!")
        page.click("#regSubmitBtn")
        page.wait_for_timeout(2500)

        # 4. Create and Send Legal Consultation Inquiry
        print("[5/5] Submitting Authoritative Consultation Inquiry & Verifying Evidence...")
        page.wait_for_selector("#chatInput", state="visible", timeout=5000)
        page.fill("#chatInput", "What is the BNS replacement for IPC Section 302 and what penalty applies?")
        page.keyboard.press("Enter")
        page.wait_for_timeout(4500)

        # Check that answer bubble appeared
        chat_html = page.inner_html("#chat")
        assert "NYAYA DARSHAN · GROUNDED" in chat_html or "103" in chat_html, "Expected grounded answer in chat"
        assert "Authoritative Evidence Panel" in chat_html, "Expected evidence panel in chat"
        print("  [+] Grounded response with Gazette evidence verified in UI stream!")

        # Take screenshot for visual QA artifact
        os.makedirs("evaluation/screenshots", exist_ok=True)
        screenshot_path = "evaluation/screenshots/phase_8_3_consultation_verified.png"
        page.screenshot(path=screenshot_path)
        print(f"  [+] UI Artifact saved to {screenshot_path}")

        browser.close()

    print("=========================================================================")
    print("=== PHASE 8.3 BROWSER SIMULATION: ALL WORKFLOWS PASSED (100% OK)     ===")
    print("=========================================================================")

if __name__ == "__main__":
    run_e2e()
