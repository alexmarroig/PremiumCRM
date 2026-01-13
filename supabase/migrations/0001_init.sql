create extension if not exists "pgcrypto";

create table if not exists public.organizations (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  owner_user_id uuid references auth.users(id),
  created_at timestamptz default now()
);

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  full_name text,
  avatar_url text,
  company_name text,
  settings jsonb default '{}'::jsonb,
  current_org_id uuid references public.organizations(id),
  created_at timestamptz default now()
);

create table if not exists public.memberships (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references public.organizations(id) on delete cascade,
  user_id uuid references auth.users(id) on delete cascade,
  role text default 'admin' check (role in ('admin', 'member', 'viewer')),
  created_at timestamptz default now(),
  unique (org_id, user_id)
);

create table if not exists public.contacts (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references public.organizations(id) on delete cascade,
  name text not null,
  email text,
  phone text,
  avatar_url text,
  tags text[] default '{}'::text[],
  lead_score int default 0,
  preferences jsonb default '{}'::jsonb,
  purchase_history jsonb default '[]'::jsonb,
  notes text,
  created_at timestamptz default now()
);

create table if not exists public.contact_identities (
  id uuid primary key default gen_random_uuid(),
  org_id uuid not null references public.organizations(id) on delete cascade,
  contact_id uuid not null references public.contacts(id) on delete cascade,
  channel text not null check (channel in ('whatsapp', 'instagram', 'messenger', 'email')),
  external_id text not null,
  created_at timestamptz default now(),
  unique (org_id, channel, external_id)
);

create table if not exists public.conversations (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references public.organizations(id) on delete cascade,
  contact_id uuid references public.contacts(id),
  channel text not null,
  channel_conversation_id text,
  sentiment text default 'neutral',
  urgency text default 'medium',
  summary text,
  is_unanswered boolean default true,
  unread_count int default 0,
  negotiation_enabled boolean default false,
  base_price numeric,
  last_message_at timestamptz,
  created_at timestamptz default now()
);

create unique index if not exists conversations_channel_conversation_unique
  on public.conversations (org_id, channel, channel_conversation_id)
  where channel_conversation_id is not null;

create table if not exists public.messages (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references public.organizations(id) on delete cascade,
  conversation_id uuid references public.conversations(id) on delete cascade,
  content text not null,
  is_from_customer boolean default true,
  sentiment text,
  channel_message_id text,
  metadata jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create unique index if not exists messages_channel_message_unique
  on public.messages (org_id, channel_message_id)
  where channel_message_id is not null;

create table if not exists public.tasks (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references public.organizations(id) on delete cascade,
  conversation_id uuid references public.conversations(id),
  contact_id uuid references public.contacts(id),
  title text not null,
  description text,
  due_date timestamptz,
  priority text default 'medium' check (priority in ('low', 'medium', 'high')),
  completed boolean default false,
  created_at timestamptz default now()
);

create unique index if not exists tasks_followup_unique
  on public.tasks (org_id, conversation_id, title, due_date)
  where title = 'Follow up';

create table if not exists public.pipelines (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references public.organizations(id) on delete cascade,
  name text not null,
  created_at timestamptz default now()
);

create table if not exists public.pipeline_stages (
  id uuid primary key default gen_random_uuid(),
  pipeline_id uuid references public.pipelines(id) on delete cascade,
  name text not null,
  position int not null,
  created_at timestamptz default now()
);

create table if not exists public.deals (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references public.organizations(id) on delete cascade,
  contact_id uuid references public.contacts(id),
  pipeline_id uuid references public.pipelines(id),
  stage_id uuid references public.pipeline_stages(id),
  title text not null,
  value numeric,
  probability int,
  status text default 'open' check (status in ('open', 'won', 'lost')),
  close_date date,
  created_at timestamptz default now()
);

create table if not exists public.automation_rules (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references public.organizations(id) on delete cascade,
  name text not null,
  description text,
  is_active boolean default true,
  created_at timestamptz default now()
);

create table if not exists public.quick_replies (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references public.organizations(id) on delete cascade,
  title text not null,
  content text not null,
  created_at timestamptz default now()
);

create table if not exists public.calendar_events (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references public.organizations(id) on delete cascade,
  title text not null,
  description text,
  starts_at timestamptz,
  ends_at timestamptz,
  created_at timestamptz default now()
);

create table if not exists public.channel_connections (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references public.organizations(id) on delete cascade,
  channel text not null,
  status text default 'active',
  settings jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists public.analytics_events (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references public.organizations(id) on delete cascade,
  event_name text not null,
  payload jsonb default '{}'::jsonb,
  created_at timestamptz default now()
);

create table if not exists public.alfred_suggestions (
  id uuid primary key default gen_random_uuid(),
  org_id uuid references public.organizations(id) on delete cascade,
  conversation_id uuid references public.conversations(id) on delete cascade,
  type text not null,
  content text not null,
  created_at timestamptz default now()
);

create index if not exists contacts_org_id_idx on public.contacts (org_id);
create index if not exists conversations_org_id_idx on public.conversations (org_id);
create index if not exists messages_org_id_idx on public.messages (org_id);
create index if not exists tasks_org_id_idx on public.tasks (org_id);
create index if not exists memberships_user_id_idx on public.memberships (user_id);
create index if not exists contact_identities_contact_id_idx on public.contact_identities (contact_id);

create or replace function public.handle_new_user()
returns trigger
language plpgsql
security definer
set search_path = public
as $$
declare
  new_org_id uuid;
  default_pipeline_id uuid;
begin
  insert into public.profiles (id, full_name, avatar_url, company_name)
  values (
    new.id,
    new.raw_user_meta_data->>'full_name',
    new.raw_user_meta_data->>'avatar_url',
    new.raw_user_meta_data->>'company_name'
  )
  on conflict (id) do nothing;

  insert into public.organizations (name, owner_user_id)
  values (
    coalesce(nullif(split_part(new.email, '@', 1), ''), 'My Workspace'),
    new.id
  )
  returning id into new_org_id;

  insert into public.memberships (org_id, user_id, role)
  values (new_org_id, new.id, 'admin')
  on conflict (org_id, user_id) do nothing;

  update public.profiles
  set current_org_id = new_org_id
  where id = new.id;

  insert into public.pipelines (org_id, name)
  values (new_org_id, 'Default Pipeline')
  returning id into default_pipeline_id;

  insert into public.pipeline_stages (pipeline_id, name, position)
  values
    (default_pipeline_id, 'Lead', 1),
    (default_pipeline_id, 'Qualified', 2),
    (default_pipeline_id, 'Proposal', 3),
    (default_pipeline_id, 'Won', 4);

  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;
create trigger on_auth_user_created
after insert on auth.users
for each row execute function public.handle_new_user();
