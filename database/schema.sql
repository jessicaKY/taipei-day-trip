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
