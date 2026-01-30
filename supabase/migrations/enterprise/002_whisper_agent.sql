CREATE TABLE IF NOT EXISTS agent_sessions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id),
  conversation_id UUID REFERENCES conversations(id),
  agent_id TEXT,
  state JSONB DEFAULT '{}'::jsonb,
  last_event TIMESTAMP
);

CREATE TABLE IF NOT EXISTS agent_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  session_id UUID REFERENCES agent_sessions(id),
  tool_called TEXT,
  input JSONB,
  output JSONB,
  success BOOLEAN,
  timestamp TIMESTAMP DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS agent_plugins (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  team_id UUID REFERENCES teams(id),
  name TEXT,
  niche TEXT,
  tools JSONB[],
  prompt_template TEXT,
  active BOOLEAN DEFAULT true
);

CREATE INDEX IF NOT EXISTS idx_agent_sessions_team ON agent_sessions(team_id);
CREATE INDEX IF NOT EXISTS idx_agent_events_session ON agent_events(session_id);
CREATE INDEX IF NOT EXISTS idx_agent_plugins_team_active ON agent_plugins(team_id, active);
