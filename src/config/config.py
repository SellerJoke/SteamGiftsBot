import ctypes
import sys

APP_NAME = "SteamGiftsBot"

# 禁用命令行的快速编辑（QuickEdit）模式和插入（Insert）模式，以免鼠标选中控制台内容导致应用暂停
if sys.platform == "win32":
    kernel32 = ctypes.windll.kernel32
    # noinspection PyUnresolvedReferences
    handle = kernel32.GetStdHandle(-10)  # STD_INPUT_HANDLE
    mode = ctypes.c_ulong()
    # noinspection PyUnresolvedReferences
    kernel32.GetConsoleMode(handle, ctypes.byref(mode))
    # 清除 ENABLE_QUICK_EDIT_MODE (0x0040) 和 ENABLE_INSERT_MODE (0x0020)
    # noinspection PyUnresolvedReferences
    kernel32.SetConsoleMode(handle, mode.value & ~0x0040 & ~0x0020)