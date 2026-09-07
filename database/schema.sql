CREATE DATABASE IF NOT EXISTS taipei_day_trip
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE taipei_day_trip;

CREATE TABLE IF NOT EXISTS categories (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(50) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_categories_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS mrt_stations (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(50) NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_mrt_stations_name (name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attractions (
  id BIGINT UNSIGNED NOT NULL,
  name VARCHAR(255) NOT NULL,
  category_id BIGINT UNSIGNED NOT NULL,
  description TEXT NOT NULL,
  address VARCHAR(255) NOT NULL,
  transport TEXT NOT NULL,
  mrt_id BIGINT UNSIGNED NOT NULL,
  latitude DECIMAL(10, 6) NOT NULL,
  longitude DECIMAL(10, 6) NOT NULL,
  memo_time TEXT NULL,
  rate TINYINT UNSIGNED NULL,
  raw_serial_no VARCHAR(50) NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_attractions_category_id (category_id),
  KEY idx_attractions_mrt_id (mrt_id),
  KEY idx_attractions_name (name),
  CONSTRAINT fk_attractions_category
    FOREIGN KEY (category_id) REFERENCES categories (id),
  CONSTRAINT fk_attractions_mrt
    FOREIGN KEY (mrt_id) REFERENCES mrt_stations (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS attraction_images (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  attraction_id BIGINT UNSIGNED NOT NULL,
  image_url VARCHAR(512) NOT NULL,
  position INT UNSIGNED NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_attraction_images_position (attraction_id, position),
  KEY idx_attraction_images_attraction_id (attraction_id),
  CONSTRAINT fk_attraction_images_attraction
    FOREIGN KEY (attraction_id) REFERENCES attractions (id)
    ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS users (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  name VARCHAR(100) NOT NULL,
  email VARCHAR(255) NOT NULL,
  password VARCHAR(255) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_users_email (email)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS bookings (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  user_id BIGINT UNSIGNED NOT NULL,
  attraction_id BIGINT UNSIGNED NOT NULL,
  booking_date DATE NOT NULL,
  booking_time ENUM('morning', 'afternoon') NOT NULL,
  price INT UNSIGNED NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  UNIQUE KEY uq_bookings_user_id (user_id),
  KEY idx_bookings_attraction_id (attraction_id),
  CONSTRAINT fk_bookings_user FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE,
  CONSTRAINT fk_bookings_attraction FOREIGN KEY (attraction_id) REFERENCES attractions (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS orders (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  order_number VARCHAR(50) NOT NULL,
  user_id BIGINT UNSIGNED NOT NULL,
  price INT UNSIGNED NOT NULL,
  status ENUM('UNPAID', 'PAID') NOT NULL DEFAULT 'UNPAID',
  contact_name VARCHAR(100) NOT NULL,
  contact_email VARCHAR(255) NOT NULL,
  contact_phone VARCHAR(30) NOT NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  paid_at TIMESTAMP NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_orders_number (order_number),
  KEY idx_orders_user_id (user_id),
  CONSTRAINT fk_orders_user FOREIGN KEY (user_id) REFERENCES users (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS order_trips (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  order_id BIGINT UNSIGNED NOT NULL,
  attraction_id BIGINT UNSIGNED NOT NULL,
  attraction_name VARCHAR(255) NOT NULL,
  attraction_address VARCHAR(255) NOT NULL,
  attraction_image VARCHAR(512) NOT NULL,
  trip_date DATE NOT NULL,
  trip_time ENUM('morning', 'afternoon') NOT NULL,
  PRIMARY KEY (id),
  UNIQUE KEY uq_order_trips_order_id (order_id),
  CONSTRAINT fk_order_trips_order FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE,
  CONSTRAINT fk_order_trips_attraction FOREIGN KEY (attraction_id) REFERENCES attractions (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS payments (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT,
  order_id BIGINT UNSIGNED NOT NULL,
  tappay_status INT NOT NULL,
  message VARCHAR(500) NOT NULL,
  rec_trade_id VARCHAR(40) NULL,
  raw_response JSON NULL,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (id),
  KEY idx_payments_order_id (order_id),
  CONSTRAINT fk_payments_order FOREIGN KEY (order_id) REFERENCES orders (id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
