import data_matrices as dm
import numpy as np
from typing import Tuple, List

FLOOR_DAMPING_PARAM = 2.0  #przykładowa wartość tłumienia podłogi między piętrami
TABU_LIST_LENGTH = 10  # przykładowa długość tabu listy
MAX_ITERATIONS = 100  # przykładowa maksymalna liczba iteracji tabu search

# funkcja celu pomocnicza wyliczana w punkcie
def goal_function_point(building: dm.Building, point: dm.Point, router: dm.Point, router_power: float = 0) \
     -> float:
    """
    dostaje building i punkt obliczeń i router od którego liczymy
    liczymy w decybelach zatem logarytmy zwraca w dB
    dostaje building i punnkt i liczy wartosc zasiegu w punkcie
    """ 
    
    distance = building.point_distance(point, router)
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
    local_router_square = np.zeros((R_max, R_max))
    
    #x, y współrzędne lewego górnego rogu 
    left_upper_x = router_point.x - R_max // 2
    left_upper_y = router_point.y - R_max // 2
    
    for i in range(R_max):
        for j in range(R_max):
            if (left_upper_x + i, left_upper_y + j) != (router_point.x, router_point.y):
                local_router_square[i, j] = 10**(goal_function_point(building, dm.Point(left_upper_x + i, left_upper_y + j, 0), router_point, 2)/10)
            else:
                local_router_square[i, j] = 3 #WARTOŚĆ SYGNAŁU W MIEJSCU RUTERA
    return local_router_square, (left_upper_x, left_upper_y)

def trnsform_current_location_into_local_ranges():
    raise NotImplementedError


def agregation_func(building: dm.Building, local_ranges: List[Tuple[np.ndarray, dm.Point]]) -> np.ndarray:
    """
    FUNKCAJ UŻYWANA PRZY INICJALIZACJI - LICZY DLA WSZYSTKICH RUTERÓW 
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


def _local_change(solution: List[int]) -> List[List[int]]:
    """
    Generuje sąsiedztwo poprzez lokalne zmiany.
    
    Typy ruchów:
    - Przesunięcie routera do sąsiedniej pozycji
    - Zamiana pozycji dwóch routerów
    """
    neighborhood = []
    num_possible = len(solution)
    
    # znajdź pozycje z routerami
    router_positions = [i for i, val in enumerate(solution) if val > 0]
    
    # przesuń każdy router do wolnej pozycji
    for pos in router_positions:
        router_id = solution[pos]
        
        #sprawdź wszystkie wolne pozycje
        for neighbor_pos in range(num_possible):
            if solution[neighbor_pos] == 0:  # wolna pozycja
                new_solution = solution.copy()
                new_solution[pos] = 0
                new_solution[neighbor_pos] = router_id
                neighborhood.append(new_solution)
    
    # zamień pozycje dwóch routerów
    for i, pos1 in enumerate(router_positions):
        for pos2 in router_positions[i+1:]:
            new_solution = solution.copy()
            new_solution[pos1], new_solution[pos2] = new_solution[pos2], new_solution[pos1]
            neighborhood.append(new_solution)
    
    return neighborhood

def aspiration_criteria(neighbor, best_value, best_solution) -> bool:
    #TODO
    """
    Funkcja realizująca kryterium aspiracji w algorytmie tabu search

    Returns:
    nie wiem w sumie XD -> np z tym lepszy od najlepszego znalezionego czy cos takiego
    """
    pass

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

def tabu_search(building: dm.Building, available_routers: list[dm.Router], tabu_length: int = TABU_LIST_LENGTH) -> Tuple[List[dm.Point], float] :
    """
    Realizuje algorytm tabu search dla optymalizacji rozmieszczenia ruterów w budynku

    Args:
        building (dm.Building): budynek
        available_routers (list): lista dostępnych ruterów do rozmieszczenia
        długość tabu listy (int)
    Returns:
        best_routers (list): najlepsze znalezione pozycje ruterów
        best_goal_value (float): wartość funkcji celu dla najlepszych pozycji
        potencjalnie inne rzeczy do rysowania wykresów itp
    """
    
    num_available_routers = len(available_routers) # liczba dostępnych ruterów

    # rozwiązanie to ciag 0 i indeksów w lidscię available_routers (początkowo pełna 0)
    # każdy indeks odpowiada pozycji w dm.Building.router_possible -> czyli potencjalne miejsca na ruter
    best_solution = [0]*len(dm.Building.router_possible) 

    # inicjalizacja tabu listy -> do niej będą wkładane zabronione ruchy
    tabu_list = []

    # generujemy początkowe rozwiązanie
    #TODO - ogarnąć jak to chcemy robić -> dużo opcji można np. losowo
    current_solution = initial_solution(building, available_routers)
    # akutalnie jest to najlepsze rozwiązanie
    best_solution = current_solution.copy()
    best_value, _ = goal_function(building, current_solution) # TODO - ta funkcja ma dostawać building i rozwiązanie...

    for i in range(MAX_ITERATIONS):
        #TODO
        # generowanie sąsiedztwa
        neighborhood = local_change(current_solution, available_routers)

        # wybór najlepszego ruchu z sąsiedztwa nie będącego w tabu liście
        for neighbor in neighborhood:
            not_in_tabu = neighbor not in tabu_list

            if not_in_tabu or aspiration_criteria(neighbor, best_value, best_solution): # liczy wartość funkcji celu dla tego sąsiada

                neighbor_value = goal_function(building, neighbor) # TODO - ta funkcja ma dostawać building i rozwiązanie...

                # sprawdź czy jest lepszy od najlepszego znalezionego
                if neighbor_value > best_value:

                    # aktualizacja rozwiązania
                    best_solution = neighbor
                    best_value = neighbor_value

                    # dodaj ruch do tabu listy

                    tabu_list.append(neighbor)
                    if len(tabu_list) > tabu_length:
                        tabu_list.pop(0)  # usuwamy najstarszy ruch z tabu listy
            

        """
        w modyfikacji taboo search funkcja może robić jesze konstrukwne zmiany co jakiś czas
        
        current_solution = constructive_change(building, best_solution)

        """

        # aktualizacja bieżącego rozwiązania
        current_solution = best_solution.copy()

    return best_solution, best_value

    


