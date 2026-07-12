import logging
import time

from src.bot import Bot
from src.config.log import setup_logging

# 应用入口，程序应该从这里开始执行
if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger("src.main")
    with Bot() as bot:
        while True:
            bot.work()
            logger.info("休眠1小时")
            time.sleep(60 * 60)
