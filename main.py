#!python
# -*- coding: utf-8 -*-

import sys
import numpy as np
import cv2
from scipy.ndimage import maximum_filter
import mss
import time
import os
from multiprocessing import Process
from CustomKeyboard import *

# 349f482e04b7bc460e6c060e169cec617c9397cc
COMPORT = "COM6"
ACCESS_KEY = 1234
"""
TODO: добавить выбор COM порта при запуске
TODO: добавить сохранение COM порта при запуске
TODO: пофиксить проблему очень темных крассных цветов
TODO: При каждой рекурсии, ставить aa[0] (количество гудов) в 1 
TODO: фильтры по X и Y (ищем медианное значение и при сильных отличиях - убираем)
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


def merging_indicators2(img, imgs_tpl, result, iters):
    kof1 = 0.9
    kof2 = 0.7  # 0.6
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
                print("add", new_data)
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
                print("add", new_data)
                result.append([1, new_data])
                return merging_indicators2(img, imgs_tpl, result, i)

    return result


def analis_awsd_multiple_sampling(imgs_tpl_a, imgs_tpl_w, imgs_tpl_s, imgs_tpl_d, loot_click):
    monitor = {"top": 340, "left": 763, "width": 385, "height": 84}
    img = None
    try:
        img = np.array(mss.mss().grab(monitor))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    except:
        print("Restart!!!!")
        sys.exit(0)
    cv2.imwrite("test.png", img)

    a = merging_indicators(img, imgs_tpl_a)
    w = merging_indicators(img, imgs_tpl_w)
    s = merging_indicators(img, imgs_tpl_s)
    d = merging_indicators(img, imgs_tpl_d)

    all = []

    # "Статичтический фильтр" - пережиток прошлого когда бдо использовало зашумление
    # сейчас скорей всего не особо нужен, но был оставлен, на точность все равно не влияет
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

    keyboard = CustomKeyboard(COMPORT, key=ACCESS_KEY)
    for i in all:
        keyboard.emulated_click(i[0])
        print(i[0])
        time.sleep(0.2)

    try:
        time.sleep(4)
        monitor = {"top": 10, "left": 10, "width": 1900, "height": 1060}
        img = np.array(mss.mss().grab(monitor))
        cv2.imwrite("test2.png", img)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        coord = find_templ(img, loot_click, 0.7, 0.71)
        if len(coord) != 0:
            keyboard.emulated_click("r")
            print("looted!!!")
    except:
        del keyboard
        print("Restart!!!!")
        sys.exit(0)
    del keyboard


def main():
    time.sleep(3)
    img_tpl_space = cv2.imread("data/patern_space.png", cv2.IMREAD_GRAYSCALE)
    img_tpl_m_first = cv2.imread("data/first_mini_game.png", cv2.IMREAD_GRAYSCALE)
    a_db = load_database_from_dir("data/a")
    w_db = load_database_from_dir("data/w")
    s_db = load_database_from_dir("data/s")
    d_db = load_database_from_dir("data/d")
    img_tpl_2space_bypass = cv2.imread("data/2space_bypass.png", cv2.IMREAD_GRAYSCALE)
    loot_click = cv2.imread("data/loot_click.png", cv2.IMREAD_GRAYSCALE)
    while True:
        time.sleep(0.1)
        monitor = {"top": 320, "left": 763, "width": 385, "height": 84}
        img = None
        try:
            img = np.array(mss.mss().grab(monitor))
            img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        except:
            print("Restart!!!!")
            sys.exit(0)

        coord = find_templ(img, img_tpl_m_first, 0.9, 0.71)
        if len(coord) != 0:
            print("press space (first mini game)")
            keyboard = CustomKeyboard(COMPORT, key=ACCESS_KEY)
            keyboard.emulated_click(" ")
            del keyboard
            # Ожидаем пока пропадет полоска первой мини игры
            time.sleep(4)
            analis_awsd_multiple_sampling(a_db, w_db, s_db, d_db, loot_click)

        coord = find_templ(img, img_tpl_space, 0.7, 0.71)
        if len(coord) != 0:
            print("Press space")
            keyboard = CustomKeyboard(COMPORT, key=ACCESS_KEY)
            keyboard.emulated_click(" ")
            del keyboard
            try:
                monitor = {"top": 20, "left": 763, "width": 385, "height": 84}
                img = np.array(mss.mss().grab(monitor))
                img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                coord = find_templ(img, img_tpl_2space_bypass, 0.7, 0.71)
                if len(coord) != 0:
                    print("Started new")
                    time.sleep(5)
                time.sleep(1)
            except:
                print("Restart!!!!")
                sys.exit(0)


if __name__ == "__main__":
    while True:
        p = Process(target=main)
        print("started new process")
        p.start()
        p.join()

