-- Migration: adds columns needed for the new exam features
-- (negative marking, shuffle, multiple attempts, publish/unpublish,
-- show/hide results, question types, attempt tracking).
--
-- Run this once against your existing MySQL database:
--   mysql -u <user> -p <db_name> < migrate_new_features.sql
--
-- If you don't have any real data yet, it's simpler to just drop the
-- database and let the app recreate everything via db.create_all()
-- on next run.

ALTER TABLE `exams`
  ADD COLUMN `negative_marking_enabled` TINYINT(1) NOT NULL DEFAULT 0,
  ADD COLUMN `negative_marks_value` FLOAT NOT NULL DEFAULT 0,
  ADD COLUMN `shuffle_questions` TINYINT(1) NOT NULL DEFAULT 0,
  ADD COLUMN `shuffle_options` TINYINT(1) NOT NULL DEFAULT 0,
  ADD COLUMN `max_attempts` INT NOT NULL DEFAULT 1,
  ADD COLUMN `show_results` TINYINT(1) NOT NULL DEFAULT 1,
  ADD COLUMN `is_published` TINYINT(1) NOT NULL DEFAULT 1,
  ADD COLUMN `min_submit_minutes` INT NOT NULL DEFAULT 0,
  ADD COLUMN `webcam_proctoring_enabled` TINYINT(1) NOT NULL DEFAULT 0;

ALTER TABLE `questions`
  ADD COLUMN `question_type` VARCHAR(20) NOT NULL DEFAULT 'mcq',
  ADD COLUMN `correct_text` VARCHAR(255) NULL,
  MODIFY COLUMN `option_a` VARCHAR(255) NULL,
  MODIFY COLUMN `option_b` VARCHAR(255) NULL,
  MODIFY COLUMN `option_c` VARCHAR(255) NULL,
  MODIFY COLUMN `option_d` VARCHAR(255) NULL,
  MODIFY COLUMN `correct_option` VARCHAR(10) NULL;

ALTER TABLE `results`
  ADD COLUMN `attempt_number` INT NOT NULL DEFAULT 1,
  ADD COLUMN `terminated` TINYINT(1) NOT NULL DEFAULT 0,
  ADD COLUMN `termination_reason` VARCHAR(50) NULL,
  MODIFY COLUMN `score` FLOAT NOT NULL;

ALTER TABLE `student_answers`
  ADD COLUMN `attempt_number` INT NOT NULL DEFAULT 1,
  MODIFY COLUMN `selected_option` VARCHAR(255) NULL;
