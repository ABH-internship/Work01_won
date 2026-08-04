ALTER TABLE customers
  DROP CONSTRAINT IF EXISTS customers_grade_check;

ALTER TABLE customers
  ADD CONSTRAINT customers_grade_check CHECK (grade IN ('A', 'B', 'C', 'N'));
