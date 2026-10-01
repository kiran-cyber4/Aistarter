require('dotenv').config();

const path = require('path');
const express = require('express');
const { GoogleGenerativeAI } = require('@google/generative-ai');
const { declarations, callTool } = require('./tools');

const PORT = process.env.PORT || 3000;
const API_KEY = process.env.GEMINI_API_KEY;
const MODEL_NAME = process.env.GEMINI_MODEL || 'gemini-1.5-flash';

if (!API_KEY) {
  console.error('Missing GEMINI_API_KEY. Copy .env.example to .env and set your key.');
  process.exit(1);
}

const genAI = new GoogleGenerativeAI(API_KEY);
const model = genAI.getGenerativeModel({
  model: MODEL_NAME,
  tools: [{ functionDeclarations: declarations }],
});

const app = express();
app.use(express.json());
app.use(express.static(path.join(__dirname, 'public')));

// Turns the client's plain chat history into Gemini's `contents` format.
function toContents(history) {
  return (history || []).map((turn) => ({
    role: turn.role === 'assistant' ? 'model' : 'user',
    parts: [{ text: turn.text }],
  }));
}

app.post('/api/chat', async (req, res) => {
  const { message, history } = req.body || {};
  if (typeof message !== 'string' || !message.trim()) {
    return res.status(400).json({ error: 'message is required' });
  }

  try {
    const chat = model.startChat({ history: toContents(history) });
    let result = await chat.sendMessage(message);
    const toolCalls = [];

    // Resolve any function calls Gemini asks for, then feed results back,
    // looping in case the model chains multiple tool calls.
    let functionCalls = result.response.functionCalls();
    while (functionCalls && functionCalls.length > 0) {
      const responses = [];
      for (const call of functionCalls) {
        const output = await callTool(call.name, call.args);
        toolCalls.push({ name: call.name, args: call.args, output });
        responses.push({
          functionResponse: { name: call.name, response: output },
        });
      }
      result = await chat.sendMessage(responses);
      functionCalls = result.response.functionCalls();
    }

    res.json({ reply: result.response.text(), toolCalls });
  } catch (err) {
    console.error('Gemini request failed:', err);
    res.status(502).json({ error: 'Failed to get a response from Gemini.' });
  }
});

app.listen(PORT, () => {
  console.log(`Gemini search chat running at http://localhost:${PORT}`);
});
