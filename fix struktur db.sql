-- --------------------------------------------------------
-- Host:                         127.0.0.1
-- Server version:               8.0.30 - MySQL Community Server - GPL
-- Server OS:                    Win64
-- HeidiSQL Version:             12.1.0.6537
-- --------------------------------------------------------

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET NAMES utf8 */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;


-- Dumping database structure for trading_db
CREATE DATABASE IF NOT EXISTS `trading_db` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;
USE `trading_db`;

-- Dumping structure for table trading_db.barang
CREATE TABLE IF NOT EXISTS `barang` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `nama` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `satuan` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=155 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table trading_db.biaya_tambahan
CREATE TABLE IF NOT EXISTS `biaya_tambahan` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `nama` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `tanggal` date NOT NULL,
  `jumlah` decimal(15,2) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table trading_db.customer
CREATE TABLE IF NOT EXISTS `customer` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `nama` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `top` bigint DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table trading_db.customer_pricelist
CREATE TABLE IF NOT EXISTS `customer_pricelist` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `id_customer` bigint unsigned NOT NULL,
  `id_barang` bigint unsigned NOT NULL,
  `harga` decimal(15,2) NOT NULL,
  `updated_at` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `id_customer` (`id_customer`),
  KEY `id_barang` (`id_barang`),
  CONSTRAINT `FK_cust_pricelist_id_barang` FOREIGN KEY (`id_barang`) REFERENCES `barang` (`id`) ON DELETE CASCADE,
  CONSTRAINT `FK_cust_pricelist_id_customer` FOREIGN KEY (`id_customer`) REFERENCES `customer` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table trading_db.hutang
CREATE TABLE IF NOT EXISTS `hutang` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `id_pembelian` bigint unsigned NOT NULL,
  `no_nota` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `tanggal` date NOT NULL,
  `due_date` date NOT NULL,
  `id_supplier` bigint unsigned NOT NULL,
  `total` decimal(15,2) NOT NULL,
  `terbayar` decimal(15,2) NOT NULL,
  `sisa` decimal(15,2) NOT NULL,
  `status` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` date DEFAULT NULL,
  `updated_at` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `id_pembelian` (`id_pembelian`),
  KEY `id_supplier` (`id_supplier`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table trading_db.pembayaran_hutang
CREATE TABLE IF NOT EXISTS `pembayaran_hutang` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `id_hutang` bigint unsigned NOT NULL,
  `bukti_penerimaan` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `tanggal_bayar` date NOT NULL,
  `jumlah` decimal(15,2) NOT NULL,
  `keterangan` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `id_hutang` (`id_hutang`),
  CONSTRAINT `FK_pembayaran_hutang_id_hutang` FOREIGN KEY (`id_hutang`) REFERENCES `hutang` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table trading_db.pembayaran_piutang
CREATE TABLE IF NOT EXISTS `pembayaran_piutang` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `id_piutang` bigint unsigned NOT NULL,
  `bukti_penerimaan` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `tanggal_bayar` date NOT NULL,
  `jumlah` decimal(15,2) NOT NULL,
  `keterangan` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `id_piutang` (`id_piutang`),
  CONSTRAINT `FK_pembayaran_piutang_id_piutang` FOREIGN KEY (`id_piutang`) REFERENCES `piutang` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table trading_db.pembelian
CREATE TABLE IF NOT EXISTS `pembelian` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `no_nota` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `tanggal` date NOT NULL,
  `id_supplier` bigint unsigned NOT NULL,
  `total` decimal(15,2) NOT NULL,
  `top` bigint DEFAULT NULL,
  `tipe` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  PRIMARY KEY (`id`),
  KEY `id_supplier` (`id_supplier`),
  CONSTRAINT `FK_pembelian_id_supplier` FOREIGN KEY (`id_supplier`) REFERENCES `supplier` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=10 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table trading_db.pembelian_detail
CREATE TABLE IF NOT EXISTS `pembelian_detail` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `id_pembelian` bigint unsigned NOT NULL,
  `id_barang` bigint unsigned NOT NULL,
  `kuantitas` bigint NOT NULL,
  `harga_satuan` decimal(15,2) NOT NULL,
  `subtotal` decimal(15,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `id_pembelian` (`id_pembelian`),
  KEY `id_barang` (`id_barang`),
  CONSTRAINT `FK_pembelian_detail_id_barang` FOREIGN KEY (`id_barang`) REFERENCES `barang` (`id`),
  CONSTRAINT `FK_pembelian_detail_id_pembelian` FOREIGN KEY (`id_pembelian`) REFERENCES `pembelian` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table trading_db.penjualan
CREATE TABLE IF NOT EXISTS `penjualan` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `no_nota` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `tanggal` date NOT NULL,
  `id_customer` bigint unsigned NOT NULL DEFAULT '0',
  `total` decimal(15,2) NOT NULL DEFAULT '0.00',
  `top` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `id_customer` (`id_customer`),
  CONSTRAINT `FK_penjualan_id_customer` FOREIGN KEY (`id_customer`) REFERENCES `customer` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=11 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table trading_db.penjualan_detail
CREATE TABLE IF NOT EXISTS `penjualan_detail` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `id_penjualan` bigint unsigned NOT NULL,
  `id_barang` bigint unsigned NOT NULL,
  `kuantitas` bigint NOT NULL,
  `harga_satuan` decimal(15,2) NOT NULL,
  `subtotal` decimal(15,2) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `id_penjualan` (`id_penjualan`),
  KEY `id_barang` (`id_barang`),
  CONSTRAINT `FK_penjualan_detail_id_barang` FOREIGN KEY (`id_barang`) REFERENCES `barang` (`id`),
  CONSTRAINT `FK_penjualan_detail_id_penjualan` FOREIGN KEY (`id_penjualan`) REFERENCES `penjualan` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=13 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table trading_db.piutang
CREATE TABLE IF NOT EXISTS `piutang` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `id_penjualan` bigint unsigned NOT NULL,
  `no_nota` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT '',
  `tanggal` date NOT NULL,
  `due_date` date NOT NULL,
  `id_customer` bigint unsigned NOT NULL DEFAULT '0',
  `total` decimal(15,2) NOT NULL,
  `terbayar` decimal(15,2) NOT NULL,
  `sisa` decimal(15,2) NOT NULL,
  `status` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` date DEFAULT NULL,
  `updated_at` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `id_penjualan` (`id_penjualan`),
  KEY `id_customer` (`id_customer`),
  CONSTRAINT `FK_piutang_id_penjualan` FOREIGN KEY (`id_penjualan`) REFERENCES `penjualan` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table trading_db.supplier
CREATE TABLE IF NOT EXISTS `supplier` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `nama` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `top` bigint DEFAULT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

-- Dumping structure for table trading_db.supplier_pricelist
CREATE TABLE IF NOT EXISTS `supplier_pricelist` (
  `id` bigint unsigned NOT NULL AUTO_INCREMENT,
  `id_supplier` bigint unsigned NOT NULL,
  `id_barang` bigint unsigned NOT NULL,
  `harga` decimal(15,2) NOT NULL,
  `updated_at` date DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `id_supplier` (`id_supplier`),
  KEY `id_barang` (`id_barang`),
  CONSTRAINT `FK_supp_pricelist_id_barang` FOREIGN KEY (`id_barang`) REFERENCES `barang` (`id`) ON DELETE CASCADE,
  CONSTRAINT `FK_supp_pricelist_id_supplier` FOREIGN KEY (`id_supplier`) REFERENCES `supplier` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=12 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Data exporting was unselected.

/*!40103 SET TIME_ZONE=IFNULL(@OLD_TIME_ZONE, 'system') */;
/*!40101 SET SQL_MODE=IFNULL(@OLD_SQL_MODE, '') */;
/*!40014 SET FOREIGN_KEY_CHECKS=IFNULL(@OLD_FOREIGN_KEY_CHECKS, 1) */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40111 SET SQL_NOTES=IFNULL(@OLD_SQL_NOTES, 1) */;
