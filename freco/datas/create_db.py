# -*- coding: UTF-8 -*-
import sqlite3
import numpy as np
import io
import os
import sys
import traceback
sys.path.append(os.path.join(os.path.dirname(__file__), '..', '..'))
import my_args_ref
sys.path.append(my_args_ref.my_args_dir)
import my_args


def adapt_array(arr):
    out = io.BytesIO()
    np.save(out, arr)
    out.seek(0)
    return sqlite3.Binary(out.read())


def convert_array(text):
    out = io.BytesIO(text)
    out.seek(0)
    return np.load(out)


# Converts np.array to TEXT when inserting
sqlite3.register_adapter(np.ndarray, adapt_array)

# Converts TEXT to np.array when selecting
sqlite3.register_converter("array", convert_array)

# 连接数据库
conn = sqlite3.connect(my_args.local_db_path, detect_types=sqlite3.PARSE_DECLTYPES)
c = conn.cursor()
print("Opened database successfully")

# 删除表EMPLOYEES
try:
    c.execute('''DROP TABLE EMPLOYEES;''')
    conn.commit()
except Exception:
    traceback.print_exc()

# 创建表EMPLOYEES
c = conn.cursor()

c.execute('''CREATE TABLE EMPLOYEES
          (ID INTEGER PRIMARY KEY NOT NULL,
          NAME TEXT NOT NULL,
          URL TEXT NOT NULL,
          FEATURE array NOT NULL,
          FEATURE2 array,
          FEATURE3 array);''')
c.execute('''CREATE UNIQUE INDEX "em_index1" ON EMPLOYEES (ID);''')
conn.commit()
print("Created Table EMPLOYEES successfully")

# 删除表VISTORS
try:
    c.execute('''DROP TABLE VISTORS;''')
    conn.commit()
except Exception:
    traceback.print_exc()

# 创建表VISTORS
c = conn.cursor()
c.execute('''CREATE TABLE VISTORS
          (ID INTEGER PRIMARY KEY NOT NULL,
          NAME TEXT NOT NULL,
          URL TEXT NOT NULL,
          VALID_TIME_START INTEGER NOT NULL,
          VALID_TIME_END INTEGER NOT NULL,
          FEATURE array NOT NULL);''')
c.execute('''CREATE UNIQUE INDEX "vi_index1" ON VISTORS (ID);''')
conn.commit()
print("Created Table VISTORS successfully")

# 关闭数据库
conn.close()
print("Closed database successfully")
