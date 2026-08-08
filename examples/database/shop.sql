CREATE DATABASE IF NOT EXISTS shop
  DEFAULT CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE shop;

-- Recreate demo schema (children first).
SET FOREIGN_KEY_CHECKS = 0;
DROP TABLE IF EXISTS order_line;
DROP TABLE IF EXISTS `order`;
DROP TABLE IF EXISTS account_payment_method;
DROP TABLE IF EXISTS account_address;
DROP TABLE IF EXISTS account;
DROP TABLE IF EXISTS product;
SET FOREIGN_KEY_CHECKS = 1;

-- Auth / customer accounts (FastAPI library-test + shared shop schema)
CREATE TABLE account (
  account_id     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  username       VARCHAR(64)     NOT NULL,
  password_hash  VARCHAR(255)    NOT NULL,
  display_name   VARCHAR(128)    NOT NULL,
  email          VARCHAR(255)    NOT NULL,
  role           VARCHAR(32)     NOT NULL DEFAULT 'customer',
  active         TINYINT(1)      NOT NULL DEFAULT 1,
  created_at     DATETIME(3)     NOT NULL DEFAULT CURRENT_TIMESTAMP(3),
  PRIMARY KEY (account_id),
  UNIQUE KEY uq_account_username (username),
  UNIQUE KEY uq_account_email (email),
  CONSTRAINT chk_account_role CHECK (role IN ('admin', 'clerk', 'customer'))
) ENGINE=InnoDB;

CREATE TABLE account_address (
  address_id     BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  account_id     BIGINT UNSIGNED NOT NULL,
  address_kind   VARCHAR(16)     NOT NULL DEFAULT 'shipping',
  street         VARCHAR(128)    NOT NULL,
  house_number   VARCHAR(16)     NOT NULL,
  postal_code    CHAR(7)         NOT NULL,  -- NL: '1234 AB'
  city           VARCHAR(64)     NOT NULL,
  country        CHAR(2)         NOT NULL DEFAULT 'NL',
  PRIMARY KEY (address_id),
  KEY idx_address_account (account_id),
  CONSTRAINT fk_address_account
    FOREIGN KEY (account_id) REFERENCES account (account_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT chk_address_kind CHECK (address_kind IN ('billing', 'shipping'))
) ENGINE=InnoDB;

-- Fake payment instruments only: IBAN and/or card last4 — never full PAN/CVC.
CREATE TABLE account_payment_method (
  payment_method_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  account_id        BIGINT UNSIGNED NOT NULL,
  method_type       VARCHAR(16)     NOT NULL,
  label             VARCHAR(64)     NOT NULL,
  iban              VARCHAR(34)     NULL,
  card_brand        VARCHAR(32)     NULL,
  card_last4        CHAR(4)         NULL,
  exp_month         TINYINT UNSIGNED NULL,
  exp_year          SMALLINT UNSIGNED NULL,
  is_default        TINYINT(1)      NOT NULL DEFAULT 0,
  PRIMARY KEY (payment_method_id),
  KEY idx_payment_account (account_id),
  CONSTRAINT fk_payment_account
    FOREIGN KEY (account_id) REFERENCES account (account_id)
    ON DELETE CASCADE ON UPDATE CASCADE,
  CONSTRAINT chk_payment_type CHECK (method_type IN ('iban', 'card'))
) ENGINE=InnoDB;

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
  customer_ref VARCHAR(128)    NULL,
  account_id   BIGINT UNSIGNED NULL,
  PRIMARY KEY (order_id),
  KEY idx_order_placed_at (placed_at),
  KEY idx_order_account (account_id),
  CONSTRAINT fk_order_account
    FOREIGN KEY (account_id) REFERENCES account (account_id)
    ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Lines: composite identity (order_id, line_number) — matches OrderLine
CREATE TABLE order_line (
  order_id      BIGINT UNSIGNED NOT NULL,
  line_number   INT UNSIGNED    NOT NULL,
  product_id    BIGINT UNSIGNED NOT NULL,
  sku_snapshot  VARCHAR(64)     NOT NULL,
  unit_price    DECIMAL(12, 2)  NOT NULL,
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
