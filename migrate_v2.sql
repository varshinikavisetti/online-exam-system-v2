-- Migration: adds student profile fields and exam scheduling columns.
--
-- Run this once against your existing MySQL database:
--   mysql -u <user> -p <db_name> < migrate_v2.sql
--
-- All new columns are nullable / have safe defaults, so existing rows and
-- existing app behaviour are unaffected until you start using the new
-- fields (student profile info, exam scheduling, email notifications).

ALTER TABLE `users`
  ADD COLUMN `mobile_number` VARCHAR(20) NULL,
  ADD COLUMN `year_of_study` VARCHAR(20) NULL,
  ADD COLUMN `department` VARCHAR(100) NULL,
  ADD COLUMN `roll_number` VARCHAR(50) NULL;

ALTER TABLE `exams`
  ADD COLUMN `scheduled_start` DATETIME NULL,
  ADD COLUMN `scheduled_end` DATETIME NULL;
