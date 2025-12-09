import data_matrices as dm
import numpy as np
from typing import Tuple, List

FLOOR_DAMPING_PARAM = 2.0  #przykładowa wartość tłumienia podłogi między piętrami
TABU_LIST_LENGTH = 10  # przykładowa długość tabu listy
MAX_ITERATIONS = 100  # przykładowa maksymalna liczba iteracji tabu search

def euclidean_distance(point1: np.ndarray, point2: np.ndarray) -> float:
    return np.sqrt(np.sum((point1 - point2) ** 2))

def goal_function(building: dm.Building, ranges_matrix: np.ndarray) -> float:
    """
    Liczy całościową funkcję celu z uwzglednieniem wag w punktach (building.cover)

    Args:
        building (dm.Building): budynek
        ranges_matrix (np.ndarray): siatka zasięgów
        
    Returns:
        goal_func_value (float): wartośc funkcji celu
    """
    # NARAZIE POMIJAM ILOSC PIĘTER WYSTACZY DODAC FOR PO PIĘTRACH POTEM
    return np.sum(building.cover * ranges_matrix)

def constructive_change(building: dm.Building, current_solution: List[int], router_usefullnes: List[int]) -> List[int]:
    #TODO
    """
    Funkcja realizująca konstruktywną zmianę w rozmieszczeniu ruterów - liczy użyteczność routerów (ilość obsługiwanych punktów)
    (#TODO potzebna modifikacja goal function)

    args:
    building


    Returns:
    całe nowe rozwiązanie czyli (zobacz w tabu_search) listę indeksów rozmieszczenia ruterów
    """
    pass

    


