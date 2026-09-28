// ==========================================================================
// JAGY — Live Hermes AI Copilot Real-Time Chat Widget
// Directly connects to the real Hermes AI model via FastAPI backend
// ==========================================================================

class HermesChatWidget {
  constructor() {
    this.modal = document.getElementById('agent-modal');
    this.messagesContainer = document.getElementById('agent-messages');
    this.input = document.getElementById('agent-input');
    this.sendBtn = document.getElementById('agent-send');
    this.fab = document.getElementById('agent-fab');
    this.closeBtn = document.getElementById('close-agent');

    // Conversation memory history
    this.history = [];
    this.isGenerating = false;

    // Determine API endpoint (supports local dev, custom domain, and file:// protocol)
    this.apiBase = window.location.origin.includes('http') && !window.location.origin.includes('file')
      ? window.location.origin
      : 'http://localhost:8000';

    this.init();
  }

  init() {
    if (!this.modal || !this.fab) return;

    this.fab.addEventListener('click', () => this.toggleModal(true));
    this.closeBtn.addEventListener('click', () => this.toggleModal(false));

    this.sendBtn.addEventListener('click', () => this.handleSend());
    this.input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        this.handleSend();
      }
    });

    // Quick prompt pills
    document.querySelectorAll('.prompt-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        const text = btn.textContent.replace(/[⚡🎯⏰🌐⚙️]/g, '').trim();
        this.input.value = `Tell me about ${text.toLowerCase()} and how to configure it.`;
        this.handleSend();
      });
    });
  }

  toggleModal(open) {
    if (open) {
      this.modal.classList.add('open');
      this.input.focus();
    } else {
      this.modal.classList.remove('open');
    }
  }

  async handleSend() {
    const text = this.input.value.trim();
    if (!text || this.isGenerating) return;

    // 1. Render User Message
    this.appendMessage(text, 'user');
    this.input.value = '';
    this.isGenerating = true;

    // 2. Render Typing Indicator
    const typingBubble = this.createTypingIndicator();
    this.messagesContainer.appendChild(typingBubble);
    this.scrollToBottom();

    try {
      // 3. Call Live Hermes API Endpoint
      const response = await fetch(`${this.apiBase}/api/agent/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          message: text,
          history: this.history
        })
      });

      typingBubble.remove();

      if (!response.ok) {
        throw new Error(`Server returned status ${response.status}`);
      }

      const data = await response.json();
      const reply = data.reply || "I didn't receive a response. Please check your backend connection.";

      // 4. Update Conversation History
      this.history.push({ role: 'user', content: text });
      this.history.push({ role: 'model', content: reply });

      // 5. Render Hermes Response
      this.appendMessage(reply, 'bot');
    } catch (err) {
      console.warn("Live API connection notice:", err);
      typingBubble.remove();
      this.appendMessage(
        `🤖 **Hermes Assistant Note**:\n\nConnecting to the local JAGY backend at \`${this.apiBase}\`...\n\nIf the server is launching or running, make sure to double-click \`Start-JAGY.bat\` or run \`python -m uvicorn web.app:app --port 8000\` on your computer!`,
        'bot'
      );
    } finally {
      this.isGenerating = false;
      this.scrollToBottom();
    }
  }

  createTypingIndicator() {
    const bubble = document.createElement('div');
    bubble.className = 'chat-bubble bubble-bot typing-indicator-bubble';
    bubble.style.display = 'flex';
    bubble.style.alignItems = 'center';
    bubble.style.gap = '6px';
    bubble.style.padding = '12px 18px';
    bubble.innerHTML = `
      <span style="font-size: 12px; color: #a5b4fc; font-weight: 600;">Hermes is thinking</span>
      <span class="typing-dot" style="width:5px; height:5px; background:#a5b4fc; border-radius:50%; animation: pulse 1s infinite alternate;"></span>
      <span class="typing-dot" style="width:5px; height:5px; background:#a5b4fc; border-radius:50%; animation: pulse 1s infinite alternate; animation-delay: 0.2s;"></span>
      <span class="typing-dot" style="width:5px; height:5px; background:#a5b4fc; border-radius:50%; animation: pulse 1s infinite alternate; animation-delay: 0.4s;"></span>
    `;
    return bubble;
  }

  appendMessage(rawText, sender) {
    const bubble = document.createElement('div');
    bubble.className = `chat-bubble bubble-${sender}`;
    bubble.innerHTML = this.formatMarkdown(rawText);
    this.messagesContainer.appendChild(bubble);
    this.scrollToBottom();
  }

  formatMarkdown(text) {
    if (!text) return '';
    let html = text
      // Code blocks
      .replace(/```([\s\S]*?)```/g, '<pre style="background: rgba(0,0,0,0.4); border: 1px solid rgba(255,255,255,0.1); border-radius: 8px; padding: 10px; margin: 8px 0; overflow-x: auto; font-family: monospace; font-size: 12px;"><code>$1</code></pre>')
      // Inline code
      .replace(/`([^`]+)`/g, '<code style="background: rgba(255,255,255,0.1); padding: 2px 6px; border-radius: 4px; font-family: monospace; font-size: 12px;">$1</code>')
      // Headers
      .replace(/^### (.*$)/gim, '<h5 style="color:#fff; margin: 10px 0 4px; font-weight: 700;">$1</h5>')
      .replace(/^## (.*$)/gim, '<h4 style="color:#fff; margin: 12px 0 6px; font-weight: 800;">$1</h4>')
      // Bold & Italic
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      // Lists
      .replace(/^\s*[-•]\s+(.*$)/gim, '<li style="margin-left: 18px; margin-bottom: 3px;">$1</li>')
      // Line breaks
      .replace(/\n\n/g, '<br><br>')
      .replace(/\n/g, '<br>');

    return html;
  }

  scrollToBottom() {
    this.messagesContainer.scrollTop = this.messagesContainer.scrollHeight;
  }
}

document.addEventListener('DOMContentLoaded', () => {
  window.hermesChat = new HermesChatWidget();
});
