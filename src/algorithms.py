import numpy as np
from typing import List, Tuple, Optional
import random
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
        # p=probs - Funkcja nie traktuje każdego indeksu równo. Indeks z wagą 10 ma 10 razy większą szansę bycia wylosowanym niż indeks z wagą 1.
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
    
    def smart_local_change(self) -> Optional[Tuple[int, int, int]]:
        """
        1. Znajduje jeden z najmniej przydatnych routerów.
        2. Znajduje dla niego nowe, losowe miejsce (preferując te z wysokim cover).
        3. Zwraca instrukcję ruchu: (id_routera, stara_pozycja, nowa_pozycja).
        NIE MODYFIKUJE STANU.
        """
        # Policz przydatność każdego routera
        usefulness_scores = self.building.calculate_router_usefulness()
        
        active_routers = []
        for pos_idx, r_id in enumerate(self.current_solution):
            if r_id != -1:
                # Pobierz wynik routera (zabezpieczenie indeksu)
                score = usefulness_scores[r_id] if r_id < len(usefulness_scores) else 0
                active_routers.append({'pos': pos_idx, 'id': r_id, 'score': score})
        
        if not active_routers:
            return None

        # Wybierz kandydata do ruchu (jeden z 2 najgorszych)
        active_routers.sort(key=lambda x: x['score'])
        n_candidates = min(2, len(active_routers)) 
        candidate = active_routers[random.randint(0, n_candidates - 1)]
        
        router_id = candidate['id']
        old_pos_idx = candidate['pos']
        
        # Wybierz nowe miejsce (Celujemy w High Priority)
        indices, probs = self.high_priority_indices
        
        if not indices: # Fallback
             indices = list(range(len(self.current_solution)))
             probs = None

        new_pos_idx = old_pos_idx
        # Próbujemy 10 razy wylosować WOLNE miejsce
        for _ in range(10):
            try_idx = np.random.choice(indices, p=probs)
            if self.current_solution[try_idx] == -1: # Jeśli wolne
                new_pos_idx = try_idx
                break
        
        # Jeśli nie trafiliśmy w wolne priorytetowe, bierzemy losowe wolne z całej mapy
        if new_pos_idx == old_pos_idx:
            free_slots = [i for i, v in enumerate(self.current_solution) if v == -1]
            if free_slots:
                new_pos_idx = random.choice(free_slots)
            else:
                return None # Brak miejsca na ruch

        return (router_id, old_pos_idx, new_pos_idx)
    
    def _apply_move(self, router_id, old_pos, new_pos):
        """Wykonuje ruch: aktualizuje tablicę solution oraz fizyczną pozycję routera."""
        self.current_solution[old_pos] = -1
        self.current_solution[new_pos] = router_id
        
        # Przestaw router fizycznie i przelicz zasięg
        new_point = self.building.router_possible[new_pos]
        self.available_routers[router_id].position = new_point
        self.available_routers[router_id].calculate_coverage(self.building)
    
    def _revert_move(self, router_id, old_pos, new_pos):
        """Cofa ruch: przywraca router na stare miejsce."""
        self.current_solution[new_pos] = -1
        self.current_solution[old_pos] = router_id
        
        # Przestaw router z powrotem fizycznie
        old_point = self.building.router_possible[old_pos]
        self.available_routers[router_id].position = old_point
        self.available_routers[router_id].calculate_coverage(self.building)

    def _are_routers_separated(self) -> bool:
        """
        Zwraca True tylko wtedy, gdy KAŻDA para routerów jest oddalona o min_distance.
        Szybki "fail-fast" - przerywa przy pierwszej kolizji.
        """
        active_routers = [r for r in self.available_routers if r.position is not None]
        count = len(active_routers)
        
        # Iterujemy po parach, żeby sprawdzić odległość
        for i in range(count):
            for j in range(i + 1, count):
                p1 = active_routers[i].position
                p2 = active_routers[j].position
                
                # Używamy metody z Building do liczenia dystansu
                dist = self.building.point_distance(p1, p2)
                
                if dist < self.min_distance:
                    return False 
        
        return True 
    
    def run(self) -> Tuple[List[int], float, dict, int]:
        """Główna pętla algorytmu."""
        
        # Start (jeśli nie wywołano wcześniej init)
        if self.current_solution is None:
            self.weighted_random_initial_solution()
            
        print(f"Start Value: {self.best_value:.2f}")

        aspiration_cnt = 0
        
        # Główna pętla
        for iteration in range(self.max_iterations):
            
            move = self.smart_local_change()
            if move is None:
                continue
                
            r_id, old_p, new_p = move
            
            # wykonanie ruchu
            self._apply_move(r_id, old_p, new_p)
            current_val = self.evaluate_solution()
            
            # sprawdzenie czy rutery są wystarczająco daleko od siebie
            is_separated = self._are_routers_separated()
            
            # sprawdzenie w tabu
            solution_signature = tuple(self.current_solution) # Krotka jest hashowalna
            is_tabu = solution_signature in self.tabu_list
            
            # ocena rozwiązania
            accept = False
            
            if not is_separated:
                # routery są za blisko.
                accept = False
            elif not is_tabu:
                accept = True
            elif current_val > self.best_value:
                # TODO: Inne kryterium aspiracji dodać
                accept = True
                aspiration_cnt += 1
            
            if accept:
                #ruch przyjęty
                self.tabu_list.append(solution_signature)
                if len(self.tabu_list) > self.tabu_length:
                    self.tabu_list.pop(0)
                
                # zmiana najlepszego rozwiązania
                if current_val > self.best_value:
                    self.best_solution = list(self.current_solution)
                    self.best_value = current_val
            else:
                # ruch odrzucony
                # cofanie zmiany
                self._revert_move(r_id, old_p, new_p)
                
                # przywrócenie current_value do wykresików
                if self.history['current_values']:
                    current_val = self.history['current_values'][-1]
                else:
                    current_val = self.best_value

            # Logowanie
            self.history['iterations'].append(iteration)
            self.history['best_values'].append(self.best_value)
            self.history['current_values'].append(current_val)

        # ustawienie rozwiązania na najlepsze
        self.current_solution = list(self.best_solution)
        
        # Reset i ustawienie
        for r in self.available_routers:
            r.position = None
            r.coverage_grid = None
            
        for pos_idx, r_id in enumerate(self.best_solution):
            if r_id != -1:
                pt = self.building.router_possible[pos_idx]
                self.available_routers[r_id].position = pt
                self.available_routers[r_id].calculate_coverage(self.building)

        return self.best_solution, self.best_value, self.history, aspiration_cnt
    