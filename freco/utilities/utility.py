# -*- coding: utf-8 -*-
import functools
import time
import traceback
import sys
import os
sys.path.append(os.path.dirname(__file__))
from log import get_logger

logger = get_logger(__name__)


def dec_print_time(func):
    """打印时间的装饰器函数.

    Parameters
    ----------
    func : 函数类型
        需要打印时间的函数.

    Returns
    -------
    func返回类型
        func返回内容.

    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        now = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        logger.info("start {}, at {}".format(func.__name__, now))
        tStart = time.time()
        result = func(*args, **kwargs)
        tEnd = time.time()
        logger.info("finish {}, cost={} s".format(func.__name__, str(tEnd - tStart)))
        return result
    return wrapper


def dec_print_exception(func):
    """打印异常的装饰器函数.

    Parameters
    ----------
    func : 函数类型
        需要打印异常的函数.

    Returns
    -------
    func返回类型
        func返回内容.

        异常返回None

    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except Exception:
            logger.error(traceback.format_exc())
            return None
    return wrapper


def dec_print_exception_str(func):
    """打印异常的装饰器函数(针对func返回内容是字符串类型).

    Parameters
    ----------
    func : 函数类型
        需要打印异常的函数.

    Returns
    -------
    func返回类型
        func返回内容.

        异常返回空字符串""

    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except Exception:
            logger.error(traceback.format_exc())
            return ""
    return wrapper


def dec_print_exception_bool(func):
    """打印异常的装饰器函数(针对func返回内容是bool类型).

    Parameters
    ----------
    func : 函数类型
        需要打印异常的函数.

    Returns
    -------
    func返回类型
        func返回内容.

        异常返回False

    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            result = func(*args, **kwargs)
            return result
        except Exception:
            logger.error(traceback.format_exc())
            return False
    return wrapper


# # test
# # @dec_print_exception
# # @dec_print_exception_str
# @dec_print_exception_bool
# def print_exception_test():
#     a[1][2] = 3
#     print(a)
#
#
# @dec_print_time
# def print_time_test():
#     a = 3
#     print(a)
#
#
# print_exception_test()
# print_time_test()
# print("hello world")
