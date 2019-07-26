# -*- coding: utf-8 -*-
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
import numpy as np
import json
import cv2
import time
import re
import base64
import copy
import traceback
import schedule
from threading import Thread, Lock
import my_args_ref
import sys
sys.path.append(my_args_ref.my_args_dir)
import my_args
from freco.datas.data_manager import DataManager
from freco.utilities.utility import dec_print_exception, dec_print_time
from freco.externals.data_transfer import DataSender, request_employees
from freco.algorithms.algo_implement import compare_cosdist, gen_feature, gen_feature_from_url
from freco.utilities.log import get_logger

logger = get_logger(__name__)


@csrf_exempt
@dec_print_time
def face_add_employee(request):
    """增加员工数据."""
    global faceRecognition

    logger.info("[http]face_add_employee")

    data = {"success": False}
    if request.method == "POST":
        try:
            body_unicode = request.body.decode('utf-8')
            body = json.loads(body_unicode)
            id = body['id']
            name = body['name']
            img_url = body['url']
        except Exception:
            logger.error(traceback.format_exc())
            data["success"] = False
            return JsonResponse(data)
        feature = gen_feature_from_url(img_url)
        if feature is not None and feature.size > 0:
            faceRecognition.dataManager.add_employee(
                id, name, img_url, feature)

    data["success"] = True
    return JsonResponse(data)


@csrf_exempt
@dec_print_time
def face_update_employee(request):
    """修改员工数据."""
    global faceRecognition

    logger.info("[http]face_update_employee")

    data = {"success": False}
    if request.method == "POST":
        try:
            body_unicode = request.body.decode('utf-8')
            body = json.loads(body_unicode)
            id = body['id']
            name = body['name']
            img_url = body['url']
        except Exception:
            logger.error(traceback.format_exc())
            data["success"] = False
            return JsonResponse(data)

        feature = gen_feature_from_url(img_url)
        if feature is not None and feature.size > 0:
            faceRecognition.dataManager.update_employee(
                id, name, img_url, feature)

    data["success"] = True
    return JsonResponse(data)


@csrf_exempt
@dec_print_time
def face_del_employee(request):
    """删除员工数据."""
    global faceRecognition

    logger.info("[http]face_del_employee")

    data = {"success": False}

    # check to see if this is a post request
    if request.method == "POST":
        try:
            body_unicode = request.body.decode('utf-8')
            body = json.loads(body_unicode)
            id = body['id']
        except Exception:
            logger.error(traceback.format_exc())
            data["success"] = False
            return JsonResponse(data)

        faceRecognition.dataManager.del_employee(id)

    data["success"] = True
    return JsonResponse(data)


@csrf_exempt
def upload(request):
    """
    receive pictures transferred by the camera and analyze the pictures.

    Parameters:
      data - reponse information
      request - incoming data , Type: "POST", including deviceId and image information, key words in request: 'divid', 'faces'
    Returns:
      data: retrun result, upload of image successful or fail
    Raises:
    HTTPError: the http address is wrong
    KeyError - the key word of upload data is wrong
    """
    global faceRecognition

    logger.info("[http]upload")

    data = {"success": True}
    msg = ''
    if request.method == "POST":
        try:
            body_unicode = request.body.decode('utf-8')
            body_data = json.loads(body_unicode)
            dev_id = int(body_data['devno'])
            if 'faces' in body_data:
                for face in body_data['faces']:
                    if 'image' in face:
                        image_data_base64 = re.sub('^data:image/.+;base64,', '', face["image"])
                        # 解码
                        img_data = base64.b64decode(image_data_base64)
                        # 转换为np数组
                        img_array = np.frombuffer(img_data, np.uint8)
                        # 转换成opencv可用格式
                        image = cv2.imdecode(img_array, cv2.COLOR_RGB2BGR)
                        shot_time = round(time.time())
                        faceRecognition.add_task(dev_id, image, shot_time)
                    else:
                        # 如果没有图片，报错
                        msg = "image is not exist"
                        logger.error(msg)
                    # 只解析第一张
                    break
        except Exception:
            logger.error(traceback.format_exc())
    else:
        msg = "invaild request type: {}".format(request.method)
        logger.error(msg)

    return JsonResponse(data)


class FaceRecognition(Thread):
    """人脸识别的类.

    实现人脸检测逻辑,定时更新机制,使用数据管理模块和数据上传模块.

    Attributes
    ----------
    dataManager : DataManager类型.
        数据管理类.
    dataSender : DataSender类型.
        数据上传类.
    list : str类型.
        待识别的图片队列
    photo_back_dir : str类型.
        备份的图片目录
    """
    class Task(object):
        """人脸识别的任务.

        Attributes
        ----------
        dev_id : int类型.
            设备id.
        image : str类型.
            待识别的图片.
        shot_time : int类型.
            抓拍时间戳.
        """

        def __init__(self, dev_id, image, shot_time):
            """初始化函数"""
            self.dev_id = dev_id
            self.image = image
            self.shot_time = shot_time

    def __init__(self, args):
        """初始化函数"""
        super().__init__()
        self.dataManager = DataManager(args)
        self.dataSender = DataSender()
        self.photo_back_dir = my_args.photo_back_dir
        self.task_list = []
        self.task_lock = Lock()

    def add_task(self, id, dev_id, shot_time):
        task = FaceRecognition.Task(id, dev_id, shot_time)
        self.task_lock.acquire()
        if len(self.task_list) > 500:
            self.task_list.pop(0)
        self.task_list.append(task)
        self.task_lock.release()

    @dec_print_exception
    @dec_print_time
    def update_all(self):
        """根据服务器的数据,同步本地的员工数据."""
        # 获取本地员工数据和服务器的员工数据
        local_employees = self.dataManager.get_employees()
        while True:
            # 请求服务器失败就一直请求
            remote_employees = request_employees()
            if remote_employees is None:
                logger.error("request_employees fail")
                time.sleep(3)
                continue
            else:
                logger.info("request_employees success")
                break

        # 同步本地员工数据
        for item in remote_employees.items():
            id = item[0]
            if id in local_employees:
                # 更新
                local_name = local_employees[id]["name"]
                local_img_url = local_employees[id]["img_url"]

                remote_name = remote_employees[id]["name"]
                remote_img_url = remote_employees[id]["img_url"]

                if local_name == remote_name and local_img_url == remote_img_url:
                    # 一样就不更新
                    pass
                else:
                    new_name = remote_name
                    new_img_url = remote_img_url
                    if local_img_url != remote_img_url:
                        new_feature = gen_feature_from_url(remote_img_url)
                        if new_feature is not None and new_feature.size > 0:
                            self.dataManager.update_employee(
                                id, new_name, new_img_url, new_feature)
                    else:
                        new_feature = local_employees[id]["feature_list"][0]
                        self.dataManager.update_employee(
                            id, new_name, new_img_url, new_feature)
            else:
                # 增加
                new_name = remote_employees[id]["name"]
                new_img_url = remote_employees[id]["img_url"]
                new_feature = gen_feature_from_url(new_img_url)
                if new_feature is not None and new_feature.size > 0:
                    self.dataManager.add_employee(
                        id, new_name, new_img_url, new_feature)
        # 删除
        for item in local_employees.items():
            id = item[0]
            if id not in remote_employees:
                self.dataManager.del_employee(id)

    def find_by_feature(self, reference_dict, feature):
        """根据特征向量查找对应的id和名字.

        Parameters
        ----------
        reference_dict : dict类型
            比对库.
        feature : numpy.array类型
            特征向量.

        Returns
        -------
        int类型, str类型
            人员id和人员名字. For example:
            1, "吕俊秀"

        """
        result = compare_cosdist(reference_dict, feature)
        if result is not None:
            id, name = result

        return id, name

    @dec_print_time
    def photo_analyze(self, image):
        """图片识别.

        Parameters
        ----------
        image : str类型
            图片.

        Returns
        -------
        int类型, int类型, str类型
            返回类型,人员id,人员名字. For example:
            1, 1, "吕俊秀"

        """
        type = -1  # -1:图片异常,0:识别为员工,2:未识别
        id = -1
        name = ""

        employees = self.dataManager.get_employees()

        feature = gen_feature(image)
        if feature is not None and feature.size > 0:
            # 比对员工库
            id, name = self.find_by_feature(employees, feature)
            if id == -1:
                # 未识别即陌生人
                type = 2
            else:
                # 识别为员工
                type = 0
        else:
            type = -1

        return type, id, name

    def run(self):
        """一直检测."""
        # 成功次数
        sucCount = 0
        # 失败次数
        failCount = 0

        # 每一小时定时同步员工数据
        schedule.every().hour.do(self.update_all)

        assert_dict = {}

        while True:
            # 定时器更新
            schedule.run_pending()

            task_list = []
            self.task_lock.acquire()
            task_list = copy.copy(self.task_list)
            self.task_list.clear()
            self.task_lock.release()

            if len(task_list) <= 0:
                time.sleep(0.005)
            else:
                for task in task_list:
                    image = task.image
                    dev_id = task.dev_id
                    shot_time = task.shot_time

                    type, id, name = self.photo_analyze(image)

                    # 统计识别结果
                    if type == 0:
                        # 识别成功
                        sucCount += 1
                    else:
                        failCount += 1
                    logger.info("sucCount:{}".format(sucCount))
                    logger.info("failCount:{}".format(failCount))

                    if type == 2:
                        logger.info("未识别")
                        # data['id'] = -1
                    elif type == -1:
                        logger.error("图片异常")
                    elif type == 0:
                        logger.info("识别员工: %s" % name)
                        if dev_id in assert_dict.keys():
                            if id in assert_dict[dev_id].keys():
                                if abs(shot_time - assert_dict[dev_id][id][-1]) < 4:
                                    logger.info('短时间内相同设备相同人员过滤')
                                    continue
                        upload_status = self.dataSender.upload_record_employee(id, dev_id, shot_time)
                        if upload_status is False:
                            logger.error("upload_record_employee fail. id: {}, name: {}".format(
                                id, name))
                            # 一旦失败,清理任务队列.防止累积历史数据上传,导致误开门问题
                            break
                        else:
                            logger.info("upload_record_employee success. id: {}, name: {}".format(
                                id, name))

                        if dev_id not in assert_dict.keys():
                            assert_dict[dev_id] = {}
                            assert_dict[dev_id][id] = [shot_time]
                        else:
                            if id not in assert_dict[dev_id].keys():
                                assert_dict[dev_id][id] = [shot_time]
                            else:
                                if len(assert_dict[dev_id][id]) > 10:
                                    assert_dict[dev_id][id].pop(0)
                                assert_dict[dev_id][id].append(shot_time)


faceRecognition = FaceRecognition(my_args)
faceRecognition.update_all()
faceRecognition.start()
# thread1 = Thread(target=face_recognize, args=()).start()
