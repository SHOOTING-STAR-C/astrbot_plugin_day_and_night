from typing import Optional, Dict,List

from data.plugins.astrbot_plugin_day_and_night.database.SleepTrackerDataBase import (
    SleepTrackerDataBase,
)

class SleepTrackerDBService:
    def __init__(self, db: SleepTrackerDataBase):
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
    async def update_custom_sleep_time(self, user_id: str, status_date: str, sleep_time: str) -> int:
        """修改用户的入睡时间，如果记录不存在则插入一条新记录"""
        return await self.db.exec_sql(
            """
            INSERT INTO user_sleep_records (user_id, sleep_time, status_date)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, status_date) DO UPDATE SET sleep_time = excluded.sleep_time
            """,
            (user_id, sleep_time, status_date),
        )

    async def update_custom_wake_time(self, user_id: str, status_date: str, wake_time: str) -> int:
        """修改用户的醒来时间，如果记录不存在则插入一条新记录"""
        return await self.db.exec_sql(
            """
            INSERT INTO user_sleep_records (user_id, wake_time, status_date)
            VALUES (?, ?, ?)
            ON CONFLICT(user_id, status_date) DO UPDATE SET wake_time = excluded.wake_time
            """,
            (user_id, wake_time, status_date))

    async def statis_sleep_data(self, user_id: str, start_date: str,end_date:str) -> Optional[List[Dict]]:
        """统计用户时间段内的睡眠数据"""
        return await self.db.query(
            """
            SELECT
                status_date AS status_date,
                sleep_time as sleep_time,
                wake_time as wake_time,
                CAST((JULIANDAY(wake_time) - JULIANDAY(sleep_time)) * 24 * 60 AS INTEGER) AS sleep_duration_minutes
            FROM user_sleep_records
            WHERE user_id = ?
              AND sleep_time IS NOT NULL
              AND wake_time IS NOT NULL
              AND status_date between ? and ?
            """,
            (user_id, start_date,end_date),
            fetch_all=True,
        )
