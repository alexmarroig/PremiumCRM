import fetch from 'node-fetch';
import { config } from '../../utils/config.js';
import { supabaseAdmin } from '../../utils/supabase.js';

export const triggerVoiceAgentCall = async (leadId, userId) => {
  // Busca o lead e o histórico de conversas
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
    Você é um agente de voz especializado em vendas e agendamento para a empresa Clarity CRM.
    Seu objetivo: Ligar para o Lead e tentar agendar uma reunião ou fechar uma venda.
    Contexto do Lead: ${lead?.name || 'Cliente'} (Telefone: ${lead?.handle || 'Desconhecido'})
    Histórico de Chat: ${history}
    Resumo da Negociação: ${summary}
    Instruções: Seja cordial, direto e use um tom profissional e amigável. Fale em Português do Brasil.
  `;

  if (!config.vapiApiKey) {
    return {
      error: 'VAPI_API_KEY não configurada no .env',
      status: 'simulation',
      message: 'A IA está pronta para ligar, mas você precisa adicionar VAPI_API_KEY no seu arquivo .env.'
    };
  }

  try {
    const response = await fetch('https://api.vapi.ai/call', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${config.vapiApiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        phoneNumberId: config.vapiPhoneNumberId,
        customer: {
          number: lead?.handle.startsWith('+') ? lead.handle : `+55${lead.handle.replace(/\D/g, '')}`,
          name: lead?.name
        },
        assistant: {
          name: 'Clarity AI Sales',
          firstMessage: `Olá ${lead?.name || 'tudo bem'}? Aqui é a inteligência artificial da Clarity. Vi que estávamos conversando por chat e resolvi te ligar para agilizarmos.`,
          model: {
            provider: 'openai',
            model: 'gpt-4o',
            messages: [
              { role: 'system', content: systemPrompt }
            ]
          },
          voice: {
             provider: '11labs',
             voiceId: 'lucas' // Ou qualquer voz em PT-BR
          }
        }
      })
    });

    const data = await response.json();
    if (!response.ok) throw new Error(JSON.stringify(data));

    return {
      call_id: data.id,
      status: data.status,
      provider: 'vapi',
      data
    };
  } catch (error) {
    return {
      error: error.message,
      status: 'failed'
    };
  }
};
