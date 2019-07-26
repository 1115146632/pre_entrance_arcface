# -*- coding: utf-8 -*-
import time
import sqlite3
import numpy as np
import io
import os
from threading import Thread, Lock
import copy
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from utilities.utility import dec_print_exception, dec_print_time
from utilities.log import get_logger

logger = get_logger(__name__)


class DBTool_sqlite3(Thread):
    """sqlite3操作类.

    实现sqlite3数据库的增删改查.

    Attributes
    ----------
        conn : connect类型
            sqlite3数据库连接对象.
        c : cursor类型
            cursor对象.
        task_list: list类型
            操作任务队列.
        task_lock: Lock类型
            操作任务线程锁.
    """

    class DBTask(object):
        """sqlite3数据库操作任务的类型.

        Attributes
        ----------
            execute_fn : 函数类型
                操作函数.
            after_execute_fn : 函数类型
                操作之后的函数.
            sql : str类型
                sql语句.
            result : 字典
                执行结果.
        """

        def __init__(self, sql, execute_fn, after_execute_fn=None):
            """初始化函数."""
            self.execute_fn = execute_fn
            self.after_execute_fn = after_execute_fn
            self.sql = sql
            self.result = None

        def __del__(self):
            """销毁函数."""
            pass

    def __init__(self, db_name):
        """初始化函数."""
        super().__init__()

        # Converts np.array to TEXT when inserting
        sqlite3.register_adapter(np.ndarray, self.adapt_array)

        # Converts TEXT to np.array when selecting
        sqlite3.register_converter("array", self.convert_array)

        self.conn = sqlite3.connect(
            db_name, detect_types=sqlite3.PARSE_DECLTYPES, check_same_thread=False)
        self.c = self.conn.cursor()

        logger.debug("Opened database successfully")

        self.task_list = []
        self.task_lock = Lock()

    def __del__(self):
        """销毁函数."""
        self.c.close()
        self.conn.close()

        logger.debug("Closed database successfully")

    def adapt_array(self, arr):
        """适配器函数, 将np array类型转为二进制类型"""
        out = io.BytesIO()
        np.save(out, arr)
        out.seek(0)
        return sqlite3.Binary(out.read())

    def convert_array(self, text):
        """转换器函数，将二进制类型转为np array类型."""
        out = io.BytesIO(text)
        out.seek(0)
        return np.load(out, allow_pickle=True)

    def _execute(self, sql):
        """执行sql语句."""
        result = {}
        if len(sql) == 1:
            result = self.c.execute(sql[0])
        elif len(sql) == 2:
            result = self.c.execute(sql[0], sql[1])
        else:
            logger.error("_execute error: sql:{}".format(sql))
        return result

    def _execute_with_commit(self, sql):
        """执行sql语句并提交."""
        if len(sql) == 1:
            self.c.execute(sql[0])
        elif len(sql) == 2:
            self.c.execute(sql[0], sql[1])
            self.conn.commit()
        else:
            logger.error("_execute_with_commit error: sql:{}".format(sql))
        return True

    def _executeSelect(self, sql):
        """执行查询语句."""
        result = self._execute(sql)
        logger.debug("selected successfully")
        return result

    def _executeInsert(self, sql):
        """执行插入语句."""
        self._execute_with_commit(sql)
        logger.debug("inserted successfully")
        return True

    def _executeUpdate(self, sql):
        """执行更新语句."""
        self._execute_with_commit(sql)
        logger.debug("updated successfully")
        return True

    def _executeDelete(self, sql):
        """执行删除语句."""
        self._execute_with_commit(sql)
        logger.debug("deleted successfully")
        return True

    def pre_executeSelect(self, sql, after_execute_fn):
        """提交执行查询语句的操作任务."""
        task = DBTool_sqlite3.DBTask(
            sql, self._executeSelect, after_execute_fn)
        self.task_lock.acquire()
        self.task_list.append(task)
        self.task_lock.release()
        return True

    def pre_executeInsert(self, sql):
        """提交执行插入语句的操作任务."""
        task = DBTool_sqlite3.DBTask(sql, self._executeInsert)
        self.task_lock.acquire()
        self.task_list.append(task)
        self.task_lock.release()
        return True

    def pre_executeUpdate(self, sql):
        """提交执行更新语句的操作任务."""
        task = DBTool_sqlite3.DBTask(sql, self._executeUpdate)
        self.task_lock.acquire()
        self.task_list.append(task)
        self.task_lock.release()
        return True

    def pre_executeDelete(self, sql):
        """提交执行删除语句的操作任务."""
        task = DBTool_sqlite3.DBTask(sql, self._executeDelete)
        self.task_lock.acquire()
        self.task_list.append(task)
        self.task_lock.release()
        return True

    def run(self):
        """执行操作任务的线程."""
        while(True):
            self.task_lock.acquire()
            task_list = copy.copy(self.task_list)
            self.task_list.clear()
            self.task_lock.release()
            if len(task_list) == 0:
                time.sleep(1)
            else:
                for task in task_list:
                    result = task.execute_fn(task.sql)
                    if task.after_execute_fn is not None:
                        task.after_execute_fn(result)


class DataManager(object):
    """管理数据的类.

    实现数据的增删改查，可能涉及内存数据，数据库数据等

    Attributes
    ----------
        data_lock : Lock类型
            数据线程锁.
        employees : dict类型
            员工数据.
        vistors : dict类型
            访客数据.
    """

    def __init__(self, args):
        """初始化函数."""
        self.data_lock = Lock()
        self.employees = {}
        self.vistors = {}
        self.db_op = DBTool_sqlite3(args.local_db_path)
        self.db_op.start()
        self.select_employees(args.local_db_path)
        self.select_vistors(args.local_db_path)

    def __del__(self):
        """销毁函数."""
        pass

    @dec_print_exception
    def add_employee(self, id, name, img_url, feature):
        """内存中, 本地数据库(异步方式)添加员工数据.

        Parameters
        ----------
            id : int类型
                员工id.
            name : str类型
                员工名字.
            img_url : str类型
                图片url.
            feature : numpy.array类型
                特征向量.

        """
        logger.info("add_employee id: {} name: {}".format(id, name))
        # 内存操作
        self.data_lock.acquire()
        self.employees[id] = {}
        self.employees[id]["name"] = name
        self.employees[id]["img_url"] = img_url
        feature_list = [feature]
        self.employees[id]["feature_list"] = feature_list
        self.data_lock.release()
        # test dec_print_exception
        # self.employees[id]["feature"][222] = {1123: 22}

        # db操作
        # test dec_print_exception
        # sql = "INSERT OR REPLACE INTO EMPLOYEES (ID, NAME, URL, 22, FEATURE) VALUES (?, ?, ?, ?)", (id, name, img_url, feature,)
        sql = "INSERT OR REPLACE INTO EMPLOYEES (ID, NAME, URL, FEATURE) VALUES (?, ?, ?, ?)", (
            id, name, img_url, feature,)
        self.db_op.pre_executeInsert(sql)

    @dec_print_exception
    def update_employee(self, id, name, img_url, feature):
        """内存, 本地数据库(异步方式)修改员工数据.

        Parameters
        ----------
            id : int类型
                员工id.
            name : str类型
                员工名字.
            img_url : str类型
                图片url.
            feature : numpy.array类型
                特征向量.

        """
        self.data_lock.acquire()
        if id in self.employees:
            # 内存操作
            self.employees[id]["name"] = name
            self.employees[id]["img_url"] = img_url
            self.employees[id]["feature_list"][0] = feature
            self.data_lock.release()

            # db操作
            # sql = "UPDATE EMPLOYEES SET NAME = ?, URL = ?, FEATURE = ? WHERE ID = ?", (
            # "刘新杰111", "http://192.168.9.10:10000/isyscoreOffice/images/1905096BG75369YW.jpg", np.array([1]), 1)
            sql = "UPDATE EMPLOYEES SET NAME = ?, URL = ?, FEATURE = ? WHERE ID = ?", (
                name, img_url, feature, id,)
            self.db_op.pre_executeUpdate(sql)
        else:
            # 增加员工数据
            # 内存操作
            self.employees[id] = {}
            self.employees[id]["name"] = name
            self.employees[id]["img_url"] = img_url
            feature_list = [feature]
            self.employees[id]["feature_list"] = feature_list
            self.data_lock.release()

            # db操作
            sql = "INSERT OR REPLACE INTO EMPLOYEES (ID, NAME, URL, FEATURE) VALUES (?, ?, ?, ?)", (
                id, name, img_url, feature,)
            self.db_op.pre_executeInsert(sql)

    @dec_print_exception
    def update_employee_feature2(self, id, feature2):
        """内存, 本地数据库(异步方式)修改员工数据的第二特征向量.

        预留.

        Parameters
        ----------
            id : int类型
                员工id.
            feature2 : numpy.array类型
                第二特征向量.

        """
        self.data_lock.acquire()
        # 内存操作
        if len(self.employees[id]["feature_list"]) >= 2:
            self.employees[id]["feature_list"][1] = feature2
        elif len(self.employees[id]["feature_list"]) == 1:
            self.employees[id]["feature_list"].append(feature2)
        else:
            logger.error("update_employee_feature2 error, feature_list is empty, id:{}".format(id))
        self.data_lock.release()
        # db操作
        sql = "UPDATE EMPLOYEES SET FEATURE2 = ? WHERE ID = ?", (feature2, id,)
        self.db_op.pre_executeUpdate(sql)

    @dec_print_exception
    def del_employee(self, id):
        """删除员工数据.

        内存, 本地数据库(异步方式)删除员工数据.

        Parameters
        ----------
            id : int类型
                员工id.

        """
        self.data_lock.acquire()
        # 内存操作
        if id in self.employees:
            self.employees.pop(id)
        self.data_lock.release()
        # db操作
        sql = "DELETE FROM EMPLOYEES WHERE ID = ?", (id,)
        self.db_op.pre_executeDelete(sql)

    @dec_print_exception
    def select_employees_asyn(self):
        """本地数据库(异步方式)查询员工数据,并将员工数据更新到内存中.

        预留

        """
        # db操作
        sql = "SELECT * FROM EMPLOYEES",

        def after_execute_fn(result):
            employees = {}
            for row in result:
                id = row[0]
                name = row[1]
                logger.info("employee id: {} name: {}".format(id, name))
                img_url = row[2]
                feature_list = []
                for i in range(3, len(row)):
                    if row[i] is not None:
                        feature_list.append(row[i])
                employees[id] = {}
                employees[id]["name"] = name
                employees[id]["img_url"] = img_url
                employees[id]["feature_list"] = feature_list
            # 内存操作
            self.data_lock.acquire()
            self.employees = copy.copy(employees)
            self.data_lock.release()

        self.db_op.pre_executeSelect(sql, after_execute_fn)

    @dec_print_exception
    @dec_print_time
    def select_employees(self, local_db_path):
        """本地数据库(同步方式)查询员工数据,并将员工数据更新到内存中.

        Parameters
        ----------
            local_db_path : str类型
                本地数据库路径.

        """
        # db操作
        db_op = DBTool_sqlite3(local_db_path)
        sql = "SELECT * FROM EMPLOYEES",
        result = db_op._executeSelect(sql)

        employees = {}
        for row in result:
            id = row[0]
            name = row[1]
            logger.info("employee id: {} name: {}".format(id, name))
            img_url = row[2]
            feature_list = []
            for i in range(3, len(row)):
                if row[i] is not None:
                    feature_list.append(row[i])
            employees[id] = {}
            employees[id]["name"] = name
            employees[id]["img_url"] = img_url
            employees[id]["feature_list"] = feature_list
        # 内存操作
        self.data_lock.acquire()
        self.employees = copy.copy(employees)
        self.data_lock.release()

        return True

    @dec_print_exception
    def add_vistor(self, id, name, img_url, valid_time_start, valid_time_end, feature):
        """内存, 本地数据库(异步方式)添加访客数据.

        Parameters
        ----------
            id : int类型
                访客id.
            name : str类型
                访客名字.
            img_url : str类型
                图片url.
            valid_time_start : int类型
                开始的时间戳，单位是ms
            valid_time_end : int类型
                结束的时间戳，单位是ms
            feature : numpy.array
                特征向量.

        """
        logger.info("add_vistor id: {} name: {}".format(id, name))
        # 内存操作
        self.data_lock.acquire()
        self.vistors[id] = {}
        self.vistors[id]["name"] = name
        self.vistors[id]["img_url"] = img_url
        self.vistors[id]["valid_time_start"] = valid_time_start
        self.vistors[id]["valid_time_end"] = valid_time_end
        feature_list = [feature]
        self.vistors[id]["feature_list"] = feature_list
        self.data_lock.release()
        # db操作
        sql = "INSERT OR REPLACE INTO VISTORS (ID, NAME, URL, VALID_TIME_START, VALID_TIME_END, FEATURE) VALUES (?, ?, ?, ?, ?, ?)", (
            id, name, img_url, valid_time_start, valid_time_end, feature,)
        self.db_op.pre_executeInsert(sql)

    @dec_print_exception
    def update_vistor(self, id, name, img_url, valid_time_start, valid_time_end, feature):
        """内存, 本地数据库(异步方式)修改访客数据.

        Parameters
        ----------
            id : int类型
                访客id.
            name : str类型
                访客名字.
            img_url : str类型
                图片url.
            valid_time_start : int类型
                开始的时间戳，单位是ms
            valid_time_end : int类型
                结束的时间戳，单位是ms
            feature : numpy.array
                特征向量.

        """
        # 内存操作
        self.data_lock.acquire()
        if id in self.vistors:
            self.vistors[id]["name"] = name
            self.vistors[id]["img_url"] = img_url
            self.vistors[id]["valid_time_start"] = valid_time_start
            self.vistors[id]["valid_time_end"] = valid_time_end
            self.vistors[id]["feature_list"][0] = feature
            self.data_lock.release()
            # db操作
            sql = "UPDATE VISTORS SET NAME = ?, URL = ?, VALID_TIME_START = ?, VALID_TIME_END = ?, FEATURE = ? WHERE ID = ?", (
                name, img_url, valid_time_start, valid_time_end, feature, id,)
            self.db_op.pre_executeUpdate(sql)
        else:
            # 增加访客数据
            # 内存操作
            self.vistors[id] = {}
            self.vistors[id]["name"] = name
            self.vistors[id]["img_url"] = img_url
            self.vistors[id]["valid_time_start"] = valid_time_start
            self.vistors[id]["valid_time_end"] = valid_time_end
            feature_list = [feature]
            self.vistors[id]["feature_list"] = feature_list
            self.data_lock.release()
            # db操作
            sql = "INSERT OR REPLACE INTO VISTORS (ID, NAME, URL, VALID_TIME_START, VALID_TIME_END, FEATURE) VALUES (?, ?, ?, ?, ?, ?)", (
                id, name, img_url, valid_time_start, valid_time_end, feature,)
            self.db_op.pre_executeInsert(sql)

    @dec_print_exception
    def del_vistor(self, id):
        """内存, 本地数据库(异步方式)删除访客数据.

        Parameters
        ----------
            id : int类型
                访客id.

        """
        self.data_lock.acquire()
        # 内存操作
        if id in self.vistors:
            self.vistors.pop(id)
        self.data_lock.release()
        # db操作
        sql = "DELETE FROM VISTORS WHERE ID = ?", (id,)
        self.db_op.pre_executeDelete(sql)

    @dec_print_exception
    def select_vistors_asyn(self):
        """本地数据库(异步方式)查询访客数据,并将访客数据更新到内存中.

        预留

        """
        # db操作
        sql = "SELECT * FROM VISTORS",

        def after_execute_fn(result):
            vistors = {}
            for row in result:
                id = row[0]
                name = row[1]
                logger.info("vistor id: {} name: {}".format(id, name))
                img_url = row[2]
                valid_time_start = row[3]
                valid_time_end = row[4]
                feature = row[5]
                feature_list = [feature]
                vistors[id] = {}
                vistors[id]["name"] = name
                vistors[id]["img_url"] = img_url
                vistors[id]["valid_time_start"] = valid_time_start
                vistors[id]["valid_time_end"] = valid_time_end
                vistors[id]["feature_list"] = feature_list
            # 内存操作
            self.data_lock.acquire()
            self.employees = copy.copy(vistors)
            self.data_lock.release()

        self.db_op.pre_executeSelect(sql, after_execute_fn)

    @dec_print_exception
    def select_vistors(self, local_db_path):
        """本地数据库(同步方式)查询访客数据,并将访客数据更新到内存中.

        Parameters
        ----------
            local_db_path : str类型.
                本地数据库路径.

        """
        # db操作
        db_op = DBTool_sqlite3(local_db_path)
        sql = "SELECT * FROM VISTORS",
        result = db_op._executeSelect(sql)

        vistors = {}
        for row in result:
            id = row[0]
            name = row[1]
            logger.info("vistor id: {} name: {}".format(id, name))
            img_url = row[2]
            valid_time_start = row[3]
            valid_time_end = row[4]
            feature = row[5]
            feature_list = [feature]
            vistors[id] = {}
            vistors[id]["name"] = name
            vistors[id]["img_url"] = img_url
            vistors[id]["valid_time_start"] = valid_time_start
            vistors[id]["valid_time_end"] = valid_time_end
            vistors[id]["feature_list"] = feature_list
        # 内存操作
        self.data_lock.acquire()
        self.vistors = copy.copy(vistors)
        self.data_lock.release()

    def get_employees(self):
        """获取内存中所有员工数据.

        Returns
        -------
        dict类型
            内存中所有员工数据. For example:
            {98: {'name': '张碧晨', 'img_url': '*.jpeg', 'feature_list': [array([[-2.66123144e-03, ...,
            97: ...
            }

        """
        self.data_lock.acquire()
        employees = copy.copy(self.employees)
        self.data_lock.release()
        return employees

    def get_vistors(self):
        """获取内存中所有访客数据.

        Returns
        -------
        dict类型
            内存中所有访客数据. For example:
            {48: {'name': 'HU', 'img_url': '*.jpg', 'valid_time_start': 1563206400000, 'valid_time_end': 1563811200000,
             'feature_list': [array([[-2.66123144e-03, ...,
            47: ...
            }

        """
        self.data_lock.acquire()
        vistors = copy.copy(self.vistors)
        self.data_lock.release()
        return vistors


# # test
# sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
# import my_args_ref
# sys.path.append(my_args_ref.my_args_dir)
# import my_args
# manager = DataManager(my_args)
# # while True:
# #     time.sleep(1)
# id = 1
# name = "l"
# feature = np.array([1, 2, 3])
# url = "http://1.jpg"
# manager.add_employee(id, name, url, feature)
# manager.update_employee(id, name, url, feature)
# manager.update_employee_feature2(id, feature)
# manager.del_employee(id)
# manager.del_employee(id)
# valid_time_start = time.time() - 10000
# valid_time_end = time.time()
# manager.add_vistor(id, name, url, valid_time_start, valid_time_end, feature)
# manager.update_vistor(id, name, url, valid_time_start, valid_time_end, feature)
# manager.del_vistor(id)
# manager.del_vistor(id)
# employees = manager.get_employees()
# vistors = manager.get_vistors()
