import numpy as np
import pytest
from src import data_matrices as dm


def create_floor():
    """
    funkcja pomocnicza tworząca przykładowe piętro do testów
    """
    wall = np.array([[0.5, 1.0, 0.5],
                     [1.0, 1.5, 1.0],
                     [0.5, 1.0, 0.5]], dtype=float)
    router = np.array([[0, 1, 0],
                       [1, 1, 1],
                       [0, 0, 0]], dtype=int)
    cover = np.array([[1, 1, 0],
                      [0, 1, 1],
                      [0, 0, 0]], dtype=int)
    
    return dm.Floor(wall_matrix=wall,
                    router_matrix=router,
                    cover_matrix=cover,
                    Floor_number=0,
                    Floor_thickness=3)

def create_floor2():
    """
    funkcja pomocnicza tworząca przykładowe piętro do testów
    """
    wall = np.array([[1.5, 1.0, 1.5],
                     [0.0, 0.0, 0.0],
                     [1.5, 1.0, 1.5]], dtype=float)
    router = np.array([[0, 0, 0],
                       [1, 1, 1],
                       [0, 0, 0]], dtype=int)
    cover = np.array([[0, 0, 0],
                      [1, 1, 1],
                      [0, 0, 0]], dtype=int)
    
    return dm.Floor(wall_matrix=wall,
                    router_matrix=router,
                    cover_matrix=cover,
                    Floor_number=1,
                    Floor_thickness=4)


def test_create_floor_returns_valid_floor():
    """
    testuje czy funkcja create_floor poprawnie tworzy obiekt Floor
    """
    floor = create_floor()
    assert isinstance(floor, dm.Floor)
    assert floor.Floor_number == 0
    assert floor.Floor_thickness == 3.0
    expected_router = np.array([[0, 1, 0],
                                [1, 1, 1],
                                [0, 0, 0]], dtype=int)
    expected_cover = np.array([[1, 1, 0],
                               [0, 1, 1],
                               [0, 0, 0]], dtype=int)
    expected_wall = np.array([[0.5, 1.0, 0.5],
                              [1.0, 1.5, 1.0],
                              [0.5, 1.0, 0.5]], dtype=float)
    assert np.array_equal(floor.router, expected_router)
    assert np.array_equal(floor.cover, expected_cover)
    assert np.array_equal(floor.wall, expected_wall)


def test_floor_init_raises_value_error_for_shape_mismatch():
    """
    testuje czy inicjalizacja Floor podnosi ValueError przy niezgodnych
    kształtach macierzy
    """

    wall = np.zeros((2, 2))
    router = np.zeros((3, 3))
    cover = np.zeros((2, 2))
    with pytest.raises(ValueError):
        dm.Floor(wall_matrix=wall,
                 router_matrix=router,
                 cover_matrix=cover,
                 Floor_number=1,
                 Floor_thickness=3.5)


def create_building():
    """
    funkcja pomocnicza tworząca przykładowy budynek do testów
    """
    floor1 = create_floor()
    floor2 = create_floor2()
    floor3 = create_floor()

    floor2.Floor_number = 1
    floor3.Floor_number = 2
    return dm.Building(Floors=[floor1, floor2, floor3], Floor_heights = 3)


@pytest.mark.parametrize("floor_count", [0, 1, 2, 3])
def test_building_initialization_various_floor_counts(floor_count):
    floors = []
    for idx in range(floor_count):
        floor = create_floor()
        floor.Floor_number = idx
        floor.Floor_thickness = 3 + idx
        floors.append(floor)

    floor_heights = 3;
    building = dm.Building(Floors =floors , Floor_heights=floor_heights)

    assert isinstance(building, dm.Building)
    assert len(building.Floor_list) == floor_count
    if floor_count:
        assert building.Floor_list[0].Floor_number == 0
        assert building.Floor_list[-1].Floor_number == floor_count - 1

def test_router_possible_collects_all_allowed_positions_dummy():
    building = dm.Building(Floors=[create_floor()], Floor_heights=3)
    positions = [(pos.x, pos.y, pos.Floor_number) for pos in building.router_possible]

    assert positions == [
        (0, 1, 0),
        (1, 0, 0),
        (1, 1, 0),
        (1, 2, 0),
    ]


def test_points_to_calculate_collects_all_cover_points_dummy():
    building = dm.Building(Floors=[create_floor()], Floor_heights=3)
    points = building.points_to_calculate

    assert len(points) == 4
    expected = {(0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 2, 0)}
    observed = {(p.x, p.y, p.Floor_number) for p in points}
    assert observed == expected


def test_router_possible_collects_all_allowed_positions():
    building = create_building()
    positions = [(pos.x, pos.y, pos.Floor_number) for pos in building.router_possible]

    assert positions == [
        (0, 1, 0),
        (1, 0, 0),
        (1, 1, 0),
        (1, 2, 0),
        (1, 0, 1),
        (1, 1, 1),
        (1, 2, 1),
        (0, 1, 2),
        (1, 0, 2),
        (1, 1, 2),
        (1, 2, 2),
    ]


def test_points_to_calculate_collects_all_cover_points():
    building = create_building()
    points = building.points_to_calculate

    expected = {
        (0, 0, 0), (0, 1, 0), (1, 1, 0), (1, 2, 0),
        (1, 0, 1), (1, 1, 1), (1, 2, 1),
        (0, 0, 2), (0, 1, 2), (1, 1, 2), (1, 2, 2),
    }
    observed = {(p.x, p.y, p.Floor_number) for p in points}

    assert observed == expected
    assert len(points) == len(expected)


def test_vertical_distance_handles_various_floors():
    building = create_building()
    assert building.vertical_distance(0, 0) == pytest.approx(0.0)
    assert building.vertical_distance(0, 1) == pytest.approx(6.0)
    assert building.vertical_distance(1, 2) == pytest.approx(7.0)
    assert building.vertical_distance(0, 2) == pytest.approx(13.0)


def test_point_distance_same_and_different_floors():
    building = create_building()
    p1 = dm.Point(0, 0, 0)
    p2 = dm.Point(3, 4, 0)
    assert building.point_distance(p1, p2) == pytest.approx(5.0)

    p3 = dm.Point(0, 0, 2)
    assert building.point_distance(p1, p3) == pytest.approx(13.0)

    p4 = dm.Point(1, 2, 1)
    expected = (1**2 + 2**2 + building.vertical_distance(0, 1)**2) ** 0.5
    assert building.point_distance(p1, p4) == pytest.approx(expected)


