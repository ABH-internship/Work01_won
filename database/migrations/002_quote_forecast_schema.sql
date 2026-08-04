ALTER TABLE customers
  ADD COLUMN grade VARCHAR(1) NOT NULL DEFAULT 'B',
  ADD COLUMN is_existing BOOLEAN NOT NULL DEFAULT true,
  ADD CONSTRAINT customers_grade_check CHECK (grade IN ('A', 'B', 'C'));

CREATE TABLE quotes (
  id BIGSERIAL PRIMARY KEY,
  customer_id BIGINT NOT NULL REFERENCES customers(id),
  item_name VARCHAR(100) NOT NULL,
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  expected_due_date DATE NOT NULL,
  quote_stage VARCHAR(20) NOT NULL CHECK (quote_stage IN ('초기', '협의중', '유력')),
  estimated_amount NUMERIC(14, 2) NOT NULL CHECK (estimated_amount >= 0),
  probability NUMERIC(5, 4) NOT NULL CHECK (probability >= 0 AND probability <= 1),
  status VARCHAR(20) NOT NULL DEFAULT '진행중' CHECK (status IN ('진행중', '전환', '실패', '보류')),
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

ALTER TABLE orders
  ADD COLUMN quote_id BIGINT REFERENCES quotes(id);

CREATE TABLE quote_materials (
  id BIGSERIAL PRIMARY KEY,
  quote_id BIGINT NOT NULL REFERENCES quotes(id) ON DELETE CASCADE,
  material_id BIGINT NOT NULL REFERENCES materials(id),
  required_quantity NUMERIC(12, 2) NOT NULL CHECK (required_quantity > 0),
  UNIQUE (quote_id, material_id)
);

ALTER TABLE order_materials
  DROP CONSTRAINT IF EXISTS order_materials_order_id_material_id_lot_no_key,
  DROP COLUMN IF EXISTS lot_no,
  ADD CONSTRAINT order_materials_order_id_material_id_key UNIQUE (order_id, material_id);

CREATE INDEX idx_quotes_customer_id ON quotes(customer_id);
CREATE INDEX idx_quotes_expected_due_date ON quotes(expected_due_date);
CREATE INDEX idx_quotes_status ON quotes(status);
CREATE INDEX idx_orders_quote_id ON orders(quote_id);
CREATE INDEX idx_quote_materials_quote_id ON quote_materials(quote_id);
CREATE INDEX idx_quote_materials_material_id ON quote_materials(material_id);
