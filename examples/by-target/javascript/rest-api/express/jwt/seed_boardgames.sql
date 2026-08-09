-- Seed: Dutch board-game shop sample data for the `shop` schema.
--
-- Apply after shop.sql (database + empty tables already exist):
--
--   mysql -u pys -p shop < examples/database/seed_boardgames.sql
--
-- Or from the MySQL client:
--
--   USE shop;
--   SOURCE examples/database/seed_boardgames.sql;
--
-- Prices are illustrative EUR snapshots (incl. BTW) inspired by common NL
-- retail listings around Aug 2026 — mainly bol.com, Spellenhuis.nl, Lobbes,
-- and 999games.nl. They are NOT live scrapes; shops change prices often.
-- Re-run clears existing shop rows so the demo catalog stays reproducible.
--
-- Demo login password for every seeded account: Welcome1!
-- (bcrypt cost 12; hash below is shared so FastAPI / teaching apps stay in sync)

USE shop;

SET NAMES utf8mb4;

-- Wipe demo data (children first because of FKs).
-- WHERE on key columns so MySQL Workbench "safe updates" (Error 1175) allows it.
DELETE FROM order_line WHERE order_id >= 1;
DELETE FROM `order` WHERE order_id >= 1;
DELETE FROM account_payment_method WHERE payment_method_id >= 1;
DELETE FROM account_address WHERE address_id >= 1;
DELETE FROM account WHERE account_id >= 1;
DELETE FROM product WHERE product_id >= 1;

ALTER TABLE product AUTO_INCREMENT = 1;
ALTER TABLE `order` AUTO_INCREMENT = 1;
ALTER TABLE account AUTO_INCREMENT = 1;
ALTER TABLE account_address AUTO_INCREMENT = 1;
ALTER TABLE account_payment_method AUTO_INCREMENT = 1;

-- Shared bcrypt for Welcome1! (do not use in production).
SET @pwd := '$2b$12$e2F7iJPHhPUkfRRa9ttwzeIpHZwRRlSxiO7Vn5fGH1EmYWkPcQRAy';

-- ---------------------------------------------------------------------------
-- Accounts — multicultural NL names; roles for JWT / FastAPI field research.
-- ---------------------------------------------------------------------------

INSERT INTO account
  (account_id, username, password_hash, display_name, email, role, active)
VALUES
  (1, 'admin',    @pwd, 'Admin Desk',           'admin@spellenhuis.example',    'admin',    1),
  (2, 'clerk',    @pwd, 'Floor Clerk',          'clerk@spellenhuis.example',    'clerk',    1),
  (3, 'amira',    @pwd, 'Amira El Amrani',      'amira.elamrani@example.nl',   'customer', 1),
  (4, 'mehmet',   @pwd, 'Mehmet Yilmaz',        'mehmet.yilmaz@example.nl',    'customer', 1),
  (5, 'priya',    @pwd, 'Priya Sharma',         'priya.sharma@example.nl',     'customer', 1),
  (6, 'fatima',   @pwd, 'Fatima Al-Hassan',     'fatima.alhassan@example.nl',  'customer', 1),
  (7, 'lars',     @pwd, 'Lars Bergstrom',       'lars.bergstrom@example.nl',   'customer', 1),
  (8, 'chinonso', @pwd, 'Chinonso Okafor',      'chinonso.okafor@example.nl',  'customer', 1),
  (9, 'sophie',   @pwd, 'Sophie de Vries',      'sophie.devries@example.nl',   'customer', 1),
  (10,'jan',      @pwd, 'Jan de Jong',          'jan.dejong@example.nl',       'customer', 1);

INSERT INTO account_address
  (address_id, account_id, address_kind, street, house_number, postal_code, city, country)
VALUES
  (1,  3, 'shipping', 'Javastraat',          '42',  '1094 HE', 'Amsterdam',  'NL'),
  (2,  3, 'billing',  'Javastraat',          '42',  '1094 HE', 'Amsterdam',  'NL'),
  (3,  4, 'shipping', 'Kinkerstraat',        '88A', '1053 EL', 'Amsterdam',  'NL'),
  (4,  5, 'shipping', 'Voorstraat',          '12',  '3512 AH', 'Utrecht',    'NL'),
  (5,  6, 'shipping', 'Westersingel',        '7',   '3014 GS', 'Rotterdam',  'NL'),
  (6,  7, 'shipping', 'Laan van Meerdervoort','210','2517 AN', 'Den Haag',   'NL'),
  (7,  8, 'shipping', 'Wilhelminaplein',     '1',   '5611 MA', 'Eindhoven',  'NL'),
  (8,  9, 'shipping', 'Nieuwendijk',         '15',  '1012 MC', 'Amsterdam',  'NL'),
  (9, 10, 'shipping', 'Oudegracht',          '99',  '3511 AD', 'Utrecht',    'NL'),
  (10,10, 'billing',  'Oudegracht',          '99',  '3511 AD', 'Utrecht',    'NL');

-- Fake instruments only: IBAN and/or card last4 — never full PAN/CVC.
INSERT INTO account_payment_method
  (payment_method_id, account_id, method_type, label, iban, card_brand, card_last4,
   exp_month, exp_year, is_default)
VALUES
  (1,  3, 'iban', 'Amira — ING',           'NL91INGB0007654321', NULL,     NULL, NULL, NULL, 1),
  (2,  4, 'iban', 'Mehmet — Rabobank',     'NL20RABO0123456789', NULL,     NULL, NULL, NULL, 1),
  (3,  5, 'card', 'Priya — Visa ****4242', NULL, 'visa',       '4242', 8, 2028, 1),
  (4,  6, 'iban', 'Fatima — ABN AMRO',     'NL39ABNA0417164300', NULL,     NULL, NULL, NULL, 1),
  (5,  7, 'card', 'Lars — Mastercard',     NULL, 'mastercard', '5555', 3, 2027, 1),
  (6,  8, 'iban', 'Chinonso — SNS',        'NL02SNSB0901234567', NULL,     NULL, NULL, NULL, 1),
  (7,  9, 'iban', 'Sophie — ASN',          'NL18ASNB0701234567', NULL,     NULL, NULL, NULL, 1),
  (8, 10, 'card', 'Jan — Visa ****1111',   NULL, 'visa',       '1111', 12, 2029, 1),
  (9, 10, 'iban', 'Jan — Triodos',         'NL13TRIO0396683220', NULL,     NULL, NULL, NULL, 0);

-- ---------------------------------------------------------------------------
-- Catalog — SKUs are shop-local codes (not publisher EANs).
-- ---------------------------------------------------------------------------

INSERT INTO product (product_id, sku, name, unit_price, active) VALUES
  -- Basisspellen (NL waar beschikbaar)
  (1,  'BG-CATAN-BASE-NL',
       'Catan — Basisspel (NL, 999 Games)',
       39.99, 1),
  (2,  'BG-TTR-EUROPE-NL',
       'Ticket to Ride: Europe (NL, Days of Wonder)',
       32.99, 1),
  (3,  'BG-AZUL-NL',
       'Azul — Tactisch tegelspecial (NL, Next Move)',
       26.99, 1),
  (4,  'BG-WINGSPAN-NL',
       'Wingspan (NL, 999 Games)',
       42.99, 1),
  (5,  'BG-DIXIT-BASE-NL',
       'Dixit — Basisspel (NL)',
       29.99, 1),
  (6,  'BG-7W-DICE-NL',
       '7 Wonders Dice (NL)',
       25.49, 1),

  -- Uitbreidingen / big box
  (7,  'BG-CATAN-SEAFARERS-NL',
       'Catan: Uitbreiding Zeevaarders (NL)',
       42.99, 1),
  (8,  'BG-CATAN-CITIES-EN',
       'Catan: Cities & Knights 6th ed. (EN)',
       54.99, 1),
  (9,  'BG-CATAN-BIGBOX-NL',
       'Catan: Big Box (NL) — basisspel + 5/6 + scenario''s',
       39.91, 1),
  (10, 'BG-TTR-NEDERLAND',
       'Ticket to Ride: Nederland — uitbreiding (NL)',
       19.89, 1),

  -- Compact / dice / family fillers
  (11, 'BG-CATAN-DICE',
       'Catan — Het Dobbelspel',
       11.99, 1),
  (12, 'BG-CATAN-FLIP7',
       'Flip 7 Compact (EN, 999 Games)',
       11.99, 1),

  -- Accessoires (Spellenhuis / specialty-shop range)
  (13, 'ACC-SLEEVE-CATAN-MATTE',
       'Gamegenic Matte sleeves Catan-size 56×82 mm (50)',
       3.95, 1),
  (14, 'ACC-SLEEVE-EU-STD-MATTE',
       'Gamegenic Matte sleeves Standard European 62×94 mm (50)',
       4.50, 1),
  (15, 'ACC-DS-STD-BLACK-MATTE',
       'Dragon Shield Standard — Black Matte (100)',
       11.00, 1),
  (16, 'ACC-DICE-TRAY-FOLD',
       'Opvouwbare dobbelsteenbak (universeel)',
       14.08, 1),
  (17, 'ACC-SCOREPAD-CATAN',
       'Scoreblok Catan (50 bladen)',
       4.95, 1),

  -- Inactive: still in DB for “active” demos / soft-delete teaching
  (18, 'BG-DISCO-OLD-CATAN',
       'Catan — oude kartonnen editie (uit assortiment)',
       29.95, 0);

-- ---------------------------------------------------------------------------
-- Sample orders — Dutch customer refs; some linked to account_id.
-- placed_at uses fixed timestamps so screenshots / tutorials stay stable.
-- ---------------------------------------------------------------------------

INSERT INTO `order` (order_id, placed_at, status, customer_ref, account_id) VALUES
  (1, '2026-07-12 14:22:05.000', 'paid',      'klant:jan.dejong@example.nl',     10),
  (2, '2026-07-18 09:05:41.000', 'shipped',   'Spellenclub Utrecht',             5),
  (3, '2026-07-29 19:40:12.000', 'placed',    'klant:sophie.visser@example.nl', 9),
  (4, '2026-08-01 11:15:00.000', 'cancelled', 'walk-in:Den Haag',                NULL),
  -- Deliberate contrast for nullable<T>: absent is not an empty string.
  (5, '2026-08-02 10:00:00.000', 'placed',    NULL,                             NULL),
  (6, '2026-08-02 10:05:00.000', 'placed',    '',                               3);

-- Lines snapshot SKU + unit_price at order time (catalog may change later).
INSERT INTO order_line
  (order_id, line_number, product_id, sku_snapshot, unit_price, quantity)
VALUES
  -- Order 1: starter evening for 4
  (1, 1, 1,  'BG-CATAN-BASE-NL',        39.99, 1),
  (1, 2, 13, 'ACC-SLEEVE-CATAN-MATTE',   3.95, 2),
  (1, 3, 17, 'ACC-SCOREPAD-CATAN',       4.95, 1),

  -- Order 2: club night restock
  (2, 1, 2,  'BG-TTR-EUROPE-NL',        32.99, 1),
  (2, 2, 10, 'BG-TTR-NEDERLAND',        19.89, 1),
  (2, 3, 3,  'BG-AZUL-NL',              26.99, 2),
  (2, 4, 15, 'ACC-DS-STD-BLACK-MATTE',  11.00, 3),

  -- Order 3: Wingspan + dice tray
  (3, 1, 4,  'BG-WINGSPAN-NL',          42.99, 1),
  (3, 2, 16, 'ACC-DICE-TRAY-FOLD',      14.08, 1),
  (3, 3, 5,  'BG-DIXIT-BASE-NL',        29.99, 1),

  -- Order 4: cancelled before ship — still useful for status demos
  (4, 1, 9,  'BG-CATAN-BIGBOX-NL',      39.91, 1);

-- Keep AUTO_INCREMENT past seeded ids if readers INSERT more via the app.
ALTER TABLE product AUTO_INCREMENT = 100;
ALTER TABLE `order` AUTO_INCREMENT = 100;
ALTER TABLE account AUTO_INCREMENT = 100;
ALTER TABLE account_address AUTO_INCREMENT = 100;
ALTER TABLE account_payment_method AUTO_INCREMENT = 100;
