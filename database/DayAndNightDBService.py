from typing import Optional, Dict

from data.plugins.astrbot_plugin_day_and_night.database.DayAndNightDataBase import (
    DayAndNightDataBase,
)

class DayAndNightDBService:
    def __init__(self, db: DayAndNightDataBase):
        self.db = db

    async def query_user_sleep_records(self, user_id: str,status_date : str) -> Optional[Dict]:
        """查询用户昨天睡眠信息"""
        return await self.db.query(
            "SELECT * FROM user_sleep_records WHERE user_id = ? and status_date = ?",
            (user_id,status_date),
            fetch_all=False,
        )
    async def insert_user_sleep_records(self, user_id: str,status_date : str) -> int:
        """记录&更新用户入睡时间"""
        return await self.db.exec_sql(
            """
            INSERT INTO user_sleep_records (user_id, sleep_time, status_date)
            VALUES (?, datetime('now', 'localtime'), ?)
            ON CONFLICT(user_id,status_date) DO UPDATE SET sleep_time = excluded.sleep_time
            """,
            (user_id, status_date),
        )
    async def update_wake_time(self, user_id: str, status_date : str) -> int:
        """记录用户醒来时间"""
        return await self.db.exec_sql(
            """
            UPDATE user_sleep_records
            SET wake_time = datetime('now', 'localtime')
            where user_id = ?
              and status_date = ?
            """,
            (user_id, status_date))