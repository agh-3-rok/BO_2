import data_matrices as dm
import numpy as np
from typing import Tuple, List


def local_router_range(building: dm.Building, router_point: dm.Point, R_max: int) -> Tuple[np.ndarray, dm.Point]:
    """
    Oblicza zasięg od pojedynczego ruter, w jego istotnym otoczeniu. Wartości oblicza się w dB
    
    Args:
        building (dm.Building): budynek
        router_point (dm.Point): punkt w którym znajduje się ruter
        R_max (int): threshold dystansu
    Returns:
        building_box (np.ndarray) - mała macierz - lokalna mapa zasięgu
        point (dm.Point) - współrzędne lewego górnego rogu lokalnej macierzy
    
    krotka z tych dwóch?
    """ 
    raise NotImplementedError


def agregation_func(building: dm.Building, local_ranges: List[Tuple[np.ndarray, dm.Point]]) -> np.ndarray:
    """
    Funkcja realizuje wzór na agregację/max sygnału, wykorzystując lokalne zasięgi od ruterów oblicza całą siatkę zasięgów.

    Args:
        building (dm.Building): budynek
        local_ranges (list): lista, krotek lokalnych zasięgów i punktów w których zaczyna się siatka
        
    Returns:
        ranges (np.ndarray): siatka zasięgów
    """
    raise NotImplementedError


def goal_function(building: dm.Building, ranges_matrix: np.ndarray) -> float:
    """
    Liczy całościową funkcję celu z uwzglednieniem wag w punktach (building.cover)

    Args:
        building (dm.Building): budynek
        ranges_matrix (np.ndarray): siatka zasięgów
        
    Returns:
        goal_func_value (float): wartośc funkcji celu
    """
    raise NotImplementedError


"""
2 warianty:
- liczysz wszystko
- próbujuesz przyspieszyć liczenie z thresholdem - czyli tylko stosunkowo bliskie
- ewentualnie inny sposób na ułatwienie oblieczeń
"""