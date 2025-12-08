import data_matrices as dm
import numpy as np
from typing import Tuple, List


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


def local_change(solution: List[int]) -> List[List[int]]:
    """
    Przesuwa jeden losowy router na losową wolną pozycję.
    
    Returns:
        Nowe rozwiązanie z jednym routerem w nowej pozycji.
    """
    num_possible = len(solution)
    router_positions = [i for i, val in enumerate(solution) if val > 0]
    
    if not router_positions:
        return solution.copy()
    
    # Losowy router do przesunięcia
    pos = np.random.choice(router_positions)
    router_id = solution[pos]
    
    # Losowa wolna pozycja
    free_positions = [i for i in range(num_possible) if solution[i] == 0]
    if not free_positions:
        return solution.copy()
    
    neighbor_pos = np.random.choice(free_positions)
    
    new_solution = solution.copy()
    new_solution[pos] = 0
    new_solution[neighbor_pos] = router_id
    
    return new_solution

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

    


