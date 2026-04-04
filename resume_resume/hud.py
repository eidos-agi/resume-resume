"""Floating progress HUD for resume-resume.

A native macOS NSPanel with WKWebView that shows streaming search results.
Stays alive across multiple MCP tool calls via Unix socket multiplexing.

Security note: This is a LOCAL-ONLY UI. The WKWebView renders data from our
own MCP server process via WKWebView.evaluateJavaScript_ (the standard PyObjC
API — there is no alternative for injecting data into a webview). All text
content is set via DOM textContent, never innerHTML, to prevent injection.

Usage:
    # Standalone test (pipe JSON-lines to stdin):
    python -m resume_resume.hud < events.jsonl

    # Socket mode (long-lived, multiplexed):
    python -m resume_resume.hud --listen /tmp/resume-hud.sock
"""

import json
import os
import select
import socket
import sys
import threading
import time
from pathlib import Path

import AppKit  # noqa: PyObjC
import Foundation
import WebKit
import objc

SOCKET_PATH = "/tmp/resume-hud.sock"
HUD_WIDTH = 620
HUD_HEIGHT = 520
DISMISS_DELAY = 0  # 0 = never auto-dismiss; user closes manually

_HTML = r"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,"SF Pro Text",sans-serif;
font-size:15px;color:#e8e8e8;background:#141416;padding:20px 24px;
-webkit-user-select:none;overflow-y:auto;height:100vh;
-webkit-font-smoothing:antialiased}
.ch{margin-bottom:20px}
.ch-hdr{font-size:13px;font-weight:600;text-transform:uppercase;
letter-spacing:.8px;color:#a0a0a5;padding-bottom:8px;
border-bottom:1px solid rgba(255,255,255,.12);margin-bottom:12px}
.ln{display:flex;align-items:flex-start;gap:12px;padding:6px 0;
opacity:0;transform:translateY(8px);animation:si .25s ease-out forwards}
@keyframes si{to{opacity:1;transform:translateY(0)}}
.ic{flex-shrink:0;width:20px;text-align:center;font-size:15px;line-height:22px}
.ic.search{color:#64d2ff}.ic.done{color:#30d158}
.ic.working{color:#ffd60a}.ic.info{color:#98989d}.ic.error{color:#ff453a}
.tx{flex:1;line-height:22px;word-break:break-word}
.tx.hl{color:#fff;font-weight:600;font-size:16px}
.rc{background:rgba(255,255,255,.07);border-radius:8px;padding:12px 14px;
margin:6px 0;opacity:0;transform:translateY(8px);animation:si .3s ease-out forwards;
cursor:default;transition:background .15s;border:1px solid rgba(255,255,255,.06)}
.rc:hover{background:rgba(255,255,255,.12)}
.rt{font-weight:600;color:#fff;margin-bottom:4px;font-size:15px}
.rm{font-size:13px;color:#a0a0a5;line-height:18px}
::-webkit-scrollbar{width:5px}
::-webkit-scrollbar-track{background:transparent}
::-webkit-scrollbar-thumb{background:rgba(255,255,255,.2);border-radius:3px}
</style></head><body><div id="root"></div>
<script>
const C={},IC={search:"\u{1F50D}",done:"\u2713",working:"\u25E6",
info:"\u2022",error:"\u2717",result:"\u25B8"};
function gch(n){if(C[n])return C[n];const d=document.createElement("div");
d.className="ch";const h=document.createElement("div");h.className="ch-hdr";
h.textContent=n;d.appendChild(h);document.getElementById("root").prepend(d);
C[n]=d;return d}
function aln(ch,t,ic,hl){const c=gch(ch),l=document.createElement("div");
l.className="ln";const i=document.createElement("span");
i.className="ic "+(ic||"info");i.textContent=IC[ic]||IC.info;
l.appendChild(i);const x=document.createElement("span");
x.className="tx"+(hl?" hl":"");x.textContent=t;l.appendChild(x);
c.appendChild(l);l.scrollIntoView({behavior:"smooth",block:"end"})}
function arc(ch,ti,me,sid){const c=gch(ch),d=document.createElement("div");
d.className="rc";d.dataset.sid=sid||"";const t=document.createElement("div");
t.className="rt";t.textContent=ti;d.appendChild(t);
const m=document.createElement("div");m.className="rm";m.textContent=me;
d.appendChild(m);c.appendChild(d);d.scrollIntoView({behavior:"smooth",block:"end"})}
function clr(n){const c=C[n];if(c)while(c.children.length>1)c.removeChild(c.lastChild)}
function ev(j){const e=JSON.parse(j);if(e.clear){clr(e.channel||"default");return}
if(e.result){arc(e.channel||"default",e.result.title,e.result.meta,e.result.session_id);return}
aln(e.channel||"default",e.text||"",e.icon||"info",e.highlight||false)}
</script></body></html>"""


class _Delegate(AppKit.NSObject):
    def windowWillClose_(self, note):
        # User closed the window — exit cleanly
        os._exit(0)


class _NavDelegate(AppKit.NSObject):
    """Detects when WKWebView finishes loading HTML."""
    hud = None  # set by ProgressHUD

    def webView_didFinishNavigation_(self, webView, navigation):
        if self.hud:
            self.hud._on_page_ready()


class ProgressHUD:
    """Native macOS floating HUD with WKWebView."""

    def __init__(self):
        self._app = AppKit.NSApplication.sharedApplication()
        self._app.setActivationPolicy_(AppKit.NSApplicationActivationPolicyRegular)
        self._app.activateIgnoringOtherApps_(True)
        self._ready = False
        self._queue = []  # events buffered until page loads

        style = (AppKit.NSWindowStyleMaskTitled | AppKit.NSWindowStyleMaskClosable
                 | AppKit.NSWindowStyleMaskUtilityWindow)

        screen = AppKit.NSScreen.mainScreen().frame()
        frame = Foundation.NSMakeRect(screen.size.width - HUD_WIDTH - 20, 60,
                                      HUD_WIDTH, HUD_HEIGHT)

        self._panel = AppKit.NSPanel.alloc() \
            .initWithContentRect_styleMask_backing_defer_(
                frame, style, AppKit.NSBackingStoreBuffered, False)
        self._panel.setTitle_("resume-resume")
        self._panel.setFloatingPanel_(True)
        self._panel.setBecomesKeyOnlyIfNeeded_(True)
        self._panel.setHidesOnDeactivate_(False)
        self._panel.setLevel_(AppKit.NSFloatingWindowLevel)
        self._panel.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorStationary
            | AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary)
        self._panel.setAlphaValue_(1.0)
        self._panel.setOpaque_(True)
        self._panel.setBackgroundColor_(
            AppKit.NSColor.colorWithCalibratedRed_green_blue_alpha_(0.08, 0.08, 0.10, 1.0))
        self._panel.setDelegate_(_Delegate.alloc().init())

        cfg = WebKit.WKWebViewConfiguration.alloc().init()
        self._wv = WebKit.WKWebView.alloc().initWithFrame_configuration_(
            Foundation.NSMakeRect(0, 0, HUD_WIDTH, HUD_HEIGHT - 22), cfg)
        self._wv.setAutoresizingMask_(
            AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable)
        self._wv.setValue_forKey_(False, "drawsBackground")

        # Navigation delegate to detect page load
        self._nav_delegate = _NavDelegate.alloc().init()
        self._nav_delegate.hud = self
        self._wv.setNavigationDelegate_(self._nav_delegate)

        self._panel.contentView().addSubview_(self._wv)
        self._wv.loadHTMLString_baseURL_(_HTML, None)
        self._panel.orderFrontRegardless()
        self._last_activity = time.time()

    def _on_page_ready(self):
        """Called when WKWebView finishes loading. Flush queued events."""
        self._ready = True
        for evt in self._queue:
            self._inject(evt)
        self._queue.clear()

    def send(self, event: dict):
        """Send event to webview. Queues if page isn't ready yet."""
        self._last_activity = time.time()
        # Bring window to front on every new event
        self._panel.orderFrontRegardless()
        self._app.activateIgnoringOtherApps_(True)
        if not self._ready:
            self._queue.append(event)
            return
        self._inject(event)

    def _inject(self, event: dict):
        """Inject event into webview via JS."""
        payload = json.dumps(json.dumps(event))
        js = f"ev({payload})"
        if threading.current_thread() is threading.main_thread():
            self._wv.evaluateJavaScript_completionHandler_(js, None)  # noqa: eval-ok
        else:
            _js_ref = js
            def _run():
                self._wv.evaluateJavaScript_completionHandler_(_js_ref, None)  # noqa: eval-ok
            Foundation.NSObject.alloc().init().performSelectorOnMainThread_withObject_waitUntilDone_(
                objc.selector(lambda s, o: _run(), signature=b"v@:@"), None, False
            )


# ── stdin mode ──────────────────────────────────────────────

def _drain(stream, hud):
    for raw in stream:
        line = (raw.strip() if isinstance(raw, str) else raw.decode().strip())
        if not line:
            continue
        try:
            evt = json.loads(line)
        except json.JSONDecodeError:
            continue
        if evt.get("done"):
            continue  # ignore done signals — user closes the window
        hud.send(evt)
    # stdin closed — keep window open, user will close it


def run_stdin():
    hud = ProgressHUD()
    threading.Thread(target=_drain, args=(sys.stdin, hud), daemon=True).start()
    hud._app.run()


# ── socket mode (multiplexer) ──────────────────────────────

def run_socket(path: str = SOCKET_PATH):
    sock_path = Path(path)
    sock_path.unlink(missing_ok=True)

    srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    srv.bind(str(sock_path))
    srv.listen(5)
    srv.setblocking(False)

    hud = ProgressHUD()

    def _loop():
        clients, bufs = [], {}
        while True:
            rd = [srv] + clients
            try:
                ready, _, _ = select.select(rd, [], [], 0.5)
            except (ValueError, OSError):
                # Transient error (e.g. bad fd) — just retry
                clients = [c for c in clients if c.fileno() >= 0]
                bufs = {c: bufs[c] for c in clients if c in bufs}
                continue
            for s in ready:
                if s is srv:
                    c, _ = srv.accept(); c.setblocking(False)
                    clients.append(c); bufs[c] = b""
                else:
                    try:
                        d = s.recv(4096)
                    except (ConnectionResetError, OSError):
                        d = b""
                    if not d:
                        clients.remove(s); del bufs[s]; s.close(); continue
                    bufs[s] += d
                    while b"\n" in bufs[s]:
                        ln, bufs[s] = bufs[s].split(b"\n", 1)
                        ln = ln.strip()
                        if not ln:
                            continue
                        try:
                            hud.send(json.loads(ln))
                        except json.JSONDecodeError:
                            pass
            # Never auto-dismiss — user closes the window manually

    threading.Thread(target=_loop, daemon=True).start()
    Path("/tmp/resume-hud.pid").write_text(str(os.getpid()))
    try:
        hud._app.run()
    finally:
        sock_path.unlink(missing_ok=True)
        Path("/tmp/resume-hud.pid").unlink(missing_ok=True)


def main():
    if "--listen" in sys.argv:
        i = sys.argv.index("--listen")
        run_socket(sys.argv[i + 1] if i + 1 < len(sys.argv) else SOCKET_PATH)
    else:
        run_stdin()


if __name__ == "__main__":
    main()
