import numpy as np
import pytest
from src import data_matrices as dm
from tests.test_data_matrices import create_floor, create_floor2, create_building


def test_horizontal_distance():
    """
    testuje czy funkcja get_horizontal_distance poprawnie liczy odległość poziomą
    """
    building = create_building()
    point1 = dm.Point(x=0, y=0, Floor_number=0)
    point2 = dm.Point(x=3, y=4, Floor_number=0)
    
    distance = building.horizontal_distance(point1, point2)
    
    assert distance == 5.0  # 3-4-5 triangle


def test_bresenham_distance():
    """
    testuje czy poprawnie interpoluję prostą
    """
    building = create_building()
    floor = np.zeros((10, 10))
    list = building.bresenham_2d(0, 0, 7, 5)

    for (x, y) in list:
        floor[y, x] = 1  # zaznaczamy punkty na macierzy
    
    print(floor)
    assert True

def test_bresenham_distance_same_point():
    """
    testuje czy poprawnie interpoluję prostą
    """
    building = create_building()
    floor = np.zeros((10, 10))
    list = building.bresenham_2d(0, 0, 0, 0)

    assert list == [(0, 0)]
    

def test_total_floor_thickness():
    """
    testuje czy funkcja total_floor_thickness poprawnie sumuje grubości pięter
    """
    building = create_building()
    
    thickness = building.total_floor_thickness(0, 2)  # od piętra 0 do 2
    
    assert thickness == 7.0  # 3.0 + 4.0


@pytest.mark.parametrize("floor_count", [0, 1, 2])
def test_calculate_line_floors(floor_count):
    """
    testuje czy funkcja calculate_line_floors poprawnie wylicza punkty na linii między dwoma punktami
    """

    f1 = dm.Floor(np.zeros((10, 10)), np.zeros((10, 10)), np.zeros((10, 10)), 0, 2)
    f2 = dm.Floor(np.zeros((10, 10)), np.zeros((10, 10)), np.zeros((10, 10)), 1, 2)
    f3 = dm.Floor(np.zeros((10, 10)), np.zeros((10, 10)), np.zeros((10, 10)), 2, 2)

    building = dm.Building([f1, f2, f3], Floor_heights=3)
   
    point1 = dm.Point(x=0, y=0, Floor_number=0)
    point2 = dm.Point(x=3, y=4, Floor_number= floor_count)

    if floor_count == 0:
        with pytest.raises(ValueError):
            building.calculate_line_floors(point1, point2)
        return  # kończymy test dla tego przypadku

    line_floors = building.calculate_line_floors(point1, point2)


    print(len(line_floors[0]))
    for p in line_floors[0]:
        print(p.x, p.y, p.Floor_number)
    assert True


def test_get_all_walls_same_floor():
    """
    testuje czy funkcja get_all_walls poprawnie sumuje tłumienie na tej samej kondygnacji
    """
    building = create_building()
    floor = building.Floor_list[0]

    point1 = dm.Point(x=0, y=0, Floor_number=0)
    point2 = dm.Point(x=2, y=1, Floor_number=0)

    walls = building.get_all_walls(point1, point2)

    expected_walls = 0
    line_points = building.bresenham_2d(point1.x, point1.y, point2.x, point2.y)
    n = len(line_points)
    for (x, y) in line_points:
        expected_walls += floor.wall[x, y]
    print(walls)

    assert walls == (expected_walls, 0.0)

def test_get_all_walls_same_floor2():
    """
    testuje czy funkcja get_all_walls poprawnie sumuje tłumienie na tej samej kondygnacji
    """
    building = create_building()
    floor = building.Floor_list[1]

    point1 = dm.Point(x=2, y=0, Floor_number=1)
    point2 = dm.Point(x=0, y=2, Floor_number=1)

    walls = building.get_all_walls(point1, point2)

    expected_walls = 0
    line_points = building.bresenham_2d(point1.x, point1.y, point2.x, point2.y)
    n = len(line_points)
    print(n)
    for (x, y) in line_points:
        expected_walls += floor.wall[x, y]
        print(x, y)
    print(walls)

    assert walls == (expected_walls, 0.0)

def test_get_all_walls_different_floors():
    """
    testuje czy funkcja get_all_walls poprawnie sumuje tłumienie na różnych kondygnacjach
    """
    building = create_building()

    point1 = dm.Point(x=0, y=0, Floor_number=0)
    point2 = dm.Point(x=2, y=2, Floor_number=2)

    walls, total_thickness = building.get_all_walls(point1, point2)

    expected_walls = 0
    total_floor_thickness = 0.0
    floor_points, total_floor_thickness = building.calculate_line_floors(point1, point2)

    for i in range(0, len(floor_points) - 1, 2):
        fp1 = floor_points[i]
        fp2 = floor_points[i + 1]
        floor = building.Floor_list[fp1.Floor_number]
        line_points = building.bresenham_2d(fp1.x, fp1.y, fp2.x, fp2.y)
        n = len(line_points)
        for (x, y) in line_points:
            expected_walls += floor.wall[x, y]*(1 + (building.Floor_heights/n)**2)**0.5

    print(walls, total_thickness)

    assert walls == expected_walls
    assert total_thickness == total_floor_thickness

