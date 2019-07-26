# -*- coding: utf-8 -*-
import numpy as np
import os
import sys
import cv2
import requests
sys.path.append(os.path.join(os.path.dirname(__file__)))
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
import insightface.deploy.arcface as arcface
from utilities.utility import dec_print_exception, dec_print_time
from utilities.log import get_logger
import my_args_ref
sys.path.append(my_args_ref.my_args_dir)
import my_args

logger = get_logger(__name__)


@dec_print_exception
def compare_cosdist(reference_dict, feature):
    """比较特征向量和对比库的各个余弦距离,返回最大的人员id和名字.

    Parameters
    ----------
    reference_dict : dict类型
        对比库.
    feature : numpy.array类型
        特征向量.

    Returns
    -------
    int类型, 名字
        员工id和名字. For example:
        1, "吕俊秀"

        异常返回None.

    """
    id = -1
    name = ""

    if not reference_dict:
        # dict为空，直接返回
        id = -1
        name = ""
        return id, name

    threshold = my_args.threshold

    all_cos_list = []
    all_id_list = []

    for item in reference_dict.items():
        id = item[0]
        cos_list = []
        feature_list = item[1]["feature_list"]
        feature_num = len(feature_list)
        for i in range(feature_num):
            feature_item = feature_list[i]
            cos = np.sum(np.multiply(feature_item, feature)) / np.sqrt(
                np.sum(np.square(feature_item))) / np.sqrt(np.sum(np.square(feature)))
            cos_list.append(cos)
        cos_max = max(cos_list)
        all_cos_list.append(cos_max)
        all_id_list.append(id)
    index = np.argmax(all_cos_list)
    logger.debug("max(all_cos_list): %f" % max(all_cos_list))
    if max(all_cos_list) > threshold:
        id = all_id_list[index]
        name = reference_dict[id]["name"]
    else:
        id = -1
        name = ""

    return id, name


@dec_print_exception
@dec_print_time
def gen_feature_from_url(img_url):
    """先下载图片,生成特征向量.

    Parameters
    ----------
    img_url : str类型
        图片url.

    Returns
    -------
    numpy.array类型
        特征向量. For example:
        [...]

        异常返回None.

    """
    feature = np.array([])

    # 下载图片
    res = requests.get(img_url, timeout=(3, 3))
    content = res.content
    image = np.asarray(bytearray(content), dtype="uint8")
    image = cv2.imdecode(image, cv2.IMREAD_COLOR)
    img_feature = arcface.img_feature(image)
    if len(img_feature) == 0:
        logger.error('gen_feature_from_url fail')
    else:
        feature = np.array([img_feature])

    return feature


@dec_print_exception
@dec_print_time
def gen_feature_from_local(img_local_path):
    """生成特征向量.

    Parameters
    ----------
    img_local_path : str类型
        本地图片路径.

    Returns
    -------
    numpy.array类型
        特征向量. For example:
        [...]

        异常返回None.

    """
    feature = np.array([])

    # 读取图片
    # 延迟可以避免:手动拷贝图片测试时，cv2.imread会报错
    # time.sleep(1)
    image = cv2.imread(img_local_path)
    logger.debug("gen_feature_from_local, img_local_path:{}".format(img_local_path))
    img_feature = arcface.img_feature(image)
    if len(img_feature) == 0:
        logger.error('gen_feature_from_local fail')
    else:
        feature = np.array([img_feature])

    return feature


@dec_print_exception
@dec_print_time
def gen_feature(image):
    """生成特征向量.

    Parameters
    ----------
    image : str类型
        图片.

    Returns
    -------
    numpy.array类型
        特征向量. For example:
        [...]

        异常返回None.

    """
    feature = np.array([])

    img_feature = arcface.img_feature(image)
    if len(img_feature) == 0:
        logger.error('gen_feature_from_local fail')
    else:
        feature = np.array([img_feature])

    return feature

# test
# dir = "E:/tool/Git/zhongzhou_pic_store/base_root/pic_store/media/"
# for filename in os.listdir(dir):
#     if filename.endswith(".jpg"):
#         print(os.path.join(dir + filename))
#         gen_feature_from_local(os.path.join(dir + filename))
#         # th1 = threading.Thread(target=gen_feature_from_local, args=(
#         #     os.path.join(dir + filename),))
#         # th1.start()
#         time.sleep(50)
#
#
# while True:
#     time.sleep(1)
