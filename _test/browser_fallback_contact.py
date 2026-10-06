#!/usr/bin/env python3
"""The fallback's Yes / No offer on Ask the Docent, and the museum-page fallback, in Chrome.

Not in CI: it needs Playwright and a local Google Chrome.  Run it against a
local server before any change to the fallback or the contact flow:

    CONTENT_ROOT=corpora python3 -m uvicorn api.main:app --port 8765 &
    pip install playwright      # in a scratch venv; drives the system Chrome
    python3 _test/browser_fallback_contact.py http://127.0.0.1:8765

Paths: speech recognition (yes, silence, no), no speech recognition, and the
recordings failing to load; then /cod.  /contact is intercepted in the browser
and never reaches the server, so no email is sent.  The page itself does not
send X-SubDocent-Test, so the local server logs these questions to
ask_log.jsonl at the repo root (gitignored); delete it afterwards.  Never point
this at production.
"""
import sys, json
from playwright.sync_api import sync_playwright

BASE = sys.argv[1].rstrip("/")
Q = "Why was the sail fairwater cut down?"
RECORDING = ("I don't have an answer for that right now, but I can pass it along to our historians "
             "and get back to you by email or text. Would you like me to do that?")
results = []

def check(label, ok, detail=""):
    results.append((label, ok)); print(("  PASS  " if ok else "  FAIL  ") + label + ("" if ok else "  " + str(detail)))

FAKE_SPEECH = """
window.__speechQueue = %s; window.__recStarts = 0;
class FakeRec { start(){ window.__recStarts++; const t = window.__speechQueue.shift();
  setTimeout(() => { if (t == null) { this.onend && this.onend(); }
    else { this.onresult && this.onresult({results: [[{transcript: t}]]}); this.onend && this.onend(); } }, 300); }
  stop(){} abort(){} }
window.SpeechRecognition = FakeRec; window.webkitSpeechRecognition = FakeRec;
"""
NO_SPEECH = "window.SpeechRecognition = undefined; window.webkitSpeechRecognition = undefined;"

def page_for(browser, init, block_audio=False):
    ctx = browser.new_context()
    ctx.add_init_script(init)
    pg = ctx.new_page()
    pg.contacts, pg.audio, pg.errors = [], [], []
    pg.on("pageerror", lambda e: pg.errors.append(str(e)))
    def contact(route):
        pg.contacts.append(route.request.post_data or "")
        route.fulfill(status=200, content_type="application/json", body='{"status":"logged"}')
    pg.route("**/contact", contact)
    def audio(route):
        pg.audio.append(route.request.url.rsplit("/", 1)[-1])
        route.abort() if block_audio else route.continue_()
    pg.route("**/audio/*.mp3", audio)
    pg.goto(BASE + "/web/askthedocent.html"); pg.wait_for_load_state("networkidle")
    return pg

def ask(pg, q=Q):
    pg.evaluate("q => { unlockAudio(); handleQuestion(q); }", q)
    pg.wait_for_function("document.getElementById('answerText').innerText.trim().length > 0", timeout=20000)

def offer_visible(pg): return pg.is_visible("#contactYes") and pg.is_visible("#contactNo")
def idle(pg, ms=40000):  # the mic button leaves its "answering" state when audio and listening are done
    pg.wait_for_function("!document.getElementById('micBtn').classList.contains('answering')", timeout=ms)

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", headless=True, args=["--autoplay-policy=no-user-gesture-required"])

    print("Path 1: speech recognition, visitor says yes, then speaks contact details")
    pg = page_for(b, FAKE_SPEECH % json.dumps(["yes", "sailor at example dot com"]))
    ask(pg)
    check("answer text is the recording word for word", pg.inner_text("#answerText").strip() == RECORDING, pg.inner_text("#answerText"))
    check("Yes / No shown under the answer", offer_visible(pg))
    pg.wait_for_selector("#contactThanks", state="visible", timeout=60000)
    check("nothits.mp3 then emailaddressorphonenumber.mp3 played", pg.audio[:2] == ["nothits.mp3", "emailaddressorphonenumber.mp3"], pg.audio)
    check("spoken contact sent once", len(pg.contacts) == 1 and "sailor at example dot com" in pg.contacts[0], pg.contacts)
    check("question sent with it", Q in (pg.contacts[0] if pg.contacts else ""))
    check("no page errors", not pg.errors, pg.errors); pg.context.close()

    print("Path 1b: speech recognition, visitor stays silent, then clicks No")
    pg = page_for(b, FAKE_SPEECH % json.dumps([None]))
    ask(pg); idle(pg); pg.wait_for_function("window.__recStarts >= 1"); pg.wait_for_timeout(1000)
    check("silence is not taken as no: buttons still there", offer_visible(pg))
    pg.click("#contactNo")
    check("No hides the offer", not pg.is_visible("#contactOffer"))
    check("nothing sent", not pg.contacts, pg.contacts)
    check("no page errors", not pg.errors, pg.errors); pg.context.close()

    print("Path 1c: speech recognition, visitor says no")
    pg = page_for(b, FAKE_SPEECH % json.dumps(["no thanks"]))
    ask(pg); pg.wait_for_function("window.__recStarts >= 1"); pg.wait_for_timeout(1500)
    check("spoken no hides the offer", not pg.is_visible("#contactOffer"))
    check("nothing sent", not pg.contacts, pg.contacts); pg.context.close()

    print("Path 2: no speech recognition")
    pg = page_for(b, NO_SPEECH)
    ask(pg)
    check("answer text is the recording", pg.inner_text("#answerText").strip() == RECORDING)
    idle(pg); pg.wait_for_timeout(1000)
    check("recording played", "nothits.mp3" in pg.audio, pg.audio)
    check("not treated as no: buttons still there after the recording", offer_visible(pg))
    pg.click("#contactYes")
    check("Yes shows the contact field", pg.is_visible("#contactInput") and not pg.is_visible("#contactYes"))
    pg.fill("#contactInput", "555-0100"); pg.click("#contactSend")
    pg.wait_for_selector("#contactThanks", state="visible", timeout=10000)
    check("typed contact sent once", len(pg.contacts) == 1 and "555-0100" in pg.contacts[0], pg.contacts)
    pg.wait_for_timeout(500); idle(pg)
    check("no page errors", not pg.errors, pg.errors); pg.context.close()

    print("Path 3: recordings fail to load (speech available)")
    pg = page_for(b, FAKE_SPEECH % json.dumps(["no"]), block_audio=True)
    ask(pg)
    check("answer text is the recording", pg.inner_text("#answerText").strip() == RECORDING)
    idle(pg, 10000); pg.wait_for_timeout(1500)
    check("buttons still there", offer_visible(pg))
    check("no listening without the prompt", pg.evaluate("window.__recStarts") == 0)
    pg.click("#contactYes"); pg.fill("#contactInput", "sailor@example.com"); pg.keyboard.press("Enter")
    pg.wait_for_selector("#contactThanks", state="visible", timeout=10000)
    check("typed contact sent once (Enter)", len(pg.contacts) == 1 and "sailor%40example.com" in pg.contacts[0] or "sailor@example.com" in (pg.contacts[0] if pg.contacts else ""), pg.contacts)
    check("no page errors", not pg.errors, pg.errors); pg.context.close()

    print("Path 4: a new question clears the offer; an ordinary answer shows none")
    pg = page_for(b, NO_SPEECH)
    ask(pg); idle(pg)
    pg.evaluate("handleQuestion('How many men were in the crew?')")
    pg.wait_for_function("document.getElementById('answerText').innerText.includes('crew') || document.getElementById('answerText').innerText.length > 200", timeout=20000)
    check("no offer under an answered question", not pg.is_visible("#contactOffer"))
    pg.context.close()

    print("Museum page /cod")
    ctx = b.new_context(); pg = ctx.new_page(); audio = []; errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.on("request", lambda r: audio.append(r.url) if r.url.endswith(".mp3") else None)
    pg.goto(BASE + "/cod"); pg.wait_for_selector("#museum-ask-input", timeout=20000)
    pg.fill("#museum-ask-input", Q); pg.click("#museum-ask-btn")
    pg.wait_for_function("(t => t.length > 0 && !t.startsWith('Asking'))(document.getElementById('museum-answer').innerText.trim())", timeout=20000)
    txt = pg.inner_text("#museum-answer").strip()
    check("museum fallback is exactly the short line", txt == "I don't have an answer for that right now.", txt)
    check("no question, no offer, no audio", "?" not in txt and "historians" not in txt and not audio, (txt, audio))
    pg.fill("#museum-ask-input", "What did USS Cod sink during the war?"); pg.click("#museum-ask-btn")
    pg.wait_for_function("(t => t.length > 0 && !t.startsWith('Asking') && !t.startsWith(\"I don't have\"))(document.getElementById('museum-answer').innerText.trim())", timeout=20000)
    check("an answerable question still answers", len(pg.inner_text("#museum-answer")) > 100)
    check("no page errors", not errs, errs)
    b.close()

failed = [l for l, ok in results if not ok]
print(f"\n{len(results) - len(failed)}/{len(results)} passed")
sys.exit(1 if failed else 0)
