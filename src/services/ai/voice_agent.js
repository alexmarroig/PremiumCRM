import { chatCompletion, textToSpeech } from '../../ai/openai.js';
import { supabaseAdmin } from '../../utils/supabase.js';

export const triggerVoiceAgentCall = async (leadId, userId) => {
  // Fetch lead and latest conversation
  const { data: lead } = await supabaseAdmin.from('contacts').select('*').eq('id', leadId).single();
  const { data: conversation } = await supabaseAdmin
    .from('conversations')
    .select('messages, context_summary, personality_analysis')
    .eq('contact_id', leadId)
    .order('last_message_at', { ascending: false })
    .limit(1)
    .single();

  const history = conversation?.messages?.map(m => m.content).join('\n') || 'Sem histórico.';
  const summary = conversation?.context_summary || 'Sem resumo.';

  const systemPrompt = `
    Você é um agente de voz especializado em vendas e agendamento.
    Seu objetivo: Ligar para o Lead e tentar agendar uma reunião ou fechar uma venda.
    Contexto do Lead: ${lead?.name || 'Cliente'}
    Histórico de Chat: ${history}
    Resumo da Negociação: ${summary}
    Instruções: Seja cordial, direto e use um tom profissional.
  `;

  // Simulate starting the call and getting the first sentence
  const firstSentence = await chatCompletion({
    messages: [
      { role: 'system', content: systemPrompt },
      { role: 'user', content: 'Inicie a ligação saudando o cliente.' }
    ]
  });

  // Convert to audio (simulating voice output)
  const audioBase64 = await textToSpeech(firstSentence);

  return {
    call_id: `call_${Date.now()}`,
    status: 'calling',
    first_sentence: firstSentence,
    audio_payload: audioBase64,
    provider: 'openai-voice-simulation'
  };
};
