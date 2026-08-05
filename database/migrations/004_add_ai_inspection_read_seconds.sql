ALTER TABLE ai_inspections
  ADD COLUMN read_seconds NUMERIC(3, 1) CHECK (
    read_seconds IS NULL OR (read_seconds >= 0 AND read_seconds <= 9.9)
  );
