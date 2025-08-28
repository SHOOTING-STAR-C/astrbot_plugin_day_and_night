CREATE TABLE IF NOT EXISTS user_sleep_records
(
    user_id INTEGER NOT NULL,              -- 用户ID
    sleep_time DATETIME NOT NULL,          -- 入睡时间
    wake_time DATETIME,                    -- 醒来时间
    status_date DATE NOT NULL,             -- 统计日期（联合主键部分）

    -- 设置联合主键
    PRIMARY KEY (user_id, status_date)
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_user_status_date ON user_sleep_records(user_id, status_date);