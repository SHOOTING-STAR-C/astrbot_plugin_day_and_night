from astrbot.api.event import AstrMessageEvent
from astrbot.api.star import Context, Star, register , StarTools
from astrbot.api import logger
from astrbot.api.all import *

from datetime import datetime, timedelta
from typing import Optional, Dict


from data.plugins.astrbot_plugin_sleep_tracker.database.SleepTrackerDataBase import (
    SleepTrackerDataBase,
)
from data.plugins.astrbot_plugin_sleep_tracker.database.SleepTrackerDBService import (
    SleepTrackerDBService,
)

@register("astrbot_plugin_sleep_tracker", "SHOOTING-STAR-C", "一个基于 AstrBot 的睡眠记录插件，帮助用户记录和分析睡眠作息情况", "v0.5.7")
class SleepTracker(Star):
    def __init__(self, context: Context,config: AstrBotConfig = None):
        super().__init__(context)
        morning_def_sup_prompt = "请祝用户早安然后告知用户的睡眠信息（包含入睡时间、醒来时间、睡眠时常）并关心一下用户的睡眠健康，确保符合人设并考虑上下文，确保对话通顺不突兀"
        night_def_sup_prompt = "请祝用户晚安，并根据入睡时间关心一下用户的睡眠健康，确保符合人设并考虑上下文，确保对话通顺不突兀"
        stats_def_sup_prompt = "告知用户的睡眠信息（包含入睡时间、醒来时间、睡眠时常）并关心一下用户的睡眠健康，确保符合人设并考虑上下文，确保对话通顺不突兀"

        self.bf_data_path = StarTools.get_data_dir("sleep_tracker_tool_plugin")
        self.db = SleepTrackerDataBase(self.bf_data_path)  # 初始化数据库
        self.db_service = SleepTrackerDBService(self.db)  # 初始化数据库服务

        self.config = config
        # 防御性配置处理：如果config为None，使用默认值
        if config is None:
            logger.warning("SleepTracker: 未提供配置文件，将使用默认配置")
            self.morning_sup_prompt = morning_def_sup_prompt
            self.night_sup_prompt = night_def_sup_prompt
            self.stats_sup_prompt = stats_def_sup_prompt
        else:
            logger.debug("SleepTracker: 使用用户配置文件")
            self.morning_sup_prompt = config.get("morning_sup_prompt", morning_def_sup_prompt)
            self.night_sup_prompt = config.get("night_sup_prompt", night_def_sup_prompt)
            self.stats_sup_prompt = config.get("stats_sup_prompt", night_def_sup_prompt)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        await self.db.initialize()  # 添加数据库初始化调用


    @llm_tool(name = "good_morning" )
    async def good_morning(self,event: AstrMessageEvent):
        """
            用户说早安/早上好等醒来起床举动后调用这个方法获取用户的睡眠情况
        """
        # 获取用户
        user_id = event.get_sender_id()
        # 获取当前时间并计算昨天的日期
        now = datetime.now()
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        line = await self.db_service.update_wake_time(user_id, yesterday)
        sleep_info = await self.db_service.query_user_sleep_records(user_id, yesterday)
        if line > 0 and sleep_info:
            morning_prompt = f"用户{user_id}向你说早安，昨晚他{sleep_info['sleep_time']}入睡，今天{sleep_info['wake_time']}醒来，{self.morning_sup_prompt}"
            logger.debug(morning_prompt)
            return morning_prompt
        else:
            nt_morning_prompt = f"用户{user_id}向你说早安，结合人设祝用户早安，可以考虑上下文，确保对话通顺不突兀"
            return nt_morning_prompt


    @llm_tool(name = "good_night" )
    async def good_night(self, event: AstrMessageEvent):
        """
            用户说晚安或睡觉了或其他入睡举动后使用这个工具记录用户入睡时间
        """
        user_id = event.get_sender_id()
        # 获取当前时间
        now = datetime.now()
        current_hour = now.hour

        # 如果是凌晨0点到6点之间，将日期调整为前一天
        if 0 <= current_hour < 6:
            from datetime import timedelta
            yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            statis_date = yesterday
        else:
            statis_date = now.strftime("%Y-%m-%d")
        line = await self.db_service.insert_user_sleep_records(user_id, statis_date)
        sleep_info = await self.db_service.query_user_sleep_records(user_id, statis_date)
        if line > 0 and sleep_info:
            night_prompt = f"用户{user_id}向你说晚安，今天他{sleep_info['sleep_time']}入睡，{self.night_sup_prompt}"
            logger.debug(night_prompt)
            return night_prompt
        else:
            error_night_prompt = f"用户{user_id}向你说晚安，结合人设祝用户晚安，可以考虑上下文，确保对话通顺不突兀"
            return error_night_prompt


    @llm_tool(name = "sleep_stats" )
    async def sleep_stats(self, event: AstrMessageEvent,statis_date:str = None):
        """
           用户获取昨天的睡眠情况时使用这个这个函数
            Args:
                statis_date(string)，指定查询某天的睡眠情况，没指定就填None
        """
        # 获取用户
        user_id = event.get_sender_id()
        # 获取当前时间并计算昨天的日期
        now = datetime.now()
        from datetime import timedelta
        if not statis_date:
            yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
            statis_date = yesterday
        sleep_info = await self.db_service.query_user_sleep_records(user_id, statis_date)
        if sleep_info and sleep_info["wake_time"]:
            stats_prompt = f"用户{user_id}向你询问他{statis_date}的睡眠情况，{statis_date}他{sleep_info['sleep_time']}入睡，今天{sleep_info['wake_time']}醒来，{self.stats_sup_prompt}"
            logger.debug(stats_prompt)
            return stats_prompt
        else:
            stats_prompt = f"用户{user_id}向你询问他{statis_date}的睡眠情况，但是因为他{statis_date}没有说晚安或今天早上没有早安导致没有记录，结合人设让用户及时对你说早安晚安，可以考虑上下文，确保对话通顺不突兀"
            return stats_prompt


    @llm_tool(name="modify_sleep_time_fuzzy")
    async def modify_sleep_time_fuzzy(self, event: AstrMessageEvent, statis_date:str, sleep_str: str = None, wake_str: str = None,modify_user_id:str=None) -> str:
        """
        用户修改入睡或醒来时间
        示例：
        - 我是早上八点醒的
        - 我是昨晚上八点睡着的
        - 修改我的入睡时间为今早8点
        - 修改我的醒来时间为昨天晚上10点
        Args:
            statis_date(string): 修改哪天,没有就填None
            sleep_str(string): 用户提供的入睡时间(%Y-%m-%d %H:%M:%S),没有就填None
            wake_str(string): 用户提供的醒来时间(%Y-%m-%d %H:%M:%S),没有就填None
            modify_user_id(string): 用户修改其他人的睡眠时间时候填写被修改用户的id，没有就填None
        Returns:
            str: 修改结果的提示信息。
        """
        if modify_user_id:
            if event.is_admin():
                user_id = modify_user_id
            else:
                return "仅管理员可修改其他人的睡眠时间，普通用户只能修改自己的睡眠时间"
        else:
            user_id = event.get_sender_id()


        # 判断是修改入睡时间还是醒来时间
        results = []
        if sleep_str:
            line = await self.db_service.update_custom_sleep_time(user_id, statis_date, sleep_str)
            if line > 0:
                results.append(f"已将{user_id}的入睡时间修改为{sleep_str}")
        if wake_str:
            line = await self.db_service.update_custom_wake_time(user_id, statis_date, wake_str)
            if line > 0:
                results.append(f"已将{user_id}的醒来时间修改为{wake_str}")
        if results:
            return "\n".join(results)

        return "修改失败，请确认输入格式是否正确。"


    @llm_tool(name="statis_sleep_data")
    async def statis_sleep_data(self, event: AstrMessageEvent, start_date: str, end_date: str) -> Optional[Dict]:
        """
        统计用户某个时间段的睡眠数据，尽量自己填参数不要询问用户
        - 查询我最近7天的睡眠情况
        - 查询一下我这周的睡眠情况
        - 帮我统计一下我这个月的睡眠数据
        - 查询我从2024-10-01到2024-10-07的睡眠情况
        - 帮我统计一下我从2023-09-25到2023-10-01的睡眠数据
        - 帮我统计一下我最近30天的睡眠数据
        Args:
            start_date (string): 统计开始日期，格式为 "YYYY-MM-DD"
            end_date (string): 统计结束日期，格式为 "YYYY-MM-DD"
        """
        # 获取用户
        user_id = event.get_sender_id()
        sleep_data = await self.db_service.statis_sleep_data(user_id, start_date, end_date)

        result_lines = []
        logger.debug(sleep_data)
        if sleep_data:
            for sleep_record in sleep_data:
                result_lines.append(f"日期: {sleep_record['status_date']}, 入睡: {sleep_record['sleep_time']}, 醒来: {sleep_record['wake_time']}, 时长: {sleep_record['sleep_duration_minutes']}")
            # 将所有行拼接成一个完整的字符串
            result = "\n".join(result_lines)
            return f"用户{user_id}在{start_date}到{end_date}期间的睡眠记录:\n{result}"
        else:
            return f"用户{user_id}在{start_date}到{end_date}期间没有睡眠记录。"



    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
