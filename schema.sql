-- 粉丝寄语表(在 hanrui 数据库中)
-- 说明: 运行 server.py 时会自动执行此建表语句; 此文件仅供手动执行或查看
CREATE TABLE IF NOT EXISTS fan_messages (
  id INT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY COMMENT '寄语ID',
  nickname VARCHAR(32) NOT NULL DEFAULT '神秘粉丝' COMMENT '粉丝昵称',
  content VARCHAR(200) NOT NULL COMMENT '寄语内容',
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='粉丝生日寄语';

-- 许愿计数表(单行计数器, id 固定为 1, 所有访客共享总数)
CREATE TABLE IF NOT EXISTS wish_stats (
  id TINYINT UNSIGNED NOT NULL PRIMARY KEY COMMENT '固定为1',
  wish_count INT UNSIGNED NOT NULL DEFAULT 0 COMMENT '许愿成功总次数'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='许愿计数';

INSERT IGNORE INTO wish_stats (id, wish_count) VALUES (1, 0);
