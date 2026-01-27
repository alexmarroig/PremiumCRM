import fetch from 'node-fetch';
import { config } from '../utils/config.js';

const OPENAI_BASE = 'https://api.openai.com/v1';

const headers = {
  Authorization: `Bearer ${config.openaiApiKey}`,
};

export const chatCompletion = async ({ messages, model = 'gpt-4o-mini' }) => {
  const response = await fetch(`${OPENAI_BASE}/chat/completions`, {
    method: 'POST',
    headers: {
      ...headers,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ model, messages, temperature: 0.4 }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`OpenAI error: ${error}`);
  }
  const data = await response.json();
  return data.choices?.[0]?.message?.content || '';
};

export const transcribeAudio = async (audioBase64) => {
  const response = await fetch(`${OPENAI_BASE}/audio/transcriptions`, {
    method: 'POST',
    headers,
    body: createAudioForm(audioBase64),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`OpenAI transcription error: ${error}`);
  }
  return response.json();
};

export const textToSpeech = async (text) => {
  const response = await fetch(`${OPENAI_BASE}/audio/speech`, {
    method: 'POST',
    headers: {
      ...headers,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ model: 'gpt-4o-mini-tts', input: text, voice: 'alloy' }),
  });

  if (!response.ok) {
    const error = await response.text();
    throw new Error(`OpenAI TTS error: ${error}`);
  }
  const audioBuffer = await response.arrayBuffer();
  return Buffer.from(audioBuffer).toString('base64');
};

const createAudioForm = (audioBase64) => {
  const form = new FormData();
  const buffer = Buffer.from(audioBase64, 'base64');
  form.append('file', new Blob([buffer]), 'audio.ogg');
  form.append('model', 'whisper-1');
  form.append('language', 'pt');
  return form;
};
