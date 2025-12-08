import data_matrices as dm
import numpy as np
from typing import Tuple, List

FLOOR_DAMPING_PARAM = 2.0  #przykładowa wartość tłumienia podłogi między piętrami

# funkcja celu pomocnicza wyliczana w punkcie
def goal_function_point(building: dm.Building, point: dm.Point, router: dm.Point, router_power: float = 0) \
     -> float:
    """
    dostaje building i punkt obliczeń i router od którego liczymy
    liczymy w decybelach zatem logarytmy zwraca w dB
    dostaje building i punnkt i liczy wartosc zasiegu w punkcie
    """ 
    
    distance = building.get_distance(point, router)
    if distance == 0:
          raise ValueError("Distance between point and router cannot be zero.")
    
    damping = building.get_damping(point, router, FLOOR_DAMPING_PARAM)
    
    # Przykładowa formuła na sygnał w dB
    signal_db = - (20 * np.log10(distance) + damping) + router_power

    # TODO trzeba uwzględnić jeszcze jaki to jest router o jakiej mocy!
    # czyli po prostu dodać do signal_db wartość mocy routera w dB
    
    return signal_db
    
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
    
    # NARAZIE POMIJAM ILOSC PIĘTER WYSTACZY DODAC FOR PO PIĘTRACH POTEM
    pietro =  building.Floor_list[0]
    H, W = pietro.wall.shape
    
    global_map = np.zeros((H, W), dtype=float)
    
    for local_grid, (start_row, start_col) in local_ranges:
        # Wymiary małego wycinka
        h_local, w_local = local_grid.shape

        # Sprawdzamy, gdzie wycinek realnie zaczyna się i kończy na mapie globalnej
        global_r_start = max(0, start_row)
        global_r_end = min(H, start_row + h_local)
        global_c_start = max(0, start_col)
        global_c_end = min(W, start_col + w_local)

        # Sprawdzamy, które fragmenty wycinka lokalnego odpowiadają tym zakresom
        # (Jeśli start_row < 0, musimy uciąć początek wycinka lokalnego)
        local_r_start = global_r_start - start_row
        local_r_end = local_r_start + (global_r_end - global_r_start)
        local_c_start = global_c_start - start_col
        local_c_end = local_c_start + (global_c_end - global_c_start)
    
        # Jeśli wycinek jest całkowicie poza mapą, pomijamy
        if global_r_start >= global_r_end or global_c_start >= global_c_end:
            continue

        # Bierzemy max z tego co już jest na mapie vs nowy wycinek
        current_slice = global_map[global_r_start:global_r_end, global_c_start:global_c_end]
        new_slice = local_grid[local_r_start:local_r_end, local_c_start:local_c_end]
        
        global_map[global_r_start:global_r_end, global_c_start:global_c_end] = np.maximum(current_slice, new_slice)

    return global_map
    

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


"""
2 warianty:
- liczysz wszystko
- próbujuesz przyspieszyć liczenie z thresholdem - czyli tylko stosunkowo bliskie
- ewentualnie inny sposób na ułatwienie oblieczeń
"""
