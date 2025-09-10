from typing import Tuple, Optional, Union, Dict, List
from pathlib import Path
from astrbot.api.star import StarTools
# from astrbot.api.all import *
from astrbot.api import logger

import aiosqlite


class SleepTrackerDataBase:
    st_db_name = "sleep_tracker.db"

    def __init__(self, st_db_path: str = None):
        super().__init__()
        if st_db_path is None:
            self.st_db_path = (
                StarTools.get_data_dir("sleep_tracker_tool_plugin") / self.st_db_name
            )
        else:
            self.st_db_path = st_db_path / self.st_db_name
        self._conn = None

    async def _init_db(self, conn: aiosqlite.Connection):
        """使用给定连接初始化数据库"""
        # 使用 pathlib 构建 SQL 文件路径
        sql_path = Path(__file__).parent / "sql" / "sleep_tracker_tool_plugin_init.sql"

        logger.debug(f"尝试从路径加载初始化SQL: {sql_path}")

        if not sql_path.exists():
            logger.error(f"初始化SQL文件不存在: {sql_path}")
            raise FileNotFoundError(f"初始化SQL文件不存在: {sql_path}")

        try:
            with open(sql_path, "r", encoding="utf-8") as f:
                sql_script = f.read()

            logger.debug(f"开始执行数据库初始化脚本，文件大小: {len(sql_script)} 字节")
            await conn.executescript(sql_script)
            await conn.commit()
            logger.debug("数据库表结构初始化成功")

        except aiosqlite.Error as e:
            logger.exception(f"数据库初始化失败: {e}")
            raise RuntimeError(f"数据库初始化失败: {e}") from e
        except Exception as e:
            logger.exception("未知错误发生在数据库初始化过程中")
            raise

    async def initialize(self):
        """异步初始化数据库"""
        logger.debug("开始初始化早安&晚安工具数据库...")
        # 先获取主连接
        self._conn = await self._get_conn()
        logger.debug(f"数据库连接已建立: {self._conn}")

        # 使用主连接初始化表结构
        await self._init_db(self._conn)
        logger.debug("早安&晚安工具数据库初始化完成")

    async def _get_conn(self) -> aiosqlite.Connection:
        """获取异步数据库连接(复用现有连接或创建新连接)

        Returns:
            aiosqlite.Connection: 数据库连接对象

        Raises:
            RuntimeError: 当连接失败时抛出
        """
        # 检查连接是否存在且有效
        if self._conn:
            try:
                # 执行简单查询验证连接是否有效
                cursor = await self._conn.cursor()
                await cursor.execute("SELECT 1")
                await cursor.close()
                return self._conn
            except aiosqlite.Error:
                # 连接无效，关闭并重新创建
                logger.warning("数据库连接已失效，重新建立连接")
                await self._conn.close()
                self._conn = None

        try:
            conn = await aiosqlite.connect(self.st_db_path)
            conn.text_factory = str
            self._conn = conn
            return conn
        except aiosqlite.Error as e:
            logger.error(f"数据库连接失败: {e}")
            raise RuntimeError(f"无法连接到数据库: {e}")

    async def close(self):
        """关闭数据库连接"""
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def exec_sql(self, sql: str, params: Tuple = None):
        """
        执行SQL(复用现有连接)

        Args:
            sql: 要执行的SQL查询语句
            params: 查询参数，可以是元组或字典
        Returns:
            int: 受影响的行数
        """
        conn = await self._get_conn()
        try:
            cursor = await conn.cursor()
            await cursor.execute(sql, params or ())
            await conn.commit()
            return cursor.rowcount
        except aiosqlite.Error as e:
            await conn.rollback()
            raise e from e

    async def query(
        self,
        sql: str,
        params: Optional[Union[Tuple, Dict]] = None,
        fetch_all: bool = True,
    ) -> Union[List[Dict], Optional[Dict]]:
        """
        执行SQL查询并返回结果(复用现有连接)

        Args:
            sql: 要执行的SQL查询语句
            params: 查询参数，可以是元组或字典
            fetch_all: 是否获取所有结果（False时只返回第一条）

        Returns:
            当 fetch_all=True 时返回 List[Dict]
            当 fetch_all=False 时返回单个 Dict 或 None（无结果时）

        Raises:
            aiosqlite.Error: 数据库操作失败时抛出
        """
        conn = await self._get_conn()
        try:
            conn.row_factory = aiosqlite.Row  # 使结果可转为字典
            cursor = await conn.cursor()

            # 根据参数类型选择执行方式
            if isinstance(params, dict):
                await cursor.execute(sql, params)
            else:
                await cursor.execute(sql, params or ())

            if fetch_all:
                return [dict(row) for row in await cursor.fetchall()]
            else:
                if result := await cursor.fetchone():
                    return dict(result)
                return None

        except aiosqlite.Error as e:
            logger.error(f"查询失败: {e}\nSQL: {sql}\nParams: {params}")
            raise
