import numpy as np
from typing import List, Tuple, Optional, Any
import random
from data_matrices import Building, Router
from config import SimulationConfig
from enums import TabuStrategy, AspirationStrategy, InitialSolutionStrategy, LocalChangeStrategy

class TabuSearch:
    """
    Algorytm Tabu Search dla optymalizacji rozmieszczenia routerów w budynku.
    """

    def __init__(
        self,
        building: Building,
        available_routers: List[Router],
        config: SimulationConfig
    ):
        """
            building: obiekt budynku z piętrami i możliwymi pozycjami routerów
            available_routers: lista dostępnych routerów do rozmieszczenia
            tabu_length: długość listy tabu
            max_iterations: maksymalna liczba iteracji
            min_distance: minimalna odległość między ruterami
            tabu_strategy: strategia w jakis sposób działa lista tabu
            aspiration_strategy: strategia kryterium aspiracji
            init_strategy: pozwala wybrać jak zostanie zainicjlaizowane rozwiązanie
            local_change_strategy: pozwala wybrać jak będzie wyglądała lokalna zmiana
        """
        self.building = building
        self.available_routers = available_routers
        self.config = config #zapamiętujemy configa jako pole klasy
        
        #zczytujemy parametry z configa
        self.tabu_length = config.tabu_length
        self.max_iterations = config.max_iterations
        self.min_distance = config.min_distance
        self.tabu_strategy = config.tabu_strategy
        self.aspiration_strategy = config.aspiration_strategy
        self.init_strategy = config.init_strategy
        self.local_change_strategy = config.local_change_strategy
        
        # Stan algorytmu
        
        # Tabu list będzie przechowywać:
        # - dla BLOCK_ROUTER_ID: int (id routera)
        # - dla BLOCK_AREA_RADIUS: Point (punkt, który został zwolniony)
        self.tabu_list: List[Any] = []
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
        self.best_solution = solution.copy()
        self.best_value = self.evaluate_solution()
        
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
        """Losuje pozycje, ale z większym prawdopodobieństwem tam, gdzie waga 'cover' jest duża"""
        
        num_routers = len(self.available_routers)
        indices, probs = self.high_priority_indices
        
        # Reset
        for r in self.available_routers:
            r.position = None
            r.coverage_layers = None
        
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
        3. I tak dla każdego piętra
        
        Returns:
            wartość funkcji celu
        """
        goal_value = 0
        for floor_idx in range(len(self.building.Floor_list)):
            
            # agreguj zasięgi wszystkich routerów dla danego piętra
            map_of_signal_for_floor = self.building.agregation_func_for_floor(floor_idx, self.available_routers)
        
            # Oblicz funkcję celu: suma iloczynów zasięgu * wagi cover
            pietro = self.building.Floor_list[floor_idx]
            goal_value += np.sum(pietro.cover * map_of_signal_for_floor)
            
        return goal_value
    
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
        
        return router_id, pos, neighbor_pos

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
        """Wykonuje ruch: aktualizuje tablicę solution oraz fizyczną pozycję routera"""
        
        self.current_solution[old_pos] = -1
        self.current_solution[new_pos] = router_id
        
        # Przestaw router fizycznie i przelicz zasięg
        new_point = self.building.router_possible[new_pos]
        self.available_routers[router_id].position = new_point
        self.available_routers[router_id].calculate_coverage(self.building)
    
    def _revert_move(self, router_id, old_pos, new_pos):
        """Cofa ruch: przywraca router na stare miejsce"""
        
        self.current_solution[new_pos] = -1
        self.current_solution[old_pos] = router_id
        
        # Przestaw router z powrotem fizycznie
        old_point = self.building.router_possible[old_pos]
        self.available_routers[router_id].position = old_point
        self.available_routers[router_id].calculate_coverage(self.building)

    def _is_location_safe_for_router(self, router_id_to_move: int, new_pos_idx: int) -> bool:
            """
            Sprawdza, czy postawienie KONKRETNEGO routera w NOWYM miejscu
            nie spowoduje kolizji z pozostałymi routerami.
            Nie obchodzi nas, czy inne routery kolidują ze sobą - naprawiamy to krok po kroku.
            """
            # Pobieramy współrzędne miejsca, w które chcemy skoczyć
            new_point = self.building.router_possible[new_pos_idx]
            
            # Iterujemy po wszystkich routerach
            for r_idx, router in enumerate(self.available_routers):
                # Pomijamy router, który właśnie przesuwamy (bo on zaraz zniknie ze starego miejsca)
                # Pomijamy też routery, które nie są jeszcze ustawione (jeśli takie są)
                if r_idx == router_id_to_move or router.position is None:
                    continue
                
                # Sprawdzamy dystans do "sąsiada"
                dist = self.building.point_distance(new_point, router.position)
                
                if dist < self.min_distance:
                    return False # Kolizja z innym routerem!
            
            return True # Miejsce jest czyste
    
    def _get_single_router_score(self, router_idx: int) -> float:
        """Liczy wynik użyteczności tylko dla jednego routera"""
        
        scores = self.building.calculate_router_usefulness()
        return scores[router_idx] if router_idx < len(scores) else 0.0

    def _check_aspiration(self, current_total_val: float, old_router_score: float, new_router_score: float) -> bool:
        """Sprawdza kryterium aspiracji"""
        
        # sprawdzamy globalny wynik
        if current_total_val > self.best_value:
            return True

        # jeśli wybrano strategię LOCAL_GAIN sprawdzaa dodatkowe warunki
        if self.aspiration_strategy == AspirationStrategy.LOCAL_GAIN:
            
            # router był użyteczny i zyskał 30%
            if old_router_score > 0 and new_router_score > (old_router_score * self.config.aspiration_threshold):
                return True
                
            # router był bezużyteczny a teraz działa sensownie
            if old_router_score == 0 and new_router_score > self.config.aspiration_usability_threshold:
                return True
                
        return False
    
    def run(self) -> Tuple[List[int], float, dict, int]:
        """Główna pętla algorytmu."""
        
        # Start (jeśli nie wywołano wcześniej init)
        if self.current_solution is None:
            if self.init_strategy == InitialSolutionStrategy.WEIGHTED_RANDOM_INITIALIZATION:
                self.weighted_random_initial_solution()
            else:
                self.initial_solution()

        aspiration_cnt = 0
        
        self.tabu_list = []
        
        # Główna pętla
        for iteration in range(self.max_iterations):
            
            if self.local_change_strategy == LocalChangeStrategy.SMART_LOCAL_CHANGE:
                move = self.smart_local_change()
            elif self.local_change_strategy == LocalChangeStrategy.RANDOM_LOCAL_CHANGE:
                move = self.local_change()
            else:
                move = None
                
            if move is None:
                continue
                
            r_id, old_p, new_p = move
            
            # pobieramy stary wynik routera (potrzebne do LOCAL_GAIN)
            old_router_score = self._get_single_router_score(r_id)
            
            #sprawdzenie czy nie wrzuciło rutera obok innego, jeśli tak to w ogole pomija możliwośc
            if not self._is_location_safe_for_router(r_id, new_p):
                if self.history['current_values']:
                    self.history['iterations'].append(iteration)
                    self.history['best_values'].append(self.best_value)
                    self.history['current_values'].append(self.history['current_values'][-1])
                continue
            
            # wykonanie ruchu
            self._apply_move(r_id, old_p, new_p)
            current_val = self.evaluate_solution()
            new_router_score = self._get_single_router_score(r_id) # Nowy wynik routera
            
            # sprawdzenie w tabu: dwie możliwe logiki
            is_tabu = False
            
            if self.tabu_strategy == TabuStrategy.BLOCK_ROUTER_ID:
                # Strategia - czy ten router jest na liście zablokowanych
                is_tabu = r_id in self.tabu_list
                
            elif self.tabu_strategy == TabuStrategy.BLOCK_AREA_RADIUS:
                # Strategia - czy nowe miejsce jest w pobliżu starego miejsca
                target_point = self.building.router_possible[new_p]
                
                # promień zakazu to zasięg routera
                router_range = self.available_routers[r_id].max_range 
                
                for forbidden_point in self.tabu_list:
                    # sprawdzamy tylko jeśli to to samo piętro
                    if target_point.Floor_number == forbidden_point.Floor_number:
                        # używamy metody do liczenia dystansu poziomego
                        dist = self.building.horizontal_distance(target_point, forbidden_point)
                        
                        if dist < self.config.block_area_radius: 
                            is_tabu = True
                            break
            
            # ocena rozwiązania
            accept = False
            
            if not is_tabu:
                accept = True
            else:
                # Kryterium Aspiracji
                if self._check_aspiration(current_val, old_router_score, new_router_score):
                    accept = True
                    aspiration_cnt += 1
            
            if accept:
                # akutalizacja listy tabu w zależności od strategii
                if self.tabu_strategy == TabuStrategy.BLOCK_ROUTER_ID:
                    # blokujemy ID routera
                    self.tabu_list.append(r_id)
                    
                elif self.tabu_strategy == TabuStrategy.BLOCK_AREA_RADIUS:
                    # Blokujemy fizyczny punkt który właśnie opuściliśmy
                    old_point_obj = self.building.router_possible[old_p]
                    self.tabu_list.append(old_point_obj)
                
                # utrzymanie dlugosci listy
                if len(self.tabu_list) > self.tabu_length:
                    self.tabu_list.pop(0)
                
                # aktualizacja best solution
                if current_val > self.best_value:
                    self.best_solution = list(self.current_solution)
                    self.best_value = current_val
            else:
                # odrzucenie ruchu
                self._revert_move(r_id, old_p, new_p)
                if self.history['current_values']:
                    current_val = self.history['current_values'][-1]
                else:
                    current_val = self.best_value

            # Logowanie
            self.history['iterations'].append(iteration)
            self.history['best_values'].append(self.best_value)
            self.history['current_values'].append(current_val)
        
        # Reset i ustawienie
        for r in self.available_routers:
            r.position = None
            r.coverage_layers = {}
            
        for pos_idx, r_id in enumerate(self.best_solution):
            if r_id != -1:
                pt = self.building.router_possible[pos_idx]
                self.available_routers[r_id].position = pt
                self.available_routers[r_id].calculate_coverage(self.building)

        return self.best_solution, self.best_value, self.history, aspiration_cnt
    