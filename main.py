from astrbot.api.event import filter, AstrMessageEvent, MessageEventResult
from astrbot.api.star import Context, Star, register , StarTools
from astrbot.api import logger
from astrbot.api.all import *

from datetime import datetime

from data.plugins.astrbot_plugin_day_and_night.database.DayAndNightDataBase import (
    DayAndNightDataBase,
)
from data.plugins.astrbot_plugin_day_and_night.database.DayAndNightDBService import (
    DayAndNightDBService,
)

@register("astrbot_plugin_day_and_night", "SHOOTING-STAR-C", "为 AstrBot 提供的一个简单早安&晚安插件", "0.0.1")
class DayAndNight(Star):
    def __init__(self, context: Context,config: AstrBotConfig = None):
        super().__init__(context)
        morning_def_sup_prompt = "请祝用户早安然后告知用户的睡眠信息（包含入睡时间、醒来时间、睡眠时常）并关心一下用户的睡眠健康，确保符合人设并考虑上下文，确保对话通顺不突兀"
        night_def_sup_prompt = "请祝用户晚安，并根据入睡时间关心一下用户的睡眠健康，确保符合人设并考虑上下文，确保对话通顺不突兀"

        self.bf_data_path = StarTools.get_data_dir("day_and_night_tool_plugin")
        self.db = DayAndNightDataBase(self.bf_data_path)  # 初始化数据库
        self.db_service = DayAndNightDBService(self.db)  # 初始化数据库服务

        self.config = config
        # 防御性配置处理：如果config为None，使用默认值
        if config is None:
            logger.warning("DayAndNight: 未提供配置文件，将使用默认配置")
            self.morning_sup_prompt = morning_def_sup_prompt
            self.night_sup_prompt = night_def_sup_prompt
        else:
            logger.debug("DayAndNight: 使用用户配置文件")
            self.morning_sup_prompt = config.get("morning_sup_prompt", morning_def_sup_prompt)
            self.night_sup_prompt = config.get("night_sup_prompt", night_def_sup_prompt)

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



    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
