# -*- coding: utf-8 -*-
import sys
import os
sys.path.append(os.path.dirname(__file__))
import face_model
import arg
from threading import Lock
import traceback
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from utilities.log import get_logger

logger = get_logger(__name__)

print(os.getcwd())

model = face_model.FaceModel(arg)

gLock_arcface = Lock()


def img_feature(image, model=model):
    global gLock_arcface

    try:
        gLock_arcface.acquire()
        img = model.get_input(image)
        # print(img)
        f1 = model.get_feature(img)
        gLock_arcface.release()
        return f1
    except Exception:
        logger.error(traceback.format_exc())
        gLock_arcface.release()
        return []

    return []


'''
model = face_model.FaceModel(args)
img = cv2.imread('C:\\Users\\123\\Desktop\\94d1cad0f434412cb4c34fc9df56511789g3j.jpg')
#'C:\\Users\\123\\Desktop\\cap20190615-132909_06000082.jpg'
img = model.get_input(img)
f1 = model.get_feature(img)
f4 = model.get_feature(img)
f5 = model.get_feature(img)
#print(f1[0:10])
#gender, age = model.get_ga(img)
#print(gender)
#rint(age)
#sys.exit(0)
path_img = []
path = 'C:\\Users\\123\\Desktop\\8'
for base_path in os.listdir(path):
    path_img.append(os.path.join(path, base_path))
cout = 0
print(path_img)
for item in path_img:
    try:
        cout += 1
        img  = cv2.imread(item)
        input_image  = model.get_input(img)
        f2 = model.get_feature(input_image)
        sim = np.dot(f1, f2.T)
        sim2 =  np.sqrt(np.dot(f1, f1.T))
        sim3 =  np.sqrt(np.dot(f2, f2.T))
    except:
        print('%d not algin '%cout)
    print(sim/sim2/sim3)
cos_dist = abs(np.sum(f1*f2)/np.sqrt((np.sum(np.square(f1)))*np.sqrt(np.sum(np.square(f2)))))
print(cos_dist)
print(len(f1))
'''
# diff = np.subtract(source_feature, target_feature)
# dist = np.sum(np.square(diff),1)
