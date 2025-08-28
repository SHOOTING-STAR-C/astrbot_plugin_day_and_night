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
    def __init__(self, context: Context):
        super().__init__(context)
        self.bf_data_path = StarTools.get_data_dir("day_and_night_tool_plugin")
        self.db = DayAndNightDataBase(self.bf_data_path)  # 初始化数据库
        self.db_service = DayAndNightDBService(self.db)  # 初始化数据库服务

    async def initialize(self):
        """可选择实现异步的插件初始化方法，当实例化该插件类之后会自动调用该方法。"""
        await self.db.initialize()  # 添加数据库初始化调用


    @llm_tool(name = 'good_morning' )
    async def good_morning(self,event: AstrMessageEvent):
        """
            用户说早安后调用这个方法

            Args：:
                - user_id: 用户的id或者名字
        """
        # 获取用户
        user_id = event.get_sender_id()
        # 获取当前时间并计算昨天的日期
        now = datetime.now()
        from datetime import timedelta
        yesterday = (now - timedelta(days=1)).strftime("%Y-%m-%d")

        curr_cid = await self.context.conversation_manager.get_curr_conversation_id(event.unified_msg_origin) # 当前用户所处对话的对话id，是一个 uuid。
        conversation = None # 对话对象
        context = [] # 上下文列表
        if curr_cid:
            conversation = await self.context.conversation_manager.get_conversation(event.unified_msg_origin, curr_cid)
            context = json.loads(conversation.history)
        line = await self.db_service.update_wake_time(user_id, yesterday)
        sleep_info = await self.db_service.query_user_sleep_records(user_id, yesterday)
        if line > 0 and sleep_info:
            morning_prompt = f"用户{user_id}向你说早安，昨晚他{sleep_info['sleep_time']}入睡，今天{sleep_info['wake_time']}醒来，请祝用户早安并评价一下他的睡眠情况"
            logger.debug(morning_prompt)
            return morning_prompt
        else:
            nt_morning_prompt = f"用户{user_id}向你说早安，请祝用户早安"
            return nt_morning_prompt


    @llm_tool(name = 'good_night' )
    async def good_night(self, event: AstrMessageEvent):
        """
            用户说晚安后使用这个工具记录用户入睡时间
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
        curr_cid = await self.context.conversation_manager.get_curr_conversation_id(event.unified_msg_origin) # 当前用户所处对话的对话id，是一个 uuid。
        conversation = None # 对话对象
        context = [] # 上下文列表
        if curr_cid:
            conversation = await self.context.conversation_manager.get_conversation(event.unified_msg_origin, curr_cid)
            context = json.loads(conversation.history)
        line = await self.db_service.insert_user_sleep_records(user_id, statis_date)
        sleep_info = await self.db_service.query_user_sleep_records(user_id, statis_date)
        logger.info(sleep_info)
        if line > 0 and sleep_info:
            night_prompt = f"用户{user_id}向你说晚安，今天他{sleep_info['sleep_time']}入睡，请祝用户晚安并评价一下他的睡眠情况"
            logger.debug(night_prompt)
            return night_prompt
        else:
            error_night_prompt = f"用户{user_id}向你说晚安，请祝用户晚安"



    async def terminate(self):
        """可选择实现异步的插件销毁方法，当插件被卸载/停用时会调用。"""
