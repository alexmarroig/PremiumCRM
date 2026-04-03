export const SUMMARY_PROMPT =
  'Resuma esta conversa em 2 frases. Sugira 3 próximas ações concretas (criar tarefa, enviar proposta X, marcar call). Contexto empresa: [TOM PME BRASILEIRO AMIGÁVEL]';

export const RESPONSE_PROMPT =
  'Gere resposta profissional, tom {{empresa_tom}}, contexto histórico: {{history}}. Lead score: {{score}}';

export const COMPRESSION_PROMPT =
  'Você é um assistente técnico. Sua tarefa é criar um resumo altamente compacto de uma conversa entre um Lead e um Atendente. ' +
  'Foque em: 1. Intenção do Lead, 2. Status da negociação, 3. Última pergunta/ponto pendente. ' +
  'O resumo será usado como memória para economizar tokens. Seja direto, use no máximo 100 palavras.';

export const PERSONALITY_PROMPT =
  'Analise o histórico desta conversa e extraia os traços de personalidade e estilo de comunicação de AMBAS as partes (Lead e Atendente). ' +
  'Retorne um JSON com o seguinte formato: ' +
  '{ "lead": { "tone": "formal/informal", "traits": ["direto", "curioso", etc], "style": "texto curto/longo" }, ' +
  '  "user": { "tone": "...", "traits": [...], "style": "..." } }. ' +
  'Não inclua explicações, apenas o JSON.';

export const SIMULATION_PROMPT =
  'Baseado na análise de personalidade {{personality}} e no histórico {{history}}, SIMULE as próximas 3 interações possíveis. ' +
  'Simule o que o Lead provavelmente perguntará e o que o Atendente responderia seguindo seu padrão. ' +
  'Retorne um JSON: { "simulation": [ { "from": "lead", "text": "..." }, { "from": "user", "text": "..." } ] }';
