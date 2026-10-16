import html
from http.server import BaseHTTPRequestHandler, HTTPServer

from awg import store

HOST, PORT = "127.0.0.1", 8000

COLORS = {
    "executed": "#1a7f37",
    "denied": "#cf222e",
    "needs_approval": "#9a6700",
    "rejected": "#6e7781",
}


def esc(value) -> str:
    # данные приходят от агента, поэтому всё экранируем
    return html.escape("" if value is None else str(value))


def render() -> str:
    p = store.load_policy()
    spent = store.spent_today()
    pending = store.list_pending()
    audit = store.list_audit(50)

    pending_rows = "".join(
        f"<tr><td>#{a['id']}</td><td>{esc(a['amount'])}</td><td>{esc(a['email'])}</td>"
        f"<td>{esc(a['description'])}</td><td>{esc(a['reason'])}</td></tr>"
        for a in pending
    ) or '<tr><td colspan="5" class="muted">No pending approvals</td></tr>'

    audit_rows = "".join(
        f"<tr><td>{esc(r['ts'][:19].replace('T', ' '))}</td>"
        f"<td><span class='tag' style='background:{COLORS.get(r['verdict'], '#6e7781')}'>"
        f"{esc(r['verdict'])}</span></td>"
        f"<td>{esc(r['amount'])}</td><td>{esc(r['email'])}</td><td>{esc(r['reason'])}</td></tr>"
        for r in audit
    ) or '<tr><td colspan="5" class="muted">No decisions yet</td></tr>'

    recipients = esc(", ".join(p.allowed_recipients)) or "any"

    return f"""<!doctype html>
<html><head><meta charset="utf-8"><meta http-equiv="refresh" content="5">
<title>Agent Wallet Guard</title>
<style>
body{{font-family:system-ui,sans-serif;margin:2rem auto;max-width:960px;padding:0 1rem;color:#1f2328}}
h1{{margin-bottom:.2rem}} h2{{margin-top:2rem}}
.cards{{display:flex;gap:1rem;flex-wrap:wrap}}
.card{{border:1px solid #d0d7de;border-radius:8px;padding:.8rem 1rem;min-width:150px}}
.card b{{display:block;font-size:1.4rem}}
table{{border-collapse:collapse;width:100%}}
th,td{{text-align:left;padding:.45rem .6rem;border-bottom:1px solid #eaeef2;font-size:.92rem}}
.tag{{color:#fff;border-radius:999px;padding:.1rem .6rem;font-size:.8rem}}
.muted{{color:#6e7781}}
</style></head><body>
<h1>Agent Wallet Guard</h1>
<div class="muted">PayPal sandbox &middot; refreshes every 5 seconds</div>

<h2>Active policy</h2>
<div class="cards">
  <div class="card">Per transaction<b>{esc(p.max_per_tx)}</b></div>
  <div class="card">Approval above<b>{esc(p.approval_threshold)}</b></div>
  <div class="card">Daily budget<b>{esc(p.daily_budget)}</b></div>
  <div class="card">Spent today<b>{esc(spent)}</b></div>
  <div class="card">Recipients<b style="font-size:1rem">{recipients}</b></div>
</div>

<h2>Pending approvals ({len(pending)})</h2>
<table><tr><th>ID</th><th>Amount</th><th>Recipient</th><th>Description</th><th>Why</th></tr>
{pending_rows}</table>
<p class="muted">Approve from the terminal: <code>python approve.py approve &lt;id&gt;</code></p>

<h2>Decision log</h2>
<table><tr><th>Time (UTC)</th><th>Verdict</th><th>Amount</th><th>Recipient</th><th>Reason</th></tr>
{audit_rows}</table>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path not in ("/", "/index.html"):
            self.send_error(404)
            return
        body = render().encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass  # тише в терминале


if __name__ == "__main__":
    store.init()
    print(f"Dashboard: http://{HOST}:{PORT}  (Ctrl+C to stop)")
    HTTPServer((HOST, PORT), Handler).serve_forever()