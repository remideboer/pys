CREATE DATABASE IF NOT EXISTS shop
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE shop;

-- Catalog: one row per sellable item (stable business key = sku)
CREATE TABLE product (
  product_id   BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  sku          VARCHAR(64)     NOT NULL,
  name         VARCHAR(255)    NOT NULL,
  unit_price   DECIMAL(12, 2)  NOT NULL,
  active       TINYINT(1)      NOT NULL DEFAULT 1,
  created_at   DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (product_id),
  UNIQUE KEY uq_product_sku (sku),
  CONSTRAINT chk_product_price CHECK (unit_price >= 0)
) ENGINE=InnoDB;

-- Header: identity = order_id (matches entity Order)
CREATE TABLE `order` (
  order_id     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  placed_at    DATETIME(3)     NOT NULL,
  status       VARCHAR(32)     NOT NULL DEFAULT 'placed',
  customer_ref VARCHAR(128)    NULL,          -- optional; drop if you don't need it yet
  PRIMARY KEY (order_id),
  KEY idx_order_placed_at (placed_at)
) ENGINE=InnoDB;

-- Lines: composite identity (order_id, line_number) — matches OrderLine
CREATE TABLE order_line (
  order_id      BIGINT UNSIGNED NOT NULL,
  line_number   INT UNSIGNED    NOT NULL,
  product_id    BIGINT UNSIGNED NOT NULL,
  sku_snapshot  VARCHAR(64)     NOT NULL,     -- denormalized SKU at order time
  unit_price    DECIMAL(12, 2)  NOT NULL,     -- price snapshot (catalog may change later)
  quantity      INT UNSIGNED    NOT NULL,
  PRIMARY KEY (order_id, line_number),
  KEY idx_order_line_product (product_id),
  CONSTRAINT fk_order_line_order
    FOREIGN KEY (order_id) REFERENCES `order` (order_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT fk_order_line_product
    FOREIGN KEY (product_id) REFERENCES product (product_id)
    ON DELETE RESTRICT ON UPDATE CASCADE,
  CONSTRAINT chk_order_line_qty CHECK (quantity > 0),
  CONSTRAINT chk_order_line_price CHECK (unit_price >= 0)
) ENGINE=InnoDB;