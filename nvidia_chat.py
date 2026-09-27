#!/usr/bin/env python3
"""
Tek dosyalık NVIDIA AI Sohbet Uygulaması.

Nasıl çalıştırılır:
    python3 nvidia_chat.py

Sonra tarayıcıda şu adresi aç: http://localhost:8765

Neden çalışıyor (önceki HTML-only sürüm neden çalışmıyordu):
Bu betik hem arayüzü sunucudan sunar hem de NVIDIA API'sine isteği
Python (sunucu tarafı) üzerinden gönderir. Tarayıcı sadece
http://localhost:8765 ile konuşur (aynı köken / same-origin),
bu yüzden CORS veya "Origin: null" engeli diye bir şey kalmaz.
API anahtarı tarayıcıya hiç inmez, sadece bu dosyada durur.
"""

import http.server
import urllib.request
import urllib.error
import json

# ⚠️ Anahtarın burada duruyor. Bu dosyayı başkalarıyla paylaşma.
API_KEY = "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"
NVIDIA_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
PORT = 8765

HTML_PAGE = r"""<!DOCTYPE html>
<html lang="tr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Yapay Zeka Sohbet</title>
<style>
  :root {
    --bg: #0f1115; --panel: #171a21; --border: #2a2f3a;
    --text: #e8eaed; --muted: #9aa0aa; --accent: #76b900;
    --accent-dark: #5c9200; --bubble-user: #2563eb; --bubble-ai: #1f2430;
  }
  * { box-sizing: border-box; }
  body {
    margin: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif;
    background: var(--bg); color: var(--text); height: 100vh; display: flex; flex-direction: column;
  }
  header {
    padding: 14px 18px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between; gap: 10px; flex-wrap: wrap;
  }
  header h1 { font-size: 16px; margin: 0; font-weight: 600; display: flex; align-items: center; }
  header .controls { display: flex; gap: 8px; align-items: center; }
  select, button {
    background: var(--panel); color: var(--text); border: 1px solid var(--border);
    border-radius: 8px; padding: 6px 10px; font-size: 13px; cursor: pointer;
  }
  select:hover, button:hover { border-color: var(--accent); }
  #chat { flex: 1; overflow-y: auto; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
  .msg {
    max-width: 100%; padding: 10px 14px; border-radius: 14px; line-height: 1.45;
    white-space: pre-wrap; word-wrap: break-word; font-size: 14.5px;
  }
  .msg.user { background: var(--bubble-user); border-bottom-right-radius: 4px; }
  .msg.ai { background: var(--bubble-ai); border: 1px solid var(--border); border-bottom-left-radius: 4px; }
  .msg.system { align-self: center; color: var(--muted); font-size: 12.5px; background: none; }
  .msg-wrap { display: flex; flex-direction: row; gap: 8px; max-width: 85%; }
  .msg-wrap.user { align-self: flex-end; flex-direction: row-reverse; }
  .msg-wrap.ai { align-self: flex-start; }
  .avatar {
    flex-shrink: 0; width: 30px; height: 30px; border-radius: 50%; display: flex;
    align-items: center; justify-content: center; font-size: 15px;
    background: var(--panel); border: 1px solid var(--border);
  }
  .msg-body { display: flex; flex-direction: column; min-width: 0; }
  .msg-meta {
    display: flex; gap: 8px; align-items: center; font-size: 11px;
    color: var(--muted); margin-top: 3px; padding: 0 4px;
  }
  .msg-meta button { background: none; border: none; padding: 0; color: var(--muted); font-size: 11px; cursor: pointer; }
  .msg-meta button:hover { color: var(--accent); }
  code { background: rgba(255,255,255,0.08); padding: 1px 5px; border-radius: 4px; font-size: 13px; }
  pre { background: #0a0c10; border: 1px solid var(--border); border-radius: 8px; padding: 10px; overflow-x: auto; margin: 6px 0; }
  pre code { background: none; padding: 0; }
  .typing { align-self: flex-start; color: var(--muted); font-size: 13px; padding: 4px 14px; }
  form#inputArea { display: flex; gap: 8px; padding: 12px; border-top: 1px solid var(--border); background: var(--panel); }
  textarea {
    flex: 1; resize: none; background: var(--bg); color: var(--text); border: 1px solid var(--border);
    border-radius: 10px; padding: 10px 12px; font-size: 14.5px; font-family: inherit; min-height: 44px; max-height: 140px;
  }
  textarea:focus { outline: none; border-color: var(--accent); }
  button.send { background: var(--accent); color: #0f1115; font-weight: 700; border: none; padding: 0 18px; }
  button.send:hover { background: var(--accent-dark); }
  button.send:disabled { opacity: .5; cursor: not-allowed; }
  #errorBox {
    display: none; margin: 8px 16px; padding: 10px 12px; background: #3a1620;
    border: 1px solid #6b2130; color: #ffb3bd; border-radius: 8px; font-size: 13px;
    align-items: center; justify-content: space-between; gap: 10px;
  }
  #errorBox button.retry {
    background: #6b2130; color: #ffdfe3; border: 1px solid #ffb3bd;
    border-radius: 6px; padding: 4px 10px; font-size: 12px; white-space: nowrap;
  }
  .spinner {
    display: inline-block; width: 12px; height: 12px; border: 2px solid var(--border);
    border-top-color: var(--accent); border-radius: 50%; animation: spin .7s linear infinite;
    margin-right: 6px; vertical-align: middle;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
</style>
</head>
<body>
<header>
  <h1>🟢 Yapay Zeka Sohbet <span id="statusDot" style="display:inline-block;width:9px;height:9px;border-radius:50%;background:#4ade80;margin-left:6px;"></span></h1>
  <div class="controls">
    <select id="modelSelect">
      <option value="meta/llama-3.1-8b-instruct">Llama 3.1 8B (hızlı, önerilen)</option>
      <option value="meta/llama-3.1-70b-instruct">Llama 3.1 70B</option>
      <option value="mistralai/mixtral-8x7b-instruct-v0.1">Mixtral 8x7B</option>
      <option value="deepseek-ai/deepseek-r1">DeepSeek R1</option>
      <option value="nvidia/nemotron-4-340b-instruct">Nemotron 4 340B</option>
    </select>
    <button id="clearBtn" title="Sohbeti temizle">🗑️ Temizle</button>
    <button id="downloadBtn" title="Sohbeti dosya olarak indir">💾 İndir</button>
  </div>
</header>
<div id="errorBox"></div>
<div id="chat"></div>
<form id="inputArea">
  <textarea id="userInput" placeholder="Mesajını yaz... (Enter: gönder, Shift+Enter: yeni satır)" rows="1"></textarea>
  <button class="send" type="submit" id="sendBtn">Gönder</button>
</form>
<script>
  window.onerror = function(msg, src, line) {
    const box = document.getElementById("errorBox");
    if (box) { box.textContent = "Sayfa hatası (satır " + line + "): " + msg; box.style.display = "flex"; }
  };

  const chatEl = document.getElementById("chat");
  const form = document.getElementById("inputArea");
  const input = document.getElementById("userInput");
  const sendBtn = document.getElementById("sendBtn");
  const modelSelect = document.getElementById("modelSelect");
  const clearBtn = document.getElementById("clearBtn");
  const downloadBtn = document.getElementById("downloadBtn");
  const errorBox = document.getElementById("errorBox");
  const statusDot = document.getElementById("statusDot");

  let history = [];
  try { history = JSON.parse(localStorage.getItem("chatHistory") || "[]"); } catch (e) {}
  function saveHistory() { try { localStorage.setItem("chatHistory", JSON.stringify(history)); } catch (e) {} }

  function setStatus(state) {
    statusDot.style.background = state === "ok" ? "#4ade80" : state === "busy" ? "#facc15" : "#ef4444";
  }

  function formatText(content) {
    let esc = content.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
    esc = esc.replace(/```([\s\S]*?)```/g, (m, code) => "<pre><code>" + code.trim() + "</code></pre>");
    esc = esc.replace(/`([^`]+)`/g, "<code>$1</code>");
    esc = esc.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
    esc = esc.replace(/\n/g, "<br>");
    return esc;
  }

  function addBubble(role, content) {
    if (role === "system") {
      const div = document.createElement("div");
      div.className = "msg system";
      div.textContent = content;
      chatEl.appendChild(div);
      chatEl.scrollTop = chatEl.scrollHeight;
      return;
    }
    const wrap = document.createElement("div");
    wrap.className = "msg-wrap " + (role === "user" ? "user" : "ai");
    const avatar = document.createElement("div");
    avatar.className = "avatar";
    avatar.textContent = role === "user" ? "🧑" : "🤖";
    const body = document.createElement("div");
    body.className = "msg-body";
    const div = document.createElement("div");
    div.className = "msg " + role;
    div.innerHTML = formatText(content);
    body.appendChild(div);
    const meta = document.createElement("div");
    meta.className = "msg-meta";
    const time = document.createElement("span");
    time.textContent = new Date().toLocaleTimeString("tr-TR", { hour: "2-digit", minute: "2-digit" });
    const copyBtn = document.createElement("button");
    copyBtn.textContent = "📋 Kopyala";
    copyBtn.onclick = () => {
      navigator.clipboard.writeText(content).then(() => {
        copyBtn.textContent = "✅ Kopyalandı";
        setTimeout(() => (copyBtn.textContent = "📋 Kopyala"), 1500);
      });
    };
    meta.appendChild(time);
    meta.appendChild(copyBtn);
    body.appendChild(meta);
    wrap.appendChild(avatar);
    wrap.appendChild(body);
    chatEl.appendChild(wrap);
    chatEl.scrollTop = chatEl.scrollHeight;
  }

  function showError(msg, onRetry) {
    errorBox.innerHTML = "";
    const span = document.createElement("span");
    span.textContent = msg;
    errorBox.appendChild(span);
    if (onRetry) {
      const btn = document.createElement("button");
      btn.className = "retry";
      btn.textContent = "🔁 Tekrar dene";
      btn.onclick = () => { hideError(); onRetry(); };
      errorBox.appendChild(btn);
    }
    errorBox.style.display = "flex";
  }
  function hideError() { errorBox.style.display = "none"; }

  try {
    const savedModel = localStorage.getItem("chatModel");
    if (savedModel) modelSelect.value = savedModel;
  } catch (e) {}
  modelSelect.addEventListener("change", () => {
    try { localStorage.setItem("chatModel", modelSelect.value); } catch (e) {}
  });

  if (history.length > 0) {
    history.forEach(m => addBubble(m.role === "user" ? "user" : "ai", m.content));
  } else {
    addBubble("system", "Sohbete hoş geldin. Bir model seç ve yazmaya başla.");
  }

  input.addEventListener("input", () => {
    input.style.height = "auto";
    input.style.height = Math.min(input.scrollHeight, 140) + "px";
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); form.requestSubmit(); }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const text = input.value.trim();
    if (!text) return;
    hideError();
    addBubble("user", text);
    history.push({ role: "user", content: text });
    saveHistory();
    input.value = "";
    input.style.height = "auto";
    await sendToAPI();
  });

  async function sendToAPI() {
    sendBtn.disabled = true;
    sendBtn.textContent = "Gönderiliyor...";
    setStatus("busy");
    const typingEl = document.createElement("div");
    typingEl.className = "typing";
    typingEl.innerHTML = '<span class="spinner"></span>Yazıyor...';
    chatEl.appendChild(typingEl);
    chatEl.scrollTop = chatEl.scrollHeight;

    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 45000);

    try {
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ model: modelSelect.value, messages: history }),
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      typingEl.remove();

      const data = await response.json();

      if (!response.ok) {
        if (response.status === 429) {
          throw Object.assign(new Error("RATE_LIMIT"), { isRateLimit: true });
        }
        throw new Error((data && data.error) ? data.error : ("Sunucu hatası: " + response.status));
      }

      const reply = data?.choices?.[0]?.message?.content ?? "(Boş yanıt geldi)";
      addBubble("ai", reply);
      history.push({ role: "assistant", content: reply });
      saveHistory();
      setStatus("ok");
    } catch (err) {
      clearTimeout(timeoutId);
      typingEl.remove();
      setStatus("error");
      if (err.isRateLimit) {
        showError("⏳ Hız limitine takıldın (NVIDIA ücretsiz kademe ~40 istek/dakika). Biraz bekleyip tekrar dene.", sendToAPI);
      } else if (err.name === "AbortError") {
        showError("İstek 45 saniyede yanıt vermedi.", sendToAPI);
      } else {
        showError("Hata: " + err.message, sendToAPI);
      }
      console.error(err);
    } finally {
      sendBtn.disabled = false;
      sendBtn.textContent = "Gönder";
      input.focus();
    }
  }

  clearBtn.addEventListener("click", () => {
    if (!confirm("Sohbet geçmişi silinsin mi?")) return;
    history = [];
    saveHistory();
    chatEl.innerHTML = "";
    addBubble("system", "Sohbet temizlendi.");
  });

  downloadBtn.addEventListener("click", () => {
    if (history.length === 0) { showError("İndirilecek bir sohbet yok."); return; }
    let text = "=== Sohbet Kaydı ===\n\n";
    history.forEach(m => { text += (m.role === "user" ? "Sen: " : "Yapay Zeka: ") + m.content + "\n\n"; });
    const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const ts = new Date().toISOString().slice(0,19).replace(/[:T]/g,"-");
    a.download = "sohbet-" + ts + ".txt";
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  });
</script>
</body>
</html>
"""


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            body = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path != "/api/chat":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        try:
            incoming = json.loads(self.rfile.read(length) or b"{}")
        except Exception:
            self._send_json(400, {"error": "Geçersiz istek gövdesi"})
            return

        payload = json.dumps({
            "model": incoming.get("model", "meta/llama-3.1-8b-instruct"),
            "messages": incoming.get("messages", []),
            "temperature": 0.7,
            "top_p": 0.9,
            "max_tokens": 1024,
            "stream": False,
        }).encode("utf-8")

        req = urllib.request.Request(
            NVIDIA_URL,
            data=payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer " + API_KEY,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                self._send_raw(resp.status, resp.read())
        except urllib.error.HTTPError as e:
            self._send_raw(e.code, e.read())
        except Exception as e:
            self._send_json(502, {"error": "Sunucuya bağlanılamadı: " + str(e)})

    def _send_json(self, status, obj):
        self._send_raw(status, json.dumps(obj).encode("utf-8"))

    def _send_raw(self, status, data_bytes):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data_bytes)))
        self.end_headers()
        self.wfile.write(data_bytes)

    def log_message(self, fmt, *args):
        print("[sunucu]", fmt % args)


if __name__ == "__main__":
    print("=" * 50)
    print(f"✅ Sohbet hazır: http://localhost:{PORT}")
    print("Bu pencereyi kapatma. Durdurmak için Ctrl+C.")
    print("=" * 50)
    http.server.HTTPServer(("localhost", PORT), Handler).serve_forever()
