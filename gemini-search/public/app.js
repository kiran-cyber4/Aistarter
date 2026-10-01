const chatEl = document.getElementById('chat');
const formEl = document.getElementById('search-form');
const inputEl = document.getElementById('search-input');

const history = [];

function addMessage(role, text) {
  const el = document.createElement('div');
  el.className = `message ${role}`;
  el.textContent = text;
  chatEl.appendChild(el);
  chatEl.scrollTop = chatEl.scrollHeight;
  return el;
}

function addToolCalls(toolCalls) {
  for (const call of toolCalls) {
    addMessage('tool', `🔧 ${call.name}(${JSON.stringify(call.args)}) → ${JSON.stringify(call.output)}`);
  }
}

formEl.addEventListener('submit', async (event) => {
  event.preventDefault();
  const message = inputEl.value.trim();
  if (!message) return;

  addMessage('user', message);
  inputEl.value = '';
  inputEl.disabled = true;
  formEl.querySelector('button').disabled = true;

  const pending = addMessage('assistant', '…thinking');

  try {
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message, history }),
    });
    const data = await res.json();

    if (!res.ok) {
      pending.remove();
      addMessage('error', data.error || 'Something went wrong.');
      return;
    }

    pending.remove();
    if (data.toolCalls && data.toolCalls.length) {
      addToolCalls(data.toolCalls);
    }
    addMessage('assistant', data.reply);

    history.push({ role: 'user', text: message });
    history.push({ role: 'assistant', text: data.reply });
  } catch (err) {
    pending.remove();
    addMessage('error', 'Network error — is the server running?');
  } finally {
    inputEl.disabled = false;
    formEl.querySelector('button').disabled = false;
    inputEl.focus();
  }
});
