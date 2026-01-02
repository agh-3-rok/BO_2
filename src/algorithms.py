import numpy as np
from typing import List, Tuple
import random

# IMPORTUJEMY klasy z pliku models.py
from data_matrices import Building, Router

class TabuSearch:
    """
    Algorytm Tabu Search dla optymalizacji rozmieszczenia routerów w budynku.
    """

    def __init__(
        self,
        building: Building,
        available_routers: List[Router],
        tabu_length: int = 10,
        max_iterations: int = 100,
    ):
        """
        Args:
            building: obiekt budynku z piętrami i możliwymi pozycjami routerów
            available_routers: lista dostępnych routerów do rozmieszczenia
            tabu_length: długość listy tabu
            max_iterations: maksymalna liczba iteracji
        """
        self.building = building
        self.available_routers = available_routers
        self.tabu_length = tabu_length
        self.max_iterations = max_iterations
        
        # Stan algorytmu
        self.tabu_list = []
        self.current_solution = None
        self.best_solution = None
        self.best_value = float('-inf')
        
        # Historia dla analizy/wykresów
        self.history = {
            'iterations': [],
            'best_values': [],
            'current_values': []
        }
        
        self.high_priority_indices = self._get_high_priority_indices()
        
    def initial_solution(self):
        """
        funkcja generująca początkowe rozwiązanie dla tabu search (np. losowe)
            [(1, 1, 1), (6, 1, 1), (6, 6, 1)] - możliwe pozycje dla ruterów
            [0, 1, -1] - na pozycji (1,1,1) - ruter0, na pozycji (6,1,1) - ruter1, na pozycji (6,6,1) - brak rutera
        """

        num_possible_positions = len(self.building.router_possible)
        num_available_routers = len(self.available_routers)

        # Inicjalizacja rozwiązania z samymi zerami
        solution = [-1] * num_possible_positions

        # Losowe rozmieszczenie ruterów
        chosen_positions = np.random.choice(
            num_possible_positions, num_available_routers, replace=False
        )
        router_num = 0
        for pos in chosen_positions:
            solution[pos] = router_num  # Oznaczamy miejsce jako zajęte przez ruter
            self.available_routers[router_num].position = self.building.router_possible[pos] # Przypisuje dp rutera jego pozycję
            self.available_routers[router_num].calculate_coverage(self.building) #Oblicza kratkę od rutera, przy rozwiązaniu początkowym
            router_num += 1
        

        self.current_solution = solution
        
    def _get_high_priority_indices(self):
        """
        Tworzy listę indeksów z mapy router_possible, gdzie cover > 0.
        Służy do szybkiego losowania 'sensownych' miejsc zamiast strzelania w puste korytarze.
        """
        indices = []
        weights = []
        
        pietro = self.building.Floor_list[0] # Uproszczenie dla 1 piętra
        possible_pts = self.building.router_possible
        
        for i, pt in enumerate(possible_pts):
            # Sprawdź wagę w tym punkcie
            w = pietro.cover[pt.x, pt.y]
            if w > 0:
                indices.append(i)
                weights.append(w)
        
        # Normalizacja wag do prawdopodobieństwa
        total_w = sum(weights)
        probs = [w / total_w for w in weights] if total_w > 0 else None
        
        return indices, probs

    def weighted_random_initial_solution(self):
        """
        NOWE PODEJŚCIE: Losuje pozycje, ale z większym prawdopodobieństwem
        tam, gdzie waga 'cover' jest duża. Szybkie i daje niezły start.
        """
        num_routers = len(self.available_routers)
        indices, probs = self.high_priority_indices
        
        # Reset
        for r in self.available_routers:
            r.position = None
            r.coverage_grid = None
        
        # Losujemy N unikalnych pozycji na podstawie wag priorytetów
        # replace=False zapewnia brak duplikatów
        chosen_indices = np.random.choice(indices, num_routers, replace=False, p=probs)
        
        # Budujemy wektor rozwiązania
        total_slots = len(self.building.router_possible)
        solution = [-1] * total_slots
        
        for r_idx, map_idx in enumerate(chosen_indices):
            solution[map_idx] = r_idx
            self.available_routers[r_idx].position = self.building.router_possible[map_idx]
            self.available_routers[r_idx].calculate_coverage(self.building)
            
        self.current_solution = solution
        self.best_solution = solution.copy()
        self.best_value = self.evaluate_solution()
        
    
    def evaluate_solution(self) -> float:
        """
        Oblicza wartość funkcji celu dla bieżącego rozwiązania.
        
        Kroki:
        1. Użyć agregation_func do stworzenia globalnej mapy zasięgu
        2. Obliczyć wartość funkcji celu (suma iloczynów zasięgu i wag cover)
        
        Returns:
            wartość funkcji celu
        """
        # Agreguj zasięgi wszystkich routerów
        ranges_matrix = self.building.agregation_func(self.available_routers)
        
        # Oblicz funkcję celu: suma iloczynów zasięgu * wagi cover
        pietro = self.building.Floor_list[0]
        goal_value = np.sum(pietro.cover * ranges_matrix)
        
        return goal_value
    
    def aspiration_criteria(self, neighbor_solution: List[int]) -> bool:
        """
        Kryterium aspiracji - pozwala na ruch tabu jeśli jest lepszy od najlepszego.
        
        Args:
            neighbor_solution: rozwiązanie sąsiednie do oceny (lista indeksów routerów)
            
        Returns:
            True jeśli neighbor jest lepszy od best_value (pozwól na ruch mimo tabu)
        """
        # Tymczasowo ustaw pozycje routerów zgodnie z neighbor_solution
        old_positions = [r.position for r in self.available_routers]
        
        # Ustaw nowe pozycje i przelicz coverage
        for i, router_idx in enumerate(neighbor_solution):
            if router_idx >= 0:  # Router przypisany do tej pozycji
                self.available_routers[router_idx].position = self.building.router_possible[i]
                self.available_routers[router_idx].calculate_coverage(self.building)
        
        # Oceń rozwiązanie
        neighbor_value = self.evaluate_solution()
        
        # Przywróć stare pozycje
        for i, router in enumerate(self.available_routers):
            router.position = old_positions[i]
            if old_positions[i] is not None:
                router.calculate_coverage(self.building)
        
        return neighbor_value > self.best_value
    
    def local_change(self):
        """
        Przesuwa jeden losowy router na losową wolną pozycję.
        Aktualizuje router.position, przelicza coverage i przypisuje do self.current_solution.
        
        Returns:
            Nowe rozwiązanie z jednym routerem w nowej pozycji.
        """
        num_possible = len(self.current_solution)
        # Znajdź pozycje z routerami (wartość >= 0)
        router_positions = [i for i, val in enumerate(self.current_solution) if val >= 0]
        
        if not router_positions:
            return self.current_solution.copy()
        
        # Losowy router do przesunięcia
        pos = np.random.choice(router_positions)
        router_id = self.current_solution[pos] #ruter_id to numer rutera na liście self.available_routers
        
        # Znajdź wolne pozycje (wartość == -1)
        free_positions = [i for i in range(num_possible) if self.current_solution[i] == -1]
        if not free_positions:
            return self.current_solution.copy()
        
        neighbor_pos = np.random.choice(free_positions)
        
        new_solution = self.current_solution.copy()
        new_solution[pos] = -1  # Stara pozycja staje się wolna
        new_solution[neighbor_pos] = router_id  # Nowa pozycja dostaje routera
        
        # Zaktualizuj pozycję routera
        self.available_routers[router_id].position = self.building.router_possible[neighbor_pos]
        
        # Przelicz kratkę zasięgu dla zmienionego routera
        self.available_routers[router_id].calculate_coverage(self.building)
        
        # Przypisz nowe rozwiązanie do current_solution
        self.current_solution = new_solution
        return new_solution
  
    def smart_local_change(self):
        """
        Generuje jednego sąsiada:
        1. Liczy użyteczność routerów.
        2. Wybiera jednego z najgorszych (żeby spróbować go poprawić).
        3. Przesuwa go w losowe wolne miejsce.
        """
        # 1. Obliczamy, jak przydatny jest każdy router w obecnym układzie
        # (Zwraca listę floatów, gdzie indeks to ID routera)
        usefulness_scores = self.building.calculate_router_usefulness()
        
        # 2. Tworzymy listę aktywnych routerów wraz z ich wynikami i pozycjami
        active_routers = []
        for pos_idx, router_id in enumerate(self.current_solution):
            if router_id != -1:
                # Pobieramy wynik dla tego routera (zabezpieczenie przed błędem indeksu)
                score = usefulness_scores[router_id] if router_id < len(usefulness_scores) else 0.0
                active_routers.append({'pos_idx': pos_idx, 'router_id': router_id, 'score': score})
        
        # Zabezpieczenie: jeśli nie ma routerów na planszy, zwracamy to co mamy
        if not active_routers:
            return self.current_solution.copy()

        # 3. Sortujemy rosnąco (najgorsze wyniki na początku)
        active_routers.sort(key=lambda x: x['score'])
        
        # 4. Wybieramy kandydata do przesunięcia.
        # WAŻNE: Nie bierzemy zawsze indexu [0] (najgorszego), bo algorytm wpadnie w pętlę.
        # Losujemy jednego z 3 najgorszych. To daje algorytmowi "oddech".
        import random
        n_worst = min(3, len(active_routers))
        candidate = active_routers[random.randint(0, n_worst - 1)]
        
        old_pos_idx = candidate['pos_idx']
        router_id = candidate['router_id']
        
        # 5. Znajdujemy wolne miejsca na mapie
        free_indices = [i for i, val in enumerate(self.current_solution) if val == -1]
        
        # Jeśli nie ma gdzie przesunąć, zwracamy bez zmian
        if not free_indices:
            return self.current_solution.copy()
            
        # Losujemy nowe miejsce
        new_pos_idx = random.choice(free_indices)
        
        # 6. Tworzymy nowe rozwiązanie (wektor)
        new_solution = self.current_solution.copy()
        new_solution[old_pos_idx] = -1      # Stare miejsce zwalniamy
        new_solution[new_pos_idx] = router_id # Nowe miejsce zajmujemy
        
        # 7. AKTUALIZACJA FIZYCZNA ROUTERA
        # Musimy zaktualizować obiekt routera, żeby calculate_coverage policzyło nowy zasięg
        new_point = self.building.router_possible[new_pos_idx]
        self.available_routers[router_id].position = new_point
        self.available_routers[router_id].calculate_coverage(self.building)
        
        # Aktualizujemy stan w obiekcie TabuSearch
        self.current_solution = new_solution
        
        return new_solution       
    
    def run(self) -> Tuple[List[int], float, dict]:
        """
        Uruchamia algorytm Tabu Search.
        
        Returns:
            (best_solution, best_value, history)
        """
        # print("=== Start Tabu Search ===")
        # self.greedy_initial_solution(step)
        aspiration_criteria_counter = 0
        for iteration in range(self.max_iterations):
            # Generuj sąsiada
            neighbor = self.smart_local_change()
            
            # Oceń sąsiada
            neighbor_value = self.evaluate_solution()
            
            # Sprawdź czy jest w tabu
            is_tabu = neighbor in self.tabu_list
            
            # Oceń czy zaakceptować (nie w tabu ALBO spełnia aspirację)
            accept = False
            if not is_tabu:
                accept = True
            elif self.aspiration_criteria(neighbor):
                aspiration_criteria_counter += 1
                accept = True
            
            if accept:
                # Dodaj do tabu listy
                self.tabu_list.append(neighbor.copy())
                if len(self.tabu_list) > self.tabu_length:
                    self.tabu_list.pop(0)
                
                # Aktualizuj najlepsze rozwiązanie
                if neighbor_value > self.best_value:
                    self.best_solution = neighbor.copy()
                    self.best_value = neighbor_value
            else:
                # Cofnij zmianę (przywróć poprzednie rozwiązanie)
                # Trzeba znaleźć router który się zmienił i cofnąć
                for i in range(len(self.current_solution)):
                    if self.current_solution[i] != neighbor[i]:
                        # Znaleziony zmieniony router
                        router_id = self.current_solution[i]
                        if router_id >= 0:
                            # Przywróć starą pozycję
                            for j in range(len(self.current_solution)):
                                if neighbor[j] == router_id and i != j:
                                    self.available_routers[router_id].position = self.building.router_possible[i]
                                    self.available_routers[router_id].calculate_coverage(self.building)
                                    break
                        break
                self.current_solution = self.best_solution.copy()
            
            # Zapisz historię
            self.history['iterations'].append(iteration + 1)
            self.history['best_values'].append(self.best_value)
            self.history['current_values'].append(neighbor_value)
            
        #     if (iteration + 1) % 10 == 0:
        #         print(f"Iteracja {iteration + 1}/{self.max_iterations}, Best: {self.best_value:.2f}")
        
        # print(f"\n=== Koniec ===")
        # print(f"Najlepsza wartość: {self.best_value:.2f}")
        
        return self.best_solution, self.best_value, self.history, aspiration_criteria_counter
        
    