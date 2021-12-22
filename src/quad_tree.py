import csv
import os
import random
import time

import pandas as pd

# settings
MAX_ELE_NUM = 100

QUADRANT_RU = 1
QUADRANT_LU = 2
QUADRANT_LB = 3
QUADRANT_RB = 4


class Region:
    def __init__(self, bottom, up, left, right):
        self.up = up
        self.bottom = bottom
        self.left = left
        self.right = right


class Point:
    def __init__(self, lng, lat, index=0):
        self.lng = lng
        self.lat = lat
        self.index = index

    def __eq__(self, other):
        if other.lng == self.lng and other.lat == self.lat:
            return True
        else:
            return False

    def __str__(self):
        return "Point({0}, {1}, {2})".format(self.lng, self.lat, self.index)

    def near(self, other):
        """
        近似相等，只要整数部分一致即可
        :param other:
        :return:
        """
        if int(other.lng) == int(self.lng) and int(other.lat) == int(self.lat):
            return True
        else:
            return False


class QuadTreeNode:
    def __init__(self, region, depth=1, is_leaf=1):
        self.depth = depth
        self.is_leaf = is_leaf
        self.region = region
        self.LU = None
        self.LB = None
        self.RU = None
        self.RB = None
        self.items = []  # ElePoitems[MAX_ELE_NUM]


class QuadTree:
    def __init__(self, region, max_num=MAX_ELE_NUM):
        """
        初始化非满四叉树，超过阈值就分裂
        :param max_num: 节点内的点数据数量预置
        """
        self.max_num = max_num
        self.root_node = QuadTreeNode(region=region)

    def build(self, points):
        for point in points:
            self.insert(point)

    def insert(self, point, node=None):
        """
        插入元素
        1.判断是否已分裂，已分裂的选择适合的子节点，插入；
        2.未分裂的查看是否过载，过载的分裂节点，重新插入；
        3.未过载的直接添加
    
        @param node
        @param point
    
        todo 使用元素原地址，避免重新分配内存造成的效率浪费
        """
        if node is None:
            node = self.root_node
        if node.is_leaf == 1:
            if len(node.items) + 1 > self.max_num:
                self.split_node(node)
                self.insert(point, node)
            else:
                # todo 点排重（不排重的话如果相同的点数目大于 MAX_ELE_NUM， 会造成无限循环分裂）
                node.items.append(point)
            return

        y_center = (node.region.up + node.region.bottom) / 2
        x_center = (node.region.left + node.region.right) / 2
        if point.lat > y_center:
            if point.lng > x_center:
                self.insert(point, node.RU)
            else:
                self.insert(point, node.LU)
        else:
            if point.lng > x_center:
                self.insert(point, node.RB)
            else:
                self.insert(point, node.LB)

    def split_node(self, node):
        """
        分裂节点
        1.通过父节点获取子节点的深度和范围
        2.生成四个节点，挂载到父节点下
        """
        y_center = (node.region.up + node.region.bottom) / 2
        x_center = (node.region.left + node.region.right) / 2

        node.is_leaf = 0
        node.RU = self.create_child_node(node, y_center, node.region.up, x_center, node.region.right)
        node.LU = self.create_child_node(node, y_center, node.region.up, node.region.left, x_center)
        node.RB = self.create_child_node(node, node.region.bottom, y_center, x_center, node.region.right)
        node.LB = self.create_child_node(node, node.region.bottom, y_center, node.region.left, x_center)

        for item in node.items:
            self.insert(item, node)

        # 清空父节点的element
        node.items = None

    def create_child_node(self, node, bottom, up, left, right):
        depth = node.depth + 1
        region = Region(bottom, up, left, right)
        child_node = QuadTreeNode(region=region, depth=depth)
        return child_node

    def delete(self, point, node=None):
        """
        删除元素
        1. 遍历元素列表，删除对应元素
        2. 检查兄弟象限元素总数，不超过最大量时组合兄弟象限
        """
        combine_flag = False
        if node is None:
            node = self.root_node
        if node.is_leaf == 1:
            for i in range(len(node.items)):
                if node.items[i] == point:
                    delete_index = node.items[i].index
                    combine_flag = True
                    del node.items[i]
                    return delete_index, combine_flag
            return -1, combine_flag
        else:
            y_center = (node.region.up + node.region.bottom) / 2
            x_center = (node.region.left + node.region.right) / 2
            if point.lat > y_center:
                if point.lng > x_center:
                    delete_index, combine_flag = self.delete(point, node.RU)
                else:
                    delete_index, combine_flag = self.delete(point, node.LU)
            else:
                if point.lng > x_center:
                    delete_index, combine_flag = self.delete(point, node.RB)
                else:
                    delete_index, combine_flag = self.delete(point, node.LB)
            if combine_flag:
                if (len(node.RU.items) + len(node.LU.items) + len(node.RB.items) + len(node.LB.items)) <= self.max_num:
                    self.combine_node(node)
                    combine_flag = False
            return delete_index, combine_flag

    def combine_node(self, node):
        """
        合并节点
        1. 遍历四个子象限的点，添加到象限点列表
        2. 释放子象限的内存
        """
        node.is_leaf = 1
        node.items = node.RU.items + node.LU.items + node.RB.items + node.LB.items
        node.RU = None
        node.LU = None
        node.RB = None
        node.LB = None

    def predict(self, point):
        return self.search(point, self.root_node)

    def search(self, point, node=None):
        if node is None:
            node = self.root_node
        # 节点内部查找：遍历
        if node.is_leaf == 1:
            for item in node.items:
                if item == point:
                    # if point.near(item):
                    return item.index
            return -1

        y_center = (node.region.up + node.region.bottom) / 2
        x_center = (node.region.left + node.region.right) / 2
        if point.lat > y_center:
            if point.lng > x_center:
                return self.search(point, node.RU)
            else:
                return self.search(point, node.LU)
        else:
            if point.lng > x_center:
                return self.search(point, node.RB)
            else:
                return self.search(point, node.LB)


def create_data_and_search():
    root_region = Region(-90, 90, -180, 180)
    quad_tree = QuadTree(region=root_region)
    lat, lng, index = 0, 0, 0
    for i in range(101):
        lng = random.uniform(-180, 180)
        lat = random.uniform(-90, 90)
        index += 1
        quad_tree.insert(Point(lng, lat, index))
    test_point = Point(lng, lat)
    search_index = quad_tree.search(test_point)
    print("{0} is found in {1}".format(test_point, search_index))
    delete_index, _ = quad_tree.delete(test_point)
    print("{0} is deleted in {1}".format(test_point, delete_index))


def create_data(path):
    with open(path, 'w', newline='') as csv_file:
        writer = csv.writer(csv_file)
        index = 0
        for i in range(100000):
            lng = random.uniform(-180, 180)
            lat = random.uniform(-90, 90)
            index += 1
            writer.writerow([lng, lat, index])


def read_data_and_search(path):
    data = pd.read_csv(path, header=None)
    train_set_point = []
    test_set_point = []
    test_ratio = 0.5  # 测试集占总数据集的比例
    for i in range(int(data.shape[0])):
        train_set_point.append(Point(data.iloc[i, 0], data.iloc[i, 1], data.iloc[i, 2]))
    test_set_point = train_set_point[:int(len(train_set_point) * test_ratio)]

    # build BTree index
    print("*************start QuadTree************")
    root_region = Region(-90, 90, -180, 180)
    quad_tree = QuadTree(region=root_region)
    print("Start Build")
    start_time = time.time()
    quad_tree.build(train_set_point)
    end_time = time.time()
    build_time = end_time - start_time
    print("Build QuadTree time ", build_time)
    err = 0
    print("Calculate error")
    start_time = time.time()
    for ind in range(len(test_set_point)):
        pre = quad_tree.predict(test_set_point[ind])
        err += abs(pre - test_set_point[ind].index)
        if err != 0:
            flag = 1
            pos = pre
            off = 1
            while pos != test_set_point[ind].index:
                pos += flag * off
                flag = -flag
                off += 1
    end_time = time.time()
    search_time = (end_time - start_time) / len(test_set_point)
    print("Search time ", search_time)
    mean_error = err * 1.0 / len(test_set_point)
    print("mean error = ", mean_error)
    print("*************end QuadTree************")


if __name__ == '__main__':
    os.chdir('D:\\Code\\Paper\\st-learned-index')
    path = 'data/test_x_y_index.csv'
    # create_data(path)
    create_data_and_search()
    # read_data_and_search(path)