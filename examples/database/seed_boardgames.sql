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

USE shop;

SET NAMES utf8mb4;

-- Wipe demo data (children first because of FKs).
-- WHERE on key columns so MySQL Workbench "safe updates" (Error 1175) allows it.
DELETE FROM order_line WHERE order_id >= 1;
DELETE FROM `order` WHERE order_id >= 1;
DELETE FROM product WHERE product_id >= 1;

ALTER TABLE product AUTO_INCREMENT = 1;
ALTER TABLE `order` AUTO_INCREMENT = 1;

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
-- Sample orders — Dutch customer refs as a small indie webshop might store.
-- placed_at uses fixed timestamps so screenshots / tutorials stay stable.
-- ---------------------------------------------------------------------------

INSERT INTO `order` (order_id, placed_at, status, customer_ref) VALUES
  (1, '2026-07-12 14:22:05.000', 'paid',    'klant:jan.dejong@example.nl'),
  (2, '2026-07-18 09:05:41.000', 'shipped', 'Spellenclub Utrecht'),
  (3, '2026-07-29 19:40:12.000', 'placed',  'klant:sophie.visser@example.nl'),
  (4, '2026-08-01 11:15:00.000', 'cancelled', 'walk-in:Den Haag');

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
