# -*- coding: utf-8 -*-
from hashlib import sha1
import time
import requests
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from utilities.utility import dec_print_exception, dec_print_exception_str, dec_print_exception_bool, dec_print_time
from utilities.log import get_logger
import my_args_ref
sys.path.append(my_args_ref.my_args_dir)
import my_args

logger = get_logger(__name__)


def getshal(s):
    """hash sha1算法加密.

    Parameters
    ----------
    s : str类型
        需要加密的字符串.

    Returns
    -------
    str类型
        加密后的字符串.

    """
    s1 = sha1()
    s1.update(s.encode())
    result = s1.hexdigest()
    return result


def genSignature(t, action=""):
    """生成加密的签名.

    Parameters
    ----------
    t : float类型
        时间戳，单位是ms.
    action : str类型
        action操作类型.

    Returns
    -------
    str类型
        加密后的签名.

    """
    if action == "":
        val = my_args.accessKeySecret + "_" + \
            my_args.accessKeyId + "_" + str(t)
    else:
        val = my_args.accessKeySecret + "_" + \
            my_args.accessKeyId + "_" + str(t) + "_" + action
    signature = getshal(val)
    return signature


@dec_print_exception_str
def login():
    """登录服务器,返回token.

    Returns
    -------
    str类型
        token. For example:
        "784508381da14a7f90ace23955af9accO48"

        异常返回"".

    """
    token = ""

    t = round(time.time()) * 1000
    signature = genSignature(t, "account.accountLogin")
    datas = {"account": my_args.account, "password": my_args.password, "timestamp": str(
        t), "accessKeyId": my_args.accessKeyId, "signature": signature}
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    r = requests.post(my_args.url_login, data=datas, headers=headers)
    logger.debug("login, return: {}".format(r.json()))
    token = r.json()["data"]["token"]

    return token


@dec_print_exception_bool
def send_record_employee(id, dev_id, shot_time):
    """将员工抓拍记录通过http方式上传到服务器.

    Parameters
    ----------
    id : int类型
        员工id.
    dev_id : int类型
        设备id.
    shot_time : int类型
        抓拍时间,单位:秒

    Returns
    -------
    bool类型
        是否成功. For example:
        True

        异常返回False.

    """
    ret = False

    json = {"userId": id, "deviceCode": str(dev_id), "timeUtc": shot_time}
    headers = {'Content-Type': 'application/json;charset=UTF-8'}
    r = requests.post(url=my_args.url_record_employee, json=json, headers=headers)
    logger.debug("send_record_employee, return: {}".format(r.json()))
    ret_code = r.json()["code"]
    if ret_code == 0:
        ret = True
    else:
        ret = False

    return ret


@dec_print_exception
@dec_print_time
def request_employees():
    """从服务器获取有效的员工数据，有效条件:在职.

    Returns
    -------
    dict类型
        员工数据. For example:
        {98: {'name': '张碧晨', 'img_url': 'http://192.168.9.10:8888/zhongzhouBios/employeeimages/59b8d21e3e1d4c74b06c2cb06c6cebb4zowo9.jpeg'},
        95: ...
        }

        异常返回None.

    """
    employees = {}

    token = login()
    if len(token) > 0:
        t = round(time.time()) * 1000
        signature = genSignature(t)
        data = {"leaved": 0, "accessKeyId": my_args.accessKeyId,
                "accessKeySecret": my_args.accessKeySecret, "timestamp": str(t), "signature": signature}
        headers = {
            "Content-Type": "application/x-www-form-urlencoded", "x-sam-Token": token}
        r = requests.post(my_args.url_request_employees,
                          data=data, headers=headers)
        logger.debug("request_employees, return: {}".format(r.json()))
        all_employees = r.json()["data"]
        for item in all_employees:
            id = item["empId"]
            name = item["empName"]
            if "photoFile" in item:
                if item["photoFile"] == "":
                    continue
                else:
                    img_url = item["photoFile"]
            else:
                continue
            employees[id] = {}
            employees[id]["name"] = name
            employees[id]["img_url"] = img_url

    return employees


class DataSender(object):
    """上传数据的类.

    实现上传员工抓拍记录,上传陌生人抓拍记录.

    Attributes
    ----------
    token : str类型.
        登录token.
    """

    def __init__(self):
        """初始化函数"""
        pass

    @dec_print_time
    def upload_record_employee(self, id, dev_id, shot_time):
        """将员工抓拍记录通过http方式上传到服务器.

        Parameters
        ----------
        id : int类型
            员工id.
        dev_id : int类型
            设备id.
        shot_time : int类型
            抓拍时间戳.

        Returns
        -------
        bool类型
            是否成功. For example:
            True

        """
        ret = False

        # 上传数据
        ret = send_record_employee(id, dev_id, shot_time)

        return ret


# test
# 登录
token = login()
print("token:{}".format(token))
if len(token) > 0:
    print("login ok")
else:
    print("login error")


# 发送员工抓拍记录
id = 1000
dev_id = 26
shot_time = round(time.time())
status = send_record_employee(id, dev_id, shot_time)
if status is True:
    print("send_record_employee ok")
else:
    print("send_record_employee error")


# 请求员工数据
employees = request_employees()
if employees is not None:
    print("request_employees ok")
else:
    print("request_employees error")


# test DataSender
dataSender = DataSender()
# 发送员工抓拍记录和图片
dataSender.upload_record_employee(id, dev_id, shot_time)
if status is True:
    print("upload_record_employee ok")
else:
    print("upload_record_employee error")
print("hello")
