# -*- coding: utf-8 -*-

import logging
import logging.config
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import my_args_ref
sys.path.append(my_args_ref.my_args_dir)
import my_args

"""
format参数中可能用到的格式化串:
    1>.%(name)s
         Logger的名字
    2>.%(levelno)s
        数字形式的日志级别
    3>.%(levelname)s
        文本形式的日志级别
    4>.%(pathname)s
        调用日志输出函数的模块的完整路径名，可能没有
    5>.%(filename)s
        调用日志输出函数的模块的文件名
    6>.%(module)s
        调用日志输出函数的模块名
    7>.%(funcName)s
        调用日志输出函数的函数名
    8>.%(lineno)d
        调用日志输出函数的语句所在的代码行
    9>.%(created)f
        当前时间，用UNIX标准的表示时间的浮 点数表示
    10>.%(relativeCreated)d
        输出日志信息时的，自Logger创建以 来的毫秒数
    11>.%(asctime)s
        字符串形式的当前时间。默认格式是 “2003-07-08 16:49:45,896”。逗号后面的是毫秒
    12>.%(thread)d
        线程ID。可能没有
    13>.%(threadName)s
        线程名。可能没有
    14>.%(process)d
        进程ID。可能没有
    15>.%(message)s
        用户输出的消息
"""


# logging.debug("debug message")  # 告警级别最低，只有在诊断问题时才有兴趣的详细信息。
# logging.info("info message")  # 告警级别比debug要高，确认事情按预期进行。
# logging.warning("warning message")  # 告警级别比info要高，该模式是默认的告警级别！预示着一些意想不到的事情发生，或在不久的将来出现一些问题（例如“磁盘空间低”）。该软件仍在正常工作。
# logging.error("error message")  # 告警级别要比warning要高，由于一个更严重的问题，该软件还不能执行某些功能。
# logging.critical("critical message")  # 告警级别要比error还要高，严重错误，表明程序本身可能无法继续运行。

def get_logger(name):
    logger_obj = logging.getLogger(name)  # 创建一个logger对象，它提供了应用程序可以直接使用的接口，其类型为“<class 'logging.RootLogger'>”；
    logger_obj.setLevel(logging.DEBUG)  # 定义默认级别

    os.makedirs(os.path.dirname(my_args.log_path), exist_ok=True)  # 自动创建目录
    fh = logging.handlers.RotatingFileHandler(my_args.log_path, maxBytes=5 * 1024 * 1024, backupCount=10, encoding='utf-8')  # 创建一个循环覆盖文件输出流；
    fh.setLevel(logging.DEBUG)  # 定义文件输出流的告警级别；

    ch = logging.StreamHandler()  # 创建一个屏幕输出流；
    ch.setLevel(logging.INFO)  # 定义屏幕输出流的告警级别；

    formater = logging.Formatter('%(asctime)s|%(module)s|%(lineno)s: %(message)s')  # 自定义日志的输出格式，这个格式可以被文件输出流和屏幕输出流调用；
    fh.setFormatter(formater)  # 添加格式花输出，即调用我们上面所定义的格式，换句话说就是给这个handler选择一个格式；
    ch.setFormatter(formater)

    logger_obj.addHandler(fh)  # logger对象可以创建多个文件输出流（fh）和屏幕输出流（ch）哟
    logger_obj.addHandler(ch)

    return logger_obj  # 将我们创建好的logger对象返回


# test
# logger = get_logger(__name__)
# logger.debug("debug")
# logger.info("info")
# logger.error("error")
# logger.warning("warning")
# logger.debug("debug")
# logger.critical("critical")
