import logging
import time

from src.bot import Bot
from src.config.log import setup_logging
from src.util.shared_objects import CONSOLE

# 应用入口，程序应该从这里开始执行
if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger("src.main")
    with Bot() as bot:
        while True:
            try:
                bot.work()
            except Exception as e:
                logger.exception("发生异常")
                raise e
            logger.info("休眠1小时")
            CONSOLE.log("休眠1小时")
            time.sleep(60 * 60)
