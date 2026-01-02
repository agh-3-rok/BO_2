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

    def greedy_initial_solution(self, step):
        """
        Tworzy rozwiązanie początkowe metodą zachłanną z optymalizacją (step).
        """            
        num_possible = len(self.building.router_possible)
        self.current_solution = [-1] * num_possible
        used_positions = set()
        
        # Kopia mapy potrzeb
        current_needs = self.building.Floor_list[0].cover.copy() 
        
        # KROK (STEP): Jak gęsto sprawdzamy mapę?
        # step = 1  -> sprawdza każdy możliwy punkt (dokładne, ale wolne)
        # step = 10 -> sprawdza co 10-ty punkt (szybkie, dobre dla dużych map 256x256)
        
        # Pętla po wszystkich dostępnych routerach (stawiamy je po kolei)
        for r_idx, router in enumerate(self.available_routers):
            
            best_pos = -1
            best_score = -float('inf')
            
            # --- 1. PĘTLA SZUKANIA (SKANOWANIE MAPY) ---
            # Sprawdzamy co N-ty punkt, żeby nie liczyć w nieskończoność
            for pos_idx in range(0, num_possible, step):
                
                # Jeśli to miejsce jest już zajęte przez poprzedni router -> pomiń
                if pos_idx in used_positions:
                    continue
                
                # Pobieramy punkt z listy wszystkich możliwych
                point = self.building.router_possible[pos_idx]
                
                # 2. SYMULACJA
                router.position = point
                router.calculate_coverage(self.building)
                
                # 3. OCENA ZYSKU
                score = self._calculate_marginal_gain(router, current_needs)
                
                # Jeśli to miejsce jest lepsze niż dotychczas znalezione dla tego routera
                if score > best_score:
                    best_score = score
                    best_pos = pos_idx # <--- ZAPAMIĘTUJEMY TYLKO INDEKS!

            # --- 4. PRZYPISANIE (TO JEST KLUCZOWE) ---
            # Pętla szukania się skończyła. Mamy w 'best_pos' indeks najlepszego miejsca.
            # Teraz faktycznie stawiamy tam router.
            
            if best_pos != -1:
                # Zapisujemy w wektorze rozwiązania
                self.current_solution[best_pos] = r_idx
                used_positions.add(best_pos)
                
                # Ustawiamy router fizycznie w najlepszym znalezionym punkcie
                router.position = self.building.router_possible[best_pos]
                router.calculate_coverage(self.building)
                
                # Aktualizujemy mapę potrzeb (wygaszamy popyt tam, gdzie router dał sygnał)
                self._subtract_needs(router, current_needs)

        # Koniec - zapisujemy wyniki
        self.best_solution = self.current_solution.copy()
        self.best_value = self.evaluate_solution()

    def _calculate_marginal_gain(self, router, current_needs) -> float:
            """
            Liczy, ile 'punktów potrzeby' zaspokoi ten router w danej pozycji.
            """
            # Jeśli router nie ma policzonego zasięgu, nie daje zysku
            if router.coverage_grid is None or router.grid_corner is None:
                return 0.0
                
            # Wymiary mapy globalnej (current_needs)
            H, W = current_needs.shape
            
            # Wymiary i pozycja mapy lokalnej routera
            local_grid = router.coverage_grid
            start_row, start_col = router.grid_corner
            h_local, w_local = local_grid.shape
            
            # --- LOGIKA WYCINANIA (SLICING) ---
            # 1. Ustalamy zakresy na mapie globalnej (przycinamy do granic budynku)
            global_r_start = max(0, start_row)
            global_r_end = min(H, start_row + h_local)
            global_c_start = max(0, start_col)
            global_c_end = min(W, start_col + w_local)
            
            # Jeśli router jest całkowicie poza mapą
            if global_r_start >= global_r_end or global_c_start >= global_c_end:
                return 0.0
                
            # 2. Ustalamy odpowiadające zakresy na mapie lokalnej routera
            local_r_start = global_r_start - start_row
            local_r_end = local_r_start + (global_r_end - global_r_start)
            local_c_start = global_c_start - start_col
            local_c_end = local_c_start + (global_c_end - global_c_start)
            
            # --- OBLICZENIA ---
            # Wycinamy fragmenty macierzy
            needs_slice = current_needs[global_r_start:global_r_end, global_c_start:global_c_end]
            router_slice = local_grid[local_r_start:local_r_end, local_c_start:local_c_end]
            
            # Mnożymy: Waga potrzeby * Siła sygnału. Sumujemy, by dostać jedną liczbę (score).
            gain = np.sum(needs_slice * router_slice)
            
            return float(gain)

    def _subtract_needs(self, router, current_needs):
        """
        Zeruje wagi w macierzy current_needs tam, gdzie router dostarczył sygnał.
        Dzięki temu kolejne routery nie będą celować w to samo miejsce.
        """
        if router.coverage_grid is None or router.grid_corner is None:
            return

        # Wymiary mapy globalnej
        H, W = current_needs.shape
        
        local_grid = router.coverage_grid
        start_row, start_col = router.grid_corner
        h_local, w_local = local_grid.shape
        
        # --- LOGIKA WYCINANIA (identyczna jak wyżej) ---
        global_r_start = max(0, start_row)
        global_r_end = min(H, start_row + h_local)
        global_c_start = max(0, start_col)
        global_c_end = min(W, start_col + w_local)
        
        if global_r_start >= global_r_end or global_c_start >= global_c_end:
            return

        local_r_start = global_r_start - start_row
        local_r_end = local_r_start + (global_r_end - global_r_start)
        local_c_start = global_c_start - start_col
        local_c_end = local_c_start + (global_c_end - global_c_start)

        # --- AKTUALIZACJA POTRZEB ---
        # Pobieramy wycinki (widoki na macierze)
        needs_slice = current_needs[global_r_start:global_r_end, global_c_start:global_c_end]
        router_slice = local_grid[local_r_start:local_r_end, local_c_start:local_c_end]
        
        # Gdzie sygnał routera jest > 0, tam ustawiamy potrzebę na 0.
        # (Zakładamy, że jeśli router tu sięga, to temat jest załatwiony).
        # Używamy maski logicznej numpy:
        mask = router_slice > 0
        
        # Zerujemy potrzeby w tych miejscach
        needs_slice[mask] = 0
    
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
        
    