from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    page.goto('http://127.0.0.1:8000')
    page.wait_for_timeout(4500)
    print('Calling openAuthModal(login)...')
    page.evaluate('openAuthModal("login")')
    modal_style = page.evaluate('window.getComputedStyle(document.getElementById("authModal")).display')
    tab_style = page.evaluate('window.getComputedStyle(document.getElementById("tabRegister")).display')
    tab_offset = page.evaluate('document.getElementById("tabRegister").offsetParent !== null')
    print(f'authModal display: {modal_style}')
    print(f'tabRegister display: {tab_style}, offsetParent: {tab_offset}')
    
    print('Switching to register...')
    page.evaluate('switchAuthTab("register")')
    reg_style = page.evaluate('window.getComputedStyle(document.getElementById("regFullName")).display')
    reg_offset = page.evaluate('document.getElementById("regFullName").offsetParent !== null')
    print(f'regFullName display: {reg_style}, offsetParent: {reg_offset}')
    b.close()
