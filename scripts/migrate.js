import fs from 'fs';
import path from 'path';
import pg from 'pg';
import dotenv from 'dotenv';

dotenv.config();

const { Client } = pg;
const databaseUrl = process.env.SUPABASE_DB_URL;
if (!databaseUrl) {
  throw new Error('SUPABASE_DB_URL is required to run migrations');
}

const migrationsPath = path.resolve('supabase/migrations/enterprise/001_init.sql');
const sql = fs.readFileSync(migrationsPath, 'utf-8');

const client = new Client({ connectionString: databaseUrl });
await client.connect();
try {
  await client.query(sql);
  console.log('Migrations applied');
} finally {
  await client.end();
}
