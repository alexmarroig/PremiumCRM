create or replace function public.is_org_member(org_uuid uuid)
returns boolean
language sql
stable
as $$
  select exists (
    select 1
    from public.memberships
    where org_id = org_uuid
      and user_id = auth.uid()
  );
$$;

create or replace function public.is_org_admin(org_uuid uuid)
returns boolean
language sql
stable
as $$
  select exists (
    select 1
    from public.memberships
    where org_id = org_uuid
      and user_id = auth.uid()
      and role = 'admin'
  );
$$;

alter table public.organizations enable row level security;
alter table public.profiles enable row level security;
alter table public.memberships enable row level security;
alter table public.contacts enable row level security;
alter table public.contact_identities enable row level security;
alter table public.conversations enable row level security;
alter table public.messages enable row level security;
alter table public.tasks enable row level security;
alter table public.pipelines enable row level security;
alter table public.pipeline_stages enable row level security;
alter table public.deals enable row level security;
alter table public.automation_rules enable row level security;
alter table public.quick_replies enable row level security;
alter table public.calendar_events enable row level security;
alter table public.channel_connections enable row level security;
alter table public.analytics_events enable row level security;
alter table public.alfred_suggestions enable row level security;

create policy "Profiles select own" on public.profiles
  for select using (id = auth.uid());
create policy "Profiles insert own" on public.profiles
  for insert with check (id = auth.uid());
create policy "Profiles update own" on public.profiles
  for update using (id = auth.uid()) with check (id = auth.uid());

create policy "Organizations select member" on public.organizations
  for select using (public.is_org_member(id));
create policy "Organizations insert owner" on public.organizations
  for insert with check (owner_user_id = auth.uid());
create policy "Organizations update admin" on public.organizations
  for update using (public.is_org_admin(id)) with check (public.is_org_admin(id));

create policy "Memberships select member" on public.memberships
  for select using (public.is_org_member(org_id));
create policy "Memberships insert admin" on public.memberships
  for insert with check (public.is_org_admin(org_id));
create policy "Memberships update admin" on public.memberships
  for update using (public.is_org_admin(org_id)) with check (public.is_org_admin(org_id));
create policy "Memberships delete admin" on public.memberships
  for delete using (public.is_org_admin(org_id));

create policy "Contacts select member" on public.contacts
  for select using (public.is_org_member(org_id));
create policy "Contacts insert member" on public.contacts
  for insert with check (public.is_org_member(org_id));
create policy "Contacts update member" on public.contacts
  for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy "Contacts delete member" on public.contacts
  for delete using (public.is_org_member(org_id));

create policy "Contact identities select member" on public.contact_identities
  for select using (public.is_org_member(org_id));
create policy "Contact identities insert member" on public.contact_identities
  for insert with check (public.is_org_member(org_id));
create policy "Contact identities update member" on public.contact_identities
  for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy "Contact identities delete member" on public.contact_identities
  for delete using (public.is_org_member(org_id));

create policy "Conversations select member" on public.conversations
  for select using (public.is_org_member(org_id));
create policy "Conversations insert member" on public.conversations
  for insert with check (public.is_org_member(org_id));
create policy "Conversations update member" on public.conversations
  for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy "Conversations delete member" on public.conversations
  for delete using (public.is_org_member(org_id));

create policy "Messages select member" on public.messages
  for select using (public.is_org_member(org_id));
create policy "Messages insert member" on public.messages
  for insert with check (public.is_org_member(org_id));
create policy "Messages update member" on public.messages
  for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy "Messages delete member" on public.messages
  for delete using (public.is_org_member(org_id));

create policy "Tasks select member" on public.tasks
  for select using (public.is_org_member(org_id));
create policy "Tasks insert member" on public.tasks
  for insert with check (public.is_org_member(org_id));
create policy "Tasks update member" on public.tasks
  for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy "Tasks delete member" on public.tasks
  for delete using (public.is_org_member(org_id));

create policy "Pipelines select member" on public.pipelines
  for select using (public.is_org_member(org_id));
create policy "Pipelines insert member" on public.pipelines
  for insert with check (public.is_org_member(org_id));
create policy "Pipelines update member" on public.pipelines
  for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy "Pipelines delete member" on public.pipelines
  for delete using (public.is_org_member(org_id));

create policy "Pipeline stages select member" on public.pipeline_stages
  for select using (exists (
    select 1
    from public.pipelines
    where pipelines.id = pipeline_stages.pipeline_id
      and public.is_org_member(pipelines.org_id)
  ));
create policy "Pipeline stages insert member" on public.pipeline_stages
  for insert with check (exists (
    select 1
    from public.pipelines
    where pipelines.id = pipeline_stages.pipeline_id
      and public.is_org_member(pipelines.org_id)
  ));
create policy "Pipeline stages update member" on public.pipeline_stages
  for update using (exists (
    select 1
    from public.pipelines
    where pipelines.id = pipeline_stages.pipeline_id
      and public.is_org_member(pipelines.org_id)
  )) with check (exists (
    select 1
    from public.pipelines
    where pipelines.id = pipeline_stages.pipeline_id
      and public.is_org_member(pipelines.org_id)
  ));
create policy "Pipeline stages delete member" on public.pipeline_stages
  for delete using (exists (
    select 1
    from public.pipelines
    where pipelines.id = pipeline_stages.pipeline_id
      and public.is_org_member(pipelines.org_id)
  ));

create policy "Deals select member" on public.deals
  for select using (public.is_org_member(org_id));
create policy "Deals insert member" on public.deals
  for insert with check (public.is_org_member(org_id));
create policy "Deals update member" on public.deals
  for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy "Deals delete member" on public.deals
  for delete using (public.is_org_member(org_id));

create policy "Automation rules select member" on public.automation_rules
  for select using (public.is_org_member(org_id));
create policy "Automation rules insert member" on public.automation_rules
  for insert with check (public.is_org_member(org_id));
create policy "Automation rules update member" on public.automation_rules
  for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy "Automation rules delete member" on public.automation_rules
  for delete using (public.is_org_member(org_id));

create policy "Quick replies select member" on public.quick_replies
  for select using (public.is_org_member(org_id));
create policy "Quick replies insert member" on public.quick_replies
  for insert with check (public.is_org_member(org_id));
create policy "Quick replies update member" on public.quick_replies
  for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy "Quick replies delete member" on public.quick_replies
  for delete using (public.is_org_member(org_id));

create policy "Calendar events select member" on public.calendar_events
  for select using (public.is_org_member(org_id));
create policy "Calendar events insert member" on public.calendar_events
  for insert with check (public.is_org_member(org_id));
create policy "Calendar events update member" on public.calendar_events
  for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy "Calendar events delete member" on public.calendar_events
  for delete using (public.is_org_member(org_id));

create policy "Channel connections select member" on public.channel_connections
  for select using (public.is_org_member(org_id));
create policy "Channel connections insert member" on public.channel_connections
  for insert with check (public.is_org_member(org_id));
create policy "Channel connections update member" on public.channel_connections
  for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy "Channel connections delete member" on public.channel_connections
  for delete using (public.is_org_member(org_id));

create policy "Analytics events select member" on public.analytics_events
  for select using (public.is_org_member(org_id));
create policy "Analytics events insert member" on public.analytics_events
  for insert with check (public.is_org_member(org_id));
create policy "Analytics events update member" on public.analytics_events
  for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy "Analytics events delete member" on public.analytics_events
  for delete using (public.is_org_member(org_id));

create policy "Alfred suggestions select member" on public.alfred_suggestions
  for select using (public.is_org_member(org_id));
create policy "Alfred suggestions insert member" on public.alfred_suggestions
  for insert with check (public.is_org_member(org_id));
create policy "Alfred suggestions update member" on public.alfred_suggestions
  for update using (public.is_org_member(org_id)) with check (public.is_org_member(org_id));
create policy "Alfred suggestions delete member" on public.alfred_suggestions
  for delete using (public.is_org_member(org_id));
