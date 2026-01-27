-- Core
CREATE TABLE IF NOT EXISTS teams (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name TEXT NOT NULL,
  subdomain TEXT UNIQUE,
  plan TEXT DEFAULT 'starter',
  stripe_customer_id TEXT,
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS users (
  id UUID REFERENCES auth.users(id),
  team_id UUID REFERENCES teams(id),
  role TEXT CHECK (role IN ('admin','manager','agent')),
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS conversations (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id),
  lead_id UUID,
  channel TEXT CHECK (channel IN ('whatsapp','instagram','messenger','email')),
  external_id TEXT,
  messages JSONB[],
  score INTEGER DEFAULT 0 CHECK (score >=0 AND score <=100),
  urgency TEXT CHECK (urgency IN ('low','medium','high')),
  tags TEXT[],
  status TEXT CHECK (status IN ('lead','customer','lost')),
  timeline JSONB DEFAULT '[]',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS leads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id),
  name TEXT,
  phone TEXT UNIQUE,
  email TEXT,
  ticket_medio DECIMAL DEFAULT 0,
  ltv DECIMAL DEFAULT 0,
  sentiment_avg DECIMAL DEFAULT 0,
  conversations UUID[],
  custom_fields JSONB DEFAULT '{}',
  updated_at TIMESTAMP DEFAULT NOW()
);

-- Automação
CREATE TABLE IF NOT EXISTS rules (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id),
  name TEXT,
  trigger JSONB,
  action JSONB,
  active BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS flows (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id),
  name TEXT,
  nodes JSONB[],
  active BOOLEAN DEFAULT true,
  executions INTEGER DEFAULT 0
);

-- Tarefas + Colab
CREATE TABLE IF NOT EXISTS tasks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id),
  lead_id UUID REFERENCES leads(id),
  title TEXT,
  description TEXT,
  priority TEXT CHECK (priority IN ('low','medium','high')),
  due_date TIMESTAMP,
  assignee_id UUID REFERENCES users(id),
  status TEXT DEFAULT 'pending' CHECK (status IN ('pending','done','overdue'))
);

CREATE TABLE IF NOT EXISTS internal_comments (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id UUID REFERENCES conversations(id),
  user_id UUID REFERENCES users(id),
  text TEXT,
  mentions TEXT[]
);

-- Analytics + Performance
CREATE TABLE IF NOT EXISTS analytics_daily (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id),
  date DATE,
  total_messages INTEGER,
  response_time_avg DECIMAL,
  conversion_rate DECIMAL,
  sentiment_positivo DECIMAL,
  leads_created INTEGER
);

CREATE TABLE IF NOT EXISTS agent_performance (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id),
  user_id UUID REFERENCES users(id),
  date DATE,
  messages_handled INTEGER,
  avg_response_time DECIMAL,
  satisfaction_score DECIMAL
);

-- Logs + Segurança
CREATE TABLE IF NOT EXISTS audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id),
  user_id UUID REFERENCES users(id),
  action TEXT,
  conversation_id UUID,
  details JSONB,
  ip_address INET,
  created_at TIMESTAMP DEFAULT NOW()
);

-- Indexes performance
CREATE INDEX IF NOT EXISTS idx_conversations_team_channel ON conversations(team_id, channel);
CREATE INDEX IF NOT EXISTS idx_leads_team_phone ON leads(team_id, phone);
