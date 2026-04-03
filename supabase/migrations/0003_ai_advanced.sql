-- Adicionar campos de IA avançada na tabela de conversas
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS context_summary TEXT;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS personality_analysis JSONB;
ALTER TABLE public.conversations ADD COLUMN IF NOT EXISTS simulation_enabled BOOLEAN DEFAULT false NOT NULL;

-- Comentários para documentação
COMMENT ON COLUMN public.conversations.context_summary IS 'Resumo técnico da conversa para economia de tokens';
COMMENT ON COLUMN public.conversations.personality_analysis IS 'Análise de personalidade do Lead e do Usuário';
COMMENT ON COLUMN public.conversations.simulation_enabled IS 'Se a simulação de resposta em tempo real está ativa para esta conversa';
