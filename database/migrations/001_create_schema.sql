CREATE TABLE customers (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE
);

CREATE TABLE orders (
  id BIGSERIAL PRIMARY KEY,
  customer_id BIGINT NOT NULL REFERENCES customers(id),
  item_name VARCHAR(100) NOT NULL,
  quantity INTEGER NOT NULL CHECK (quantity > 0),
  due_date DATE NOT NULL,
  status VARCHAR(30) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE units (
  id BIGSERIAL PRIMARY KEY,
  order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  unit_no VARCHAR(30) NOT NULL UNIQUE,
  item_detail VARCHAR(120),
  status VARCHAR(30) NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE process_masters (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(50) NOT NULL UNIQUE,
  sequence INTEGER NOT NULL UNIQUE CHECK (sequence > 0),
  standard_days NUMERIC(5, 2) NOT NULL CHECK (standard_days >= 0)
);

CREATE TABLE unit_processes (
  id BIGSERIAL PRIMARY KEY,
  unit_id BIGINT NOT NULL REFERENCES units(id) ON DELETE CASCADE,
  process_master_id BIGINT NOT NULL REFERENCES process_masters(id),
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  status VARCHAR(30) NOT NULL,
  result_quantity INTEGER CHECK (result_quantity IS NULL OR result_quantity >= 0),
  is_rework BOOLEAN NOT NULL DEFAULT false,
  UNIQUE (unit_id, process_master_id)
);

CREATE TABLE materials (
  id BIGSERIAL PRIMARY KEY,
  name VARCHAR(100) NOT NULL UNIQUE,
  unit VARCHAR(20) NOT NULL,
  lead_time_days INTEGER NOT NULL DEFAULT 0 CHECK (lead_time_days >= 0)
);

CREATE TABLE inventories (
  id BIGSERIAL PRIMARY KEY,
  material_id BIGINT NOT NULL REFERENCES materials(id),
  lot_no VARCHAR(50) NOT NULL,
  purchased_quantity NUMERIC(12, 2) NOT NULL CHECK (purchased_quantity >= 0),
  current_quantity NUMERIC(12, 2) NOT NULL CHECK (current_quantity >= 0),
  received_at DATE NOT NULL,
  UNIQUE (material_id, lot_no),
  CHECK (current_quantity <= purchased_quantity)
);

CREATE TABLE order_materials (
  id BIGSERIAL PRIMARY KEY,
  order_id BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  material_id BIGINT NOT NULL REFERENCES materials(id),
  required_quantity NUMERIC(12, 2) NOT NULL CHECK (required_quantity > 0),
  lot_no VARCHAR(50),
  inventory_id BIGINT REFERENCES inventories(id),
  UNIQUE (order_id, material_id, lot_no)
);

CREATE TABLE ai_inspections (
  id BIGSERIAL PRIMARY KEY,
  unit_id BIGINT NOT NULL REFERENCES units(id) ON DELETE CASCADE,
  inspection_type VARCHAR(50) NOT NULL,
  result VARCHAR(20) NOT NULL,
  confidence NUMERIC(5, 2) CHECK (confidence IS NULL OR (confidence >= 0 AND confidence <= 100)),
  finding TEXT,
  inspected_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE tests (
  id BIGSERIAL PRIMARY KEY,
  unit_id BIGINT NOT NULL REFERENCES units(id) ON DELETE CASCADE,
  test_item VARCHAR(80) NOT NULL,
  measured_value VARCHAR(80) NOT NULL,
  criteria VARCHAR(80) NOT NULL,
  result VARCHAR(20) NOT NULL,
  tester VARCHAR(50) NOT NULL,
  tested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE events (
  id BIGSERIAL PRIMARY KEY,
  unit_id BIGINT REFERENCES units(id) ON DELETE SET NULL,
  event_type VARCHAR(50) NOT NULL,
  message TEXT NOT NULL,
  severity VARCHAR(20) NOT NULL,
  occurred_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_orders_due_date ON orders(due_date);
CREATE INDEX idx_units_order_id ON units(order_id);
CREATE INDEX idx_unit_processes_unit_id ON unit_processes(unit_id);
CREATE INDEX idx_unit_processes_status ON unit_processes(status);
CREATE INDEX idx_order_materials_order_id ON order_materials(order_id);
CREATE INDEX idx_inventories_material_id ON inventories(material_id);
CREATE INDEX idx_ai_inspections_unit_id ON ai_inspections(unit_id);
CREATE INDEX idx_tests_unit_id ON tests(unit_id);
CREATE INDEX idx_events_occurred_at ON events(occurred_at DESC);
