# tutaj wstawiam kilka danych

import numpy as np
from typing import List


class Floor:
    """Przechowuje topografię pojedynczego piętra.

    Atrybuty:
    - `wall_matrix` (`np.ndarray` float): macierz współczynników tłumienia. Wartości
        bliskie 0.0 oznaczają brak przeszkody, większe wartości odpowiadają
        ścianom lub innym elementom tłumiącym. Macierz odzwierciedla kształt
        i rozkład przeszkód na piętrze.
    - `router_matrix` (`np.ndarray` bool): macierz pozycji, gdzie można ustawić router
        (True = pozycja dozwolona, False = niedozwolona).
    - `cover_matrix` (`np.ndarray` int): macierz punktów do pokrycia zasięgiem.
        0-5 jak bardzo chcemy zasięg w punkcie,
        `-1` = poza budynkiem / niedostępny.
    - `Floor_number` (int): numer piętra.
    - `Floor_thickness` (float): grubość stropu/podłogi, używana przy obliczaniu
        tłumienia sygnału między piętrami.

    Uwaga: wszystkie macierze (`wall`, `router`, `cover`) muszą mieć ten sam rozmiar.
    """

    def __init__(
        self,
        wall_matrix: np.ndarray,
        router_matrix: np.ndarray,
        cover_matrix,
        Floor_number: int,
        Floor_thickness: float,
    ):

        # chcemy mieć pewność że wszystkie macierze mają ten sam rozmiar
        if (
            wall_matrix.shape != router_matrix.shape
            or wall_matrix.shape != cover_matrix.shape
        ):
            raise ValueError("Wszystkie macierze muszą mieć ten sam rozmiar.")

        self.wall = wall_matrix
        self.router = router_matrix
        self.cover = cover_matrix
        self.Floor_number = Floor_number  # to w sumie nie jest potrzebn
        self.Floor_thickness = Floor_thickness


def euclidean_distance(point1: np.ndarray, point2: np.ndarray) -> float:
    return np.sqrt(np.sum((point1 - point2) ** 2))


class Point:
    def __init__(self, x: int, y: int, Floor_number: int):
        self.x = x
        self.y = y
        self.Floor_number = Floor_number

    def __repr__(self):
        return f"{self.x, self.y, self.Floor_number}"


class Building:
    # obiekt przechowujący budynek składający się z pięter
    # zawiera listę pięter

    # class Point:
    #     """
    #     pomocnicza klasa do definicji punkty w przestrzeni budynku
    #     """
    #     def __init__(self, x: int, y: int, Floor_number: int):
    #         self.x = x
    #         self.y = y
    #         self.Floor_number = Floor_number

    def __init__(self, Floors: list[Floor], Floor_heights: float):
        self.Floor_list = Floors
        self.router_possible = (
            self.__get_possible_router_positions()
        )  # od razu buduje liste możliwych pozycji routerów dla łatwiejszego dostępu
        self.points_to_calculate = (
            self.__get_points_to_calculate()
        )  # od razu buduje liste punktów do obliczenia zasięgu dla łatwiejszego dostępu
        self.Floor_heights = Floor_heights

    def __get_possible_router_positions(self) -> List:
        """
        Zwraca listę krotek (x, y, Floor_number) z możliwymi pozycjami routerów w całym budynku
        """
        possible_positions = []
        for fl in self.Floor_list:
            for x in range(fl.router.shape[0]):
                for y in range(fl.router.shape[1]):
                    if (
                        fl.router[x, y] == 1
                    ):  # zakładamy, że 1 oznacza dozwoloną pozycję
                        possible_positions.append((x, y, fl.Floor_number))

        return possible_positions

    def __get_points_to_calculate(self) -> list[Point]:
        """
        Zwraca listę punktów do obliczenia zasięgu w całym budynku
        """
        points_to_calculate = []
        for fl in self.Floor_list:
            for x in range(fl.cover.shape[0]):
                for y in range(fl.cover.shape[1]):
                    if (
                        fl.cover[x, y] != 0
                    ):  # zakładamy, że jęśli nie ma tam 0 to oznacza, że w punkcie nalezy obliczyć zasięg
                        points_to_calculate.append(Point(x, y, fl.Floor_number))

        return points_to_calculate

    def point_distance(point1: Point, point2: Point) -> float:
        # TODO
        """
        metoda licząca dystans międz puntkuami w budynku
        """
        pass

    def get_damping(p1: Point, p2: Point) -> float:
        # TODO
        """
        metoda licząca tłumienie między piętrami
        Bresenham's line algorithm może być pomocny
        """
        pass
