# ui/dashboard.py — assemble the SUKOT dashboard SPA
import json
from ui.theme import page_head, APP
from ui import dash_html, dash_css, dash_js

def render() -> str:
    titles = json.dumps(dash_html.TITLES, ensure_ascii=False)
    protos = json.dumps({
        "vless-ws": "VLESS + WebSocket (زنده)",
        "vless-tcp": "VLESS + TCP خام",
        "xhttp-packet-up": "XHTTP packet-up (زنده)",
        "xhttp-stream-up": "XHTTP stream-up (زنده)",
        "vmess-ws": "VMess + WebSocket (فقط لینک)",
        "trojan-ws": "Trojan + WebSocket (فقط لینک)",
        "manual": "لینک دستی (همه پروتکل‌ها)",
    }, ensure_ascii=False)
    js = dash_js.js().replace("__TITLES__", titles).replace("__PROTOS__", protos)
    css = dash_css.css()
    head = page_head(f"{APP} Control Center", extra_css=css)
    return head + f"""
<body>
{dash_html.body()}
<script src="/assets/qr.js"></script>
<script>{js}</script>
</body>
</html>"""
