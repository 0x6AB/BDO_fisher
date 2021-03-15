#!python
# -*- coding: utf-8 -*-
import sys
import numpy as np
import cv2
from scipy.ndimage import maximum_filter
import mss
import time
import os
from multiprocessing import Process, freeze_support
from CustomKeyboard import *
import argparse
import json

global_monitor = {"top": 0, "left": 500, "width": 900, "height": 1080}

"""
TODO: разработать систему конфигов
TODO: добавить конфиги под 1440p, 720p
TODO: добавить сохранение COM порта при запуске
TODO: пофиксить проблему очень темных крассных цветов (по идее достаточно собрать семпл,
                                                или прийдётся менять один с каналов перед преобразованием)
TODO: При каждой рекурсии, ставить aa[0] (количество гудов) в 1 
TODO: добавить фильтр рыбы
TODO: добавить смену удочек
"""


def find_templ(img, img_tpl, filter_koef, koef):
    # размер шаблона
    h, w = img_tpl.shape

    # строим карту совпадений с шаблоном
    match_map = cv2.matchTemplate(img, img_tpl, cv2.TM_CCOEFF_NORMED)

    # значение карты для области максимально близкой к шаблону
    max_match_map = np.max(match_map)

    if (max_match_map < koef):
        return []   # совпадения не обнаружены

    # коэффициент "похожести", 0 - все, 1 - точное совпадение
    a = filter_koef
    # отрезаем карту по порогу 
    match_map = (match_map >= max_match_map * a) * match_map

    # выделяем на карте локальные максимумы
    match_map_max = maximum_filter(match_map, size=min(w, h))
    # т.е. области наиболее близкие к шаблону
    match_map = np.where((match_map == match_map_max), match_map, 0)

    # координаты локальных максимумов
    ii = np.nonzero(match_map)
    rr = tuple(zip(*ii))

    res = [[c[1], c[0], w, h] for c in rr]
   
    return res


def load_database_from_dir(dir):
    loaded_data = []
    for f in filter(lambda x: x.endswith('.png'), os.listdir(dir)):
        loaded_data.append(cv2.imread(os.path.join(dir, f), cv2.IMREAD_GRAYSCALE))
    return loaded_data


"""
Две функи ниже писались давно, что там происходит я и сам не помню, в ближайшее время постараюсь переписать нормально.
Основаная задача медианная фильтрация данных (с особенностями)
"""


def merging_indicators2(img, imgs_tpl, result, iters):
    kof1 = 0.9
    kof2 = 0.7  # 0.6
    for i in range(1, len(imgs_tpl)):
        new_datas = find_templ(img, imgs_tpl[i], kof1, kof2)
        # Ориентируемся на координаты x,y
        # Отличие плюс, минус 5
        # Медианный фильтр по координатам
        for new_data in new_datas:
            # x = new_data[0], y = new_data[1]
            flag = True
            for aa in result:
                # aa[0] - int значение количества гудов на эту точку
                # aa[1] - точка
                if new_data[0] - 5 < aa[1][0] < new_data[0] + 5 and new_data[1] - 5 < aa[1][1] < new_data[1] + 5:
                    aa[0] += 1
                    flag = False

            if flag:
                # print("add2", new_data)
                result.append([1, new_data])
                return merging_indicators2(img, imgs_tpl, result, i)
    return result


def merging_indicators(img, imgs_tpl):
    kof1 = 0.9
    kof2 = 0.7  # 0.6

    result = []
    for dat in find_templ(img, imgs_tpl[0], kof1, kof2):
        result.append([1, dat])

    for i in range(1, len(imgs_tpl)):
        new_datas = find_templ(img, imgs_tpl[i], kof1, kof2)
        # Ориентируемся на координаты x,y
        # Отличие плюс, минус 5
        for new_data in new_datas:
            # x = new_data[0], y = new_data[1]
            flag = True
            for aa in result:
                # aa[0] - int значение количества гудов на эту точку
                # aa[1] - точка
                if new_data[0] - 5 < aa[1][0] < new_data[0] + 5 and new_data[1] - 5 < aa[1][1] < new_data[1] + 5:
                    aa[0] += 1
                    flag = False

            if flag:
                # print("add", new_data)
                result.append([1, new_data])
                return merging_indicators2(img, imgs_tpl, result, i)

    return result


def analis_awsd_multiple_sampling(imgs_tpl_a, imgs_tpl_w, imgs_tpl_s, imgs_tpl_d, loot_click):
    start_time = time.time()
    img = None
    try:
        img = np.array(mss.mss().grab(global_monitor))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    except:
        print("Restart!!!!")
        sys.exit(0)
    # cv2.imwrite("test.png", img)

    a = merging_indicators(img, imgs_tpl_a)
    w = merging_indicators(img, imgs_tpl_w)
    s = merging_indicators(img, imgs_tpl_s)
    d = merging_indicators(img, imgs_tpl_d)

    all = []

    # "Статичтический фильтр" - пережиток прошлого когда бдо использовало зашумление
    # сейчас скорей всего не особо нужен, но был оставлен, повышает точность
    # Раньше еще использовалось, помимо использования нескольких патернов,
    # семплирование на протяжении какого то времени.
    for aa in a:
        if aa[0] >= 2:
            all.append(("a", aa[1]))
    for ww in w:
        if ww[0] >= 2:
            all.append(("w", ww[1]))
    for ss in s:
        if ss[0] >= 2:
            all.append(("s", ss[1]))
    for dd in d:
        if dd[0] >= 2:
            all.append(("d", dd[1]))

    # Сортировка по координате x
    all.sort(key=lambda x: (int(x[1][0])))

    print("analis_awsd_multiple_sampling %s seconds" % (time.time() - start_time))

    keyboard = CustomKeyboard(COMPORT, key=ACCESS_KEY)
    for i in all:
        keyboard.emulated_click(i[0])
        print("[%s]" % i[0])
        time.sleep(0.2)

    try:
        time.sleep(4)
        monitor = {"top": 10, "left": 10, "width": 1900, "height": 1060}
        img = np.array(mss.mss().grab(monitor))
        # cv2.imwrite("test.png", img)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        coord = find_templ(img, loot_click, 0.7, 0.71)
        if len(coord) != 0:
            keyboard.emulated_click("r")
            print("[r]")
    except:
        del keyboard
        print("Restart!!!!")
        sys.exit(0)
    del keyboard


def main(local_comport, local_ACCESS_KEY, local_config):

    global COMPORT
    COMPORT = local_comport
    global ACCESS_KEY
    ACCESS_KEY = local_ACCESS_KEY

    config = json.loads(open(local_config).read())
    # global global_monitor
    # global_monitor = config["monitor_global"]
    img_tpl_space = cv2.imread(config["patterns"]["space"], cv2.IMREAD_GRAYSCALE)
    img_tpl_m_first = cv2.imread(config["patterns"]["first_mini_game"], cv2.IMREAD_GRAYSCALE)
    a_db = load_database_from_dir(config["patterns"]["a_dir"])
    w_db = load_database_from_dir(config["patterns"]["w_dir"])
    s_db = load_database_from_dir(config["patterns"]["s_dir"])
    d_db = load_database_from_dir(config["patterns"]["d_dir"])
    img_tpl_2space_bypass = cv2.imread(config["patterns"]["2space_bypass"], cv2.IMREAD_GRAYSCALE)
    loot_click = cv2.imread(config["patterns"]["loot_click"], cv2.IMREAD_GRAYSCALE)

    while True:
        time.sleep(0.01)
        img = None
        try:
            img = np.array(mss.mss().grab(global_monitor))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        except Exception as e:
            print("1 Restart!!!!")
            sys.exit(0)

        coord = find_templ(img, img_tpl_m_first, 0.9, 0.71)
        if len(coord) != 0:
            print("[space] (first mini game)")
            keyboard = CustomKeyboard(COMPORT, key=ACCESS_KEY)
            keyboard.emulated_click(" ")
            del keyboard
            # Ожидаем пока пропадет полоска первой мини игры
            sleep_time = random.uniform(2.5, 3.0)
            time.sleep(sleep_time)
            analis_awsd_multiple_sampling(a_db, w_db, s_db, d_db, loot_click)

        coord = find_templ(img, img_tpl_space, 0.7, 0.71)
        if len(coord) != 0:
            print("[space]")
            keyboard = CustomKeyboard(COMPORT, key=ACCESS_KEY)
            keyboard.emulated_click(" ")
            del keyboard
            time.sleep(0.5)
            try:
                img = np.array(mss.mss().grab(global_monitor))
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                coord = find_templ(img, img_tpl_2space_bypass, 0.7, 0.71)
                if len(coord) != 0:
                    print("Started new")
                    time.sleep(5)
                time.sleep(1)
            except Exception as e:
                print("2 Restart!!!!")
                sys.exit(0)


if __name__ == "__main__":
    # Для работы модуля multiprocessing с pyinstaller
    freeze_support()

    parser = argparse.ArgumentParser(description='Black desert fishing bot')

    parser.add_argument('--port', action="store", dest="port", default=None, type=str)
    parser.add_argument('--key', action="store", dest="key", default=1234, type=int)
    parser.add_argument('--config', action="store", dest="config", default="1080p_RU.json", type=str)
    args = parser.parse_args()
    if not args.port:
        i = 0
        ports = serial_ports()
        for port in ports:
            i += 1
            print("%d) %s" % (i, port))
        print("Please select COM port (1-%d): " % i, end="")
        num = int(input())
        try:
            args.port = ports[num-1]
        except:
            print("Error select port")
            sys.exit(-1)

    time.sleep(3)
    while True:
        p = Process(target=main, args=(args.port, args.key, args.config))
        print("started new process")
        p.start()
        p.join()

