/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19-11.4.8-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: 127.0.0.1    Database: jarvis_ai_sitebuilder
-- ------------------------------------------------------
-- Server version	11.4.8-MariaDB-ubu2204

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*M!100616 SET @OLD_NOTE_VERBOSITY=@@NOTE_VERBOSITY, NOTE_VERBOSITY=0 */;

--
-- Table structure for table `core_aimodelssettings`
--

DROP TABLE IF EXISTS `core_aimodelssettings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_aimodelssettings` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `type` varchar(20) NOT NULL,
  `model` varchar(20) NOT NULL,
  `prompt_tokens_price_1m` decimal(14,2) NOT NULL,
  `completion_tokens_price_1m` decimal(14,2) NOT NULL,
  `my_margin` double NOT NULL,
  `format` varchar(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `core_aimodelssettings_type_model_7411591e_uniq` (`type`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_aimodelssettings`
--

LOCK TABLES `core_aimodelssettings` WRITE;
/*!40000 ALTER TABLE `core_aimodelssettings` DISABLE KEYS */;
INSERT INTO `core_aimodelssettings` VALUES
(1,'CHATGPT','gpt-5',10.00,60.00,2,'image'),
(2,'CHATGPT','gpt-5.1',1.25,10.00,2,'text'),
(3,'CHATGPT','gpt-image-1',10.00,40.00,2,'image'),
(4,'CHATGPT','gpt-4o',10.00,60.00,2,'image');
/*!40000 ALTER TABLE `core_aimodelssettings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_systemprompts`
--

DROP TABLE IF EXISTS `core_systemprompts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_systemprompts` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `type` varchar(64) NOT NULL,
  `prompt` longtext NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_systemprompts`
--

LOCK TABLES `core_systemprompts` WRITE;
/*!40000 ALTER TABLE `core_systemprompts` DISABLE KEYS */;
INSERT INTO `core_systemprompts` VALUES
(1,'basic_prompt','Ты HTML верстальщик, помогаешь пользователю сверстать сайт'),
(2,'name_classification','Придумай имя сайта исходя из промпта на его создание. Длина имени не более 30 символов. Верни мне только имя, которое я сразу покажу пользователю'),
(3,'basic_json','Выполни запрос, который отправил тебе пользователь\r\nв ответе я от тебя ожидаю json текст, со списком операций, без лишних данных, чтобы я смог сразу передать в парсер\r\n\r\n[\r\n    {file_operation:\'\', file_path:\'\', \'text\':\'\', \'prompt\': \'\'}\r\n    ...\r\n]\r\n\r\nв котором\r\nfile_path - полный путь к файлу, над которым нужно произвести операцию, все пути относительные от корня, т.е. index.html должен лежать в ./index.html\r\nfile_operation - операция над файлом в django проекте:\r\n- delete - удалить файл, котрый находится в file_path, в этом случае text не нужен\r\n- replace - заменить файл, который находится в file_path, на текст который указать в text\r\n- create - создать новый файл\r\ntext - текст файла, если требуется создать растровое изображение то создай пустой соответствующий файл (в имени изображения обязательно должны быть его размеры), а в поле prompt положи максимально подробный запрос к ИИ, по которому я впоследствии сгенерирую картинку\r\nprompt - промт для генерации растровой картинки\r\n\r\nесли один файл ссылается на другой, в нем должны быть относительные пути\r\n\r\nПри создании сайта, не создавай предварительные вложенные директории вида site \\ www \\ user и т.п., т.е. в корне должен уже лежать index.html и от этого строится дальше структура'),
(4,'i_have_page_screenshot','высылаю тебе скриншот созданного сайта и конкретно страницы, куда нужно разместить картинку, используй его, для того, чтобы сохранить визуал и стиль для новых изображений'),
(5,'generate_image_for_site','нужно сгенерировать изображение которое я сохраню по указанному пути\\\r\nты должен учитывать тематику сайта, его цветовую схему для генерации релевантного изображения\r\nесли ты не можешь сгенерировать изображение нужного размера, сгенерируй подходящего возможного размера\r\nне размещай на картинке какие-либо тексты'),
(6,'site_edit_make_plan','пользователь ввел запрос ниже, твоя задача\r\nтакже я тебе присылаю структуру сайта\r\nтвоя задача на данном этапе составить план редактирования сайта, в соответствии с запросом пользователя, в ответе я ожидаю от тебя корректный JSON который я сразу передам в парсер\r\n\r\n[\r\n    {\'engine\': \'\', \'prompt\': \'\',  file_path: \'\'}\r\n    ...\r\n]\r\n\r\nВ зависимости от вариантов engine, prompt и file_path будут переданы в соответствующий обработчик:\r\n- text2img - твой prompt будет передан в ИИ редактирования изображения - file_path\r\n- text2text - твой prompt будет передан в текстовый ИИ. Также если ты укажешь file_path, я передам тело этого файла. При этом я сам дополнительно попрошу ИИ вернуть мне ответ в виде: \r\n>>\r\n[\r\n    {file_operation:\'\', file_path:\'\', \'text\':\'\', \'prompt\': \'\'}\r\n    ...\r\n]\r\n\r\nв котором\r\nfile_path - полный путь к файлу, над которым нужно произвести операцию, все пути относительные от корня, т.е. index.html должен лежать в ./index.html\r\nfile_operation - операция над файлом в django проекте:\r\n- delete - удалить файл, котрый находится в file_path, в этом случае text не нужен\r\n- replace - заменить файл, который находится в file_path, на текст который указать в text\r\n- create - создать новый файл\r\ntext - текст файла, если требуется создать растровое изображение то создай пустой соответствующий файл (в имени изображения обязательно должны быть его размеры), а в поле prompt положи максимально подробный запрос к ИИ, по которому я впоследствии сгенерирую картинку\r\nprompt - промт для генерации растровой картинки\r\n\r\nесли один файл ссылается на другой, в нем должны быть относительные пути\r\n<<\r\nтаким образом, одна твоя задача может сможет изменить сразу несколько файлов\r\n\r\nЕсли пользовательская задача не требует модификации нескольких файлов — ИИ должен менять минимально возможное количество файлов\r\n\r\nКаждая инструкция из твоего плана будет исполняться изолированно друг от друга, таким образом в одном промте ты не можешь ссылаться на другой\r\nЕсли требуется коррекция текста, то необходимо составить план для каждого файла который требует коррекции индивидуально\r\n\r\nОбрати внимание на структуру сайта и убедись что все файлы присутствуют, если нет - сгенерируй их через text2text (и в этом случае file_path - нужно оставить пустым)'),
(7,'site_copy','Максимально сохрани стили, шрифты, разметку, иконки, картинки, выравнивание текста и сам текст с сайта');
/*!40000 ALTER TABLE `core_systemprompts` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `core_paymentgatewaysettings`
--

DROP TABLE IF EXISTS `core_paymentgatewaysettings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `core_paymentgatewaysettings` (
  `id` bigint(20) NOT NULL AUTO_INCREMENT,
  `type` varchar(20) NOT NULL,
  `commission_extra` double NOT NULL,
  `currency` varchar(20) NOT NULL,
  `method` varchar(20) NOT NULL,
  `enabled` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `core_paymentgatewaysettings_type_method_currency_e5651a15_uniq` (`type`,`method`,`currency`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `core_paymentgatewaysettings`
--

LOCK TABLES `core_paymentgatewaysettings` WRITE;
/*!40000 ALTER TABLE `core_paymentgatewaysettings` DISABLE KEYS */;
INSERT INTO `core_paymentgatewaysettings` VALUES
(1,'cryptogator',0.015,'USDT','Tron',1),
(2,'cryptogator',0.015,'USDT','Ethereum',1);
/*!40000 ALTER TABLE `core_paymentgatewaysettings` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*M!100616 SET NOTE_VERBOSITY=@OLD_NOTE_VERBOSITY */;

-- Dump completed on 2025-11-27 19:29:44
