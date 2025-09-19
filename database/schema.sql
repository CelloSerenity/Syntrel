-- Copyright © Krypton 2019-Present - https://github.com/kkrypt0nn/Python-Discord-Bot-Template/blob/main/database/schema.sql

CREATE TABLE IF NOT EXISTS `warns` (
  `id` int(11) NOT NULL,
  `user_id` varchar(20) NOT NULL,
  `server_id` varchar(20) NOT NULL,
  `moderator_id` varchar(20) NOT NULL,
  `reason` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS `dm_relays` (
  `user_id` varchar(20) NOT NULL PRIMARY KEY,
  `channel_id` varchar(20) NOT NULL,
  `webhook_id` varchar(20) NOT NULL,
  `webhook_token` varchar(255) NOT NULL,
  `created_at` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP
);