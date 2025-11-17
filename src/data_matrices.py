
#tutaj wstawiam kilka danych 

import numpy as np
from typing import List



class floor:
    """
    obiekt przechowujący topografie daneg piętra
    zawiera:
    wall_matrix: macierz ścian (zawiera współrczynniki tłumienia potrzebne do liczenie zasięgu)
    teraz warto zawuażyć że sam krztałt budynku jak i jego pięter może byc dowolny 
    jego krztałt będzie odzwierciedlnoy w przechowwyanych macierzach
    można sobie wyobrazić że macierz ścian stanowi "pokrycie" piętra  

    router_matrix: macierz routerów (zawiera dozwolone współrzędne do stawiania routerów na danym piętrze)
    macierz binarna 0/1 gdzie 1 oznacza że można postawić routera

    cover_matrix : macierz zachowująca gdzie chcemy mieć zasięg 
    tam gdzie nie ma bydunku / lub nie chcemy mieć zasięgu dac inf ;pp   

    floor_number: numer piętra

    floor_thickness: grubość podłogi (do liczenia tłumienia między piętrami)
    """    

    def __init__(self, wall_matrix: np.ndarray, router_matrix: np.ndarray, cover_matrix: np.ndarray, floor_number: int, floor_thickness: float):

        # chcemy mieć pewność że wszystkie macierze mają ten sam rozmiar
        if wall_matrix.shape != router_matrix.shape or wall_matrix.shape != cover_matrix.shape:
            raise ValueError("Wszystkie macierze muszą mieć ten sam rozmiar.")

        self.wall = wall_matrix
        self.router = router_matrix
        self.cover = cover_matrix
        self.floor_number = floor_number # to w sumie nie jest potrzebn
        self.floor_thickness = floor_thickness

def euclidean_distance(point1: np.ndarray, point2: np.ndarray) -> float:
    return np.sqrt(np.sum((point1 - point2) ** 2))  

class building:
    # obiekt przechowujący budynek składający się z pięter
    # zawiera listę pięter

    """
    pomocnicza klasa do definicji punkty w przestrzeni budynku
    """
    class point:
        def __init__(self, x: int, y: int, floor_number: int):
            self.x = x
            self.y = y
            self.floor_number = floor_number

    def __init__(self, floors: list[floor], floor_height: float):
        self.floor_list = floors
        self.router_possible = self.__get_possible_router_positions() # od razu buduje liste możliwych pozycji routerów dla łatwiejszego dostępu
        self.points_to_calculate = self.__get_points_to_calculate() # od razu buduje liste punktów do obliczenia zasięgu dla łatwiejszego dostępu
        self.floor_height = floor_height
        

    def __get_possible_router_positions(self) -> np.ndarray:
        # zwraca macierz z możliwymi pozycjami routerów w całym budynku
        # (x, y, floor_number)
        # ta funkcja będzie ważna w celu zaimplementowanie taboo search!

        possible_positions = []
        for fl in self.floor_list:
            for x in range(fl.router.shape[0]):
                for y in range(fl.router.shape[1]):
                    if fl.router[x, y] == 1:  # zakładamy, że 1 oznacza dozwoloną pozycję
                        possible_positions.append((x, y, fl.floor_number))

        return np.array(possible_positions)


    def __get_points_to_calculate(self) -> List(point):
        # zwraca macierz z punktami do obliczenia zasięgu w całym budynku
        # (x, y, floor_number)
    
        points_to_calculate = []
        for fl in self.floor_list:
            for x in range(fl.cover.shape[0]):
                for y in range(fl.cover.shape[1]):
                    if fl.cover[x, y] == 1:  # zakładamy, że 1 oznacza punkt do obliczenia zasięgu
                        points_to_calculate.append((x, y, fl.floor_number))

        return np.array(points_to_calculate)
    
    def point_distance(self):
        pass
