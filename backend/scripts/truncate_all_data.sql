-- Truncate all application data in public schema.
-- Keeps PostGIS reference table and Alembic version.
DO $$
DECLARE
  stmt text;
BEGIN
  SELECT 'TRUNCATE ' || string_agg(format('%I.%I', schemaname, tablename), ', ') || ' CASCADE'
  INTO stmt
  FROM pg_tables
  WHERE schemaname = 'public'
    AND tablename NOT IN ('spatial_ref_sys', 'alembic_version');
  IF stmt IS NOT NULL THEN
    EXECUTE stmt;
  END IF;
END $$;
