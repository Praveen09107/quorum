-- Real, honest rollback -- fails loud (a real constraint violation),
-- not silently, if any real 'gate_approved' row already exists, the
-- same "never silently truncate/corrupt real data" discipline
-- migration 0005's own down.sql already established for this project.
ALTER TABLE expenses DROP CONSTRAINT expenses_source_check;
ALTER TABLE expenses ADD CONSTRAINT expenses_source_check
    CHECK (source IN ('on_device', 'manual', 'extracted'));
