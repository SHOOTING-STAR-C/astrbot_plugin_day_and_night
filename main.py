from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register , StarTools
from astrbot.api import logger
from astrbot.api.all import *

from datetime import datetime, timedelta

from data.plugins.astrbot_plugin_day_and_night.database.DayAndNightDataBase import (
    DayAndNightDataBase,
)
from data.plugins.astrbot_plugin_day_and_night.database.DayAndNightDBService import (
    DayAndNightDBService,
)

@register("astrbot_plugin_day_and_night", "SHOOTING-STAR-C", "为 AstrBot 提供的一个简单早安&晚安插件", "v0.5.2")
class DayAndNight(Star):
    def __init__(self, context: Context,config: AstrBotConfig = None):
        super().__init__(context)
        morning_def_sup_prompt = "请祝用户早安然后告知用户的睡眠信息（包含入睡时间、醒来时间、睡眠时常）并关心一下用户的睡眠健康，确保符合人设并考虑上下文，确保对话通顺不突兀"
        night_def_sup_prompt = "请祝用户晚安，并根据入睡时间关心一下用户的睡眠健康，确保符合人设并考虑上下文，确保对话通顺不突兀"
        stats_def_sup_prompt = "告知用户的睡眠信息（包含入睡时间、醒来时间、睡眠时常）并关心一下用户的睡眠健康，确保符合人设并考虑上下文，确保对话通顺不突兀"

        self.bf_data_path = StarTools.get_data_dir("day_and_night_tool_plugin")
        self.db = DayAndNightDataBase(self.bf_data_path)  # 初始化数据库
        self.db_service = DayAndNightDBService(self.db)  # 初始化数据库服务

        self.config = config
        # 防御性配置处理：如果config为None，使用默认值
        if config is None:
            logger.warning("DayAndNight: 未提供配置文件，将使用默认配置")
            self.morning_sup_prompt = morning_def_sup_prompt
            self.night_sup_prompt = night_def_sup_prompt
            self.stats_sup_prompt = stats_def_sup_prompt
        else:
            logger.debug("DayAndNight: 使用用户配置文件")
            self.morning_sup_prompt = config.get("morning_sup_prompt", morning_def_sup_prompt)
            self.night_sup_prompt = config.get("night_sup_prompt", night_def_sup_prompt)
            self.stats_sup_prompt = config.get("stats_sup_prompt", night_def_sup_prompt)

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        await self.db.initialize()  # 添加数据库初始化调用


    @llm_tool(name = 'good_morning' )
    async def good_morning(self,event: AstrMessageEvent):
        """
            用户说早安/早上好等醒来起床举动后调用这个方法获取用户的睡眠情况
        """
        # 获取用户
        user_id = event.get_sender_id()
        # 获取当前时间并计算昨天的日期
        now = datetime.now()
        from datetime import timedelta
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


    @llm_tool(name = 'good_night' )
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


    @llm_tool(name = 'sleep_stats' )
    async def sleep_stats(self, event: AstrMessageEvent):
        """
           用户获取昨天的睡眠情况时使用这个这个函数
        """
        # 获取用户
        user_id = event.get_sender_id()
        # 获取当前时间并计算昨天的日期
        now = datetime.now()
        from datetime import timedelta
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")
        sleep_info = await self.db_service.query_user_sleep_records(user_id, yesterday)
        if sleep_info and sleep_info['wake_time']:
            stats_prompt = f"用户{user_id}向你询问他昨日的睡眠情况，昨晚他{sleep_info['sleep_time']}入睡，今天{sleep_info['wake_time']}醒来，{self.stats_sup_prompt}"
            logger.debug(stats_prompt)
            return stats_prompt
        else:
            stats_prompt = f"用户{user_id}向你询问他昨天的睡眠情况，但是因为他昨晚没有说晚安或今天早上没有早安导致没有记录，结合人设让用户及时对你说早安晚安，可以考虑上下文，确保对话通顺不突兀"
            return stats_prompt


    @llm_tool(name='modify_sleep_time_fuzzy')
    async def modify_sleep_time_fuzzy(self, event: AstrMessageEvent,statis_date:str, sleep_str: str, wake_str: str):
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
        Returns:
            str: 修改结果的提示信息。
        """
        user_id = event.get_sender_id()

        # 判断是修改入睡时间还是醒来时间
        if sleep_str:
            line = await self.db_service.update_custom_sleep_time(user_id, statis_date, sleep_str)
            if line > 0:
                return f"已将{user_id}的入睡时间修改为{sleep_str}"
        if wake_str:
            line = await self.db_service.update_custom_wake_time(user_id, statis_date, wake_str)
            if line > 0:
                return f"已将{user_id}的醒来时间修改为{wake_str}"

        return "修改失败，请确认输入格式是否正确。"


    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
