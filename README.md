## 一、项目介绍
基于Python的SteamGifts机器人，用于自动参与SteamGifts网站的赠送。
## 二、功能
1. 自动抓取SteamGifts网站的赠送列表。
2. 自动抓取Steam游戏评价信息。
3. 将赠送按照游戏评价排序。
4. 自动参与高评价游戏的赠送，如果点数不足，自动退出低评价游戏的赠送获取点数。
## 三、运行方法
1. 安装Python，并配置环境变量，可参考[一文教你如何在Windows下安装 Python 环境 - 知乎](https://zhuanlan.zhihu.com/p/1969557833444992216)
2. 在项目/resources/config.yml中配置PHPSESSID，或者在运行过程中按照提示输入PHPSESSID。
3. 双击项目根目录下的SteamGiftsBot.bat文件即可运行。
