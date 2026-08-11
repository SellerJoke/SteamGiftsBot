import logging
import random
import time

from src.bot import Bot
from src.config.log import setup_logging
from src.util.shared_objects import CONSOLE

# 应用入口，程序应该从这里开始执行
if __name__ == "__main__":
    setup_logging()
    logger = logging.getLogger("src.main")
    SLEEP_INTERVAL: int = 50	# 每轮休眠的分钟数
    with Bot() as bot:
        while True:
            try:
                bot.work()
            except Exception as e:
                logger.exception("发生异常")
                raise e
            logger.info(f"休眠约{SLEEP_INTERVAL}分钟")
            CONSOLE.log(f"休眠约{SLEEP_INTERVAL}分钟", end="\n\n")
            # 随机休眠40分钟到60分钟
            time.sleep(SLEEP_INTERVAL * 60 * (1 + random.uniform(-0.2, 0.2)))
