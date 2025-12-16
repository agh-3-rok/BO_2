# tutaj wstawiam kilka danych
from __future__ import annotations # To rozwiązuje problem kolejności klas
import numpy as np
from typing import List, Tuple
from math import floor

FLOOR_DAMPING_PARAM = 2.0  #przykładowa wartość tłumienia podłogi między piętrami
TABU_LIST_LENGTH = 10  # przykładowa długość tabu listy
MAX_ITERATIONS = 100  # przykładowa maksymalna liczba iteracji tabu search


class Point:
    def __init__(self, x: int, y: int, Floor_number: int):
        self.x = x
        self.y = y
        self.Floor_number = Floor_number

    def __repr__(self):
        return f"{self.x, self.y, self.Floor_number}"


class Floor:
    """Przechowuje topografię pojedynczego piętra.

    Atrybuty:
    - `wall_matrix` (`np.ndarray` float): macierz współczynników tłumienia. Wartości
        bliskie 0.0 oznaczają brak przeszkody, większe wartości odpowiadają
        ścianom lub innym elementom tłumiącym. Macierz odzwierciedla kształt
        i rozkład przeszkód na piętrze.
    - `router_matrix` (`np.ndarray` bool): macierz pozycji, gdzie można ustawić router
        (True = pozycja dozwolona, False = niedozwolona).
    - `cover_matrix` (`np.ndarray` int): macierz punktów do pokrycia zasięgiem.
        0-5 jak bardzo chcemy zasięg w punkcie,
        `-1` = poza budynkiem / niedostępny.
    - `Floor_number` (int): numer piętra.
    - `Floor_thickness` (float): grubość stropu/podłogi, używana przy obliczaniu
        tłumienia sygnału między piętrami.

    Uwaga: wszystkie macierze (`wall`, `router`, `cover`) muszą mieć ten sam rozmiar.
    """

    def __init__(
        self,
        wall_matrix: np.ndarray,
        router_matrix: np.ndarray,
        cover_matrix,
        Floor_number: int,
        Floor_thickness: float,
    ):

        # chcemy mieć pewność że wszystkie macierze mają ten sam rozmiar
        if (
            wall_matrix.shape != router_matrix.shape
            or wall_matrix.shape != cover_matrix.shape
        ):
            raise ValueError("Wszystkie macierze muszą mieć ten sam rozmiar.")

        self.wall = wall_matrix
        self.router = router_matrix
        self.cover = cover_matrix
        self.Floor_number = Floor_number  # to w sumie nie jest potrzebn
        self.Floor_thickness = Floor_thickness


class Building:
    # obiekt przechowujący budynek składający się z pięter
    # zawiera listę pięter

    def __init__(
        self, Floors: list[Floor], Floor_heights: int, available_routers: list[Router]
    ):
        self.Floor_list = Floors
        self.router_possible = (
            self.__get_possible_router_positions()
        )  # od razu buduje liste możliwych pozycji routerów dla łatwiejszego dostępu
        self.points_to_calculate = (
            self.__get_points_to_calculate()
        )  # od razu buduje liste punktów do obliczenia zasięgu dla łatwiejszego dostępu
        self.Floor_heights = Floor_heights
        self.available_routers = available_routers
        
    def __get_possible_router_positions(self) -> List:
        """
        Zwraca listę krotek (x, y, Floor_number) z możliwymi pozycjami routerów w całym budynku
        """
        possible_positions = []
        for fl in self.Floor_list:
            for x in range(fl.router.shape[0]):
                for y in range(fl.router.shape[1]):
                    if (
                        fl.router[x, y] == 1
                    ):  # zakładamy, że 1 oznacza dozwoloną pozycję
                        possible_positions.append(Point(x, y, fl.Floor_number))

        return possible_positions

    def __get_points_to_calculate(self) -> list[Point]:
        """
        Zwraca listę punktów do obliczenia zasięgu w całym budynku
        """
        points_to_calculate = []
        for fl in self.Floor_list:
            for x in range(fl.cover.shape[0]):
                for y in range(fl.cover.shape[1]):
                    if (
                        fl.cover[x, y] != 0
                    ):  # zakładamy, że jęśli nie ma tam 0 to oznacza, że w punkcie nalezy obliczyć zasięg
                        points_to_calculate.append(Point(x, y, fl.Floor_number))

        return np.array(points_to_calculate)

    def vertical_distance(self, floor1: int, floor2: int) -> int:
        """
        pomocnicza metoda licząca dystans pionowy między piętrami
        w metrach
        uwzglednia grubość podłóg i wysokość pięter
        """

        min_floor = min(floor1, floor2)
        max_floor = max(floor1, floor2)

        z = 0.0

        for i in range(min_floor, max_floor):
            z += self.Floor_list[i].Floor_thickness + self.Floor_heights

        return z

    def horizontal_distance(self, point1: Point, point2: Point) -> float:
        """
        funkcja licząca poziomy dystans między punktami na tym samym piętrze
        w metrach
        """
        x = point1.x - point2.x
        y = point1.y - point2.y
        return (x**2 + y**2) ** 0.5

    def point_distance(self, point1: Point, point2: Point) -> float:
        """
        funkcja licząca fizyczny dystans między puntkuami w budynku
        w metrach
        """

        z = self.vertical_distance(point1.Floor_number, point2.Floor_number)
        x = point1.x - point2.x
        y = point1.y - point2.y
        return (x**2 + y**2 + z**2) ** 0.5

    def bresenham_2d(self, x1: int, y1: int, x2: int, y2: int) -> List[tuple[int, int]]:
        """
        Zwraca listę kolejnych współrzędnych leżących na odcinku między (x1, y1) i (x2, y2) czyli na piętrze...
        wykorzystując algorytm Bresenhama. Punkty są zwracane łącznie z początkiem i końcem.
        """

        points: list[tuple[int, int]] = []

        x, y = x1, y1
        dx = abs(x2 - x1)
        dy = abs(y2 - y1)
        sx = 1 if x2 >= x1 else -1
        sy = 1 if y2 >= y1 else -1

        points.append((x, y))

        if dx >= dy:
            err = dx / 2
            while x != x2:
                x += sx
                err -= dy
                if err < 0:
                    y += sy
                    err += dx
                points.append((x, y))
        else:
            err = dy / 2
            while y != y2:
                y += sy
                err -= dx
                if err < 0:
                    x += sx
                    err += dy
                points.append((x, y))
        return points

    def total_floor_thickness(self, floor1: int, floor2: int) -> float:
        """
        funkcja licząca łączną grubość podłóg między dwoma piętrami
        """
        min_floor = min(floor1, floor2)
        max_floor = max(floor1, floor2)

        total_thickness = 0.0

        for i in range(min_floor, max_floor):
            total_thickness += self.Floor_list[i].Floor_thickness

        return total_thickness

    def tan_to_cos_and_sin(self, tg_angle: float) -> tuple[float, float]:
        """
        funkcja pomocnicza konwertująca tangens kąta na cos i sin
        # jeśli dostanie +Inf to zwraca (0,1)
        # jeśli dostanie -Inf to zwraca (0,-1)
        """
        if tg_angle == float("inf"):
            return 0.0, 1.0
        if tg_angle == float("-inf"):
            return 0.0, -1.0

        cos_angle = 1 / (1 + tg_angle**2) ** 0.5
        sin_angle = tg_angle * cos_angle
        return cos_angle, sin_angle

    def calculate_line_floors(self, p1: Point, p2: Point) -> tuple[list[Point], float]:
        """
        funkcja wyliczająca punkty końcowe i początkowe lini na danych piętrach
        w celu wykorzytania ich do liczenia tłumienia przez ściany na konkretnych piętrach
        oraz całkowitą grubość podłóg pokonanych między punktami

        funkcja zakłada że punkty p1 i p2 są na różnych piętrach!

        lista punktów jest o jeden za długa -> ostatni punkt to punkt docelowy p2 (zakładamy, że zaraz przy podłodze, zatem pomijamy drogę na piętrze docelowym)

        """
        # TODO: obsługa przypadku gdy p1 i p2 są pionowo nad sobą
        # TODO: dostałeś ten sam punkt 2 razy

        # szeregowanie wyższe niższ punkt
        p_lower = p1 if p1.Floor_number < p2.Floor_number else p2
        p_higher = p2 if p1.Floor_number < p2.Floor_number else p1

        # piętro niższe i wyższe
        f1 = p_lower.Floor_number
        f2 = p_higher.Floor_number

        if f1 == f2:
            raise ValueError("Punkty muszą być na różnych piętrach.")

        vertical_distance = self.vertical_distance(
            f1, f2
        )  # cały pionowy dystans między puntkami podłogi + piętra
        horizontal_distance = self.horizontal_distance(
            p1, p2
        )  # poziomy dystans między punktami na piętrze

        # tangens kąta nachylenia linii między punktami
        # tu trzeba sprawdzić czy tangens nie jest nieskończony (czy punkty nie sa nad sobą  pionowo)
        if horizontal_distance == 0:
            tg_angle = float("inf")
        #  tutaj trzeba po prostu potraktować że cała droga jest pokonywana na pojedynczej kratce podłogi
        # i pokonuje gruboś piętra na niej
        else:
            tg_angle = vertical_distance / horizontal_distance

        # wyliczam odległość horyzontalną na każdym z pokonywanych pięter
        if tg_angle == float("inf"):
            horizontal_distance = 0.0
        else:
            horizontal_distance = self.Floor_heights / tg_angle

        # tangens kąta nachylenia linii na piętrze w poziomie
        # ponownie trzeba sprawdzić czy tangens nie jest nieskończony -> w równoległa z OY
        # uwzględniamy znak
        if (p2.x - p1.x) == 0:
            if p2.y - p1.y > 0:
                tg_horizontal = float("inf")
            else:
                tg_horizontal = float("-inf")
        else:
            tg_horizontal = (
                (p2.y - p1.y) / (p2.x - p1.x) if (p2.x - p1.x) != 0 else float("inf")
            )

        # teraz wyliczam punkty do Breshama na konkretnych piętrach (początek i koniec lini przez piętro żeby nakarmić bresenhama)
        floor_points = [p_lower]
        cos_angle, sin_angle = self.tan_to_cos_and_sin(
            tg_horizontal
        )  # funkcje tryg wyliczone z tangensa kąta poziomego

        # wliczam zawsze pierwsze, ostatnie pomijam (zakładam, że routery są montowane przy podłodze)
        for f in range(f1, f2):
            last_point = floor_points[-1]

            # uwzględniamy jeszcze grubość podłogi przez którą przechodziliśmy do wyliczenia nastepnego punktu na następnym piętrze

            new_x = last_point.x + horizontal_distance * cos_angle
            new_y = last_point.y + horizontal_distance * sin_angle

            floor_points.append(
                Point(int(floor(new_x)), int(floor(new_y)), f)
            )  # zaokrąglamy do najniżjszych calkowitych współrzędnych
            # żeby nie wyjść poza macierz piętra

            # uwzględniamy jeszcze grubość podłogi przez którą przechodziliśmy do wyliczenia nastepnego punktu na następnym piętrze
            # tylko jeśli następne piętro istnieje
            if f + 1 < len(self.Floor_list):
                x_after_floor = (
                    new_x + self.Floor_list[f + 1].Floor_thickness * cos_angle / tg_angle
                )
                y_after_floor = (
                    new_y + self.Floor_list[f + 1].Floor_thickness * sin_angle / tg_angle
                )
                p_after_floor = Point(
                    int(floor(x_after_floor)), int(floor(y_after_floor)), f + 1
                )
                floor_points.append(p_after_floor)

        # ostatni punkt nie jest potrzebny on powinien pokrywac się z p_higher

        # teraz wyliczam grubość drogi poświęconej na podłogi jako różnice całej drogi od dystansu na piętrach
        total_floor_thickness = self.total_floor_thickness(f1, f2)

        return floor_points, total_floor_thickness

    def get_all_walls(self, p1: Point, p2: Point) -> tuple[float, float]:
        """
        funkcja zwracająca  całkowity współcznynnik tłumienia ścian na drodze między punktami p1 i p2  oraz całkowitą grubość podłóg między piętrami

        wykorzystuje algorytm Bresenhama do znalezienia punktów na konkretnych piętrach
        oraz macierz ścian pięter do znalezienia współczynników tłumienia
        oraz całkowitą grubość podłóg między piętrami
        """
        # TODO: usunąć sprawdzanie cały czas czy punkt jest w tablicy

        walls = 0  # tłumienie ścian

        # obłsuga przypadku gdy punkty są na tym samym piętrze -> od razu bresenham
        if p1.Floor_number == p2.Floor_number:
            # punkty na tym samym piętrze
            floor = self.Floor_list[p1.Floor_number]
            line_points = self.bresenham_2d(p1.x, p1.y, p2.x, p2.y)
            n = len(line_points)  # liczba interpolowanych puntków na linii
            for x, y in line_points:
                if 0 <= x < floor.wall.shape[0] and 0 <= y < floor.wall.shape[1]:
                    walls += floor.wall[
                        x, y
                    ]  # uwzględniam wysokość piętra rozłożoną na liczbę punktów
            return walls, 0.0

        # punkty na różnych piętrach
        floor_points, total_floor_thickness = self.calculate_line_floors(p1, p2)

        # musi skakać co 2 bo, punkty po sobie śa na jednym piętrze -> bresenham między nimi
        # TODO : obsługa przypadku gdy punkty są pionowo nad sobą
        for i in range(0, len(floor_points) - 1, 2):
            fp1 = floor_points[i]
            fp2 = floor_points[i + 1]
            floor = self.Floor_list[fp1.Floor_number]
            line_points = self.bresenham_2d(fp1.x, fp1.y, fp2.x, fp2.y)
            n = len(line_points)  # liczba interpolowanych puntków na linii
            for x, y in line_points:
                if 0 <= x < floor.wall.shape[0] and 0 <= y < floor.wall.shape[1]:
                    walls += (
                        floor.wall[x, y] * (1 + (self.Floor_heights / n) ** 2) ** 0.5
                    )

        return walls, total_floor_thickness

    def get_damping(self, p1: Point, p2: Point, floor_damping_param) -> float:
        """
        funckja licząca tłumienie między piętrami
        Bresenham's line algorithm używany do badania ile ścian przecina linia między punktami
        """

        walls, total_floor_thickness = self.get_all_walls(p1, p2)
        total_damping = walls + floor_damping_param * total_floor_thickness

        return total_damping
    
    def goal_function_point(self, point: Point, router: Point, router_power: float = 0) -> float:
        """
        dostaje building i punkt obliczeń i router od którego liczymy
        liczymy w decybelach zatem logarytmy zwraca w dB
        dostaje building i punnkt i liczy wartosc zasiegu w punkcie
        """ 
        
        distance = self.point_distance(point, router)
        if distance == 0:
            raise ValueError("Distance between point and router cannot be zero.")
        
        damping = self.get_damping(point, router, FLOOR_DAMPING_PARAM)
        
        # Przykładowa formuła na sygnał w dB
        signal_db = - (20 * np.log10(distance) + damping) + router_power

        # TODO trzeba uwzględnić jeszcze jaki to jest router o jakiej mocy!
        # czyli po prostu dodać do signal_db wartość mocy routera w dB
        
        return signal_db
    
    def agregation_func(self, routers: List[Router]) -> np.ndarray:
        """
        Funkcja realizuje wzór na agregację/max sygnału, wykorzystując obiekty Router z ich kratkami zasięgu.
        Oblicza całą siatkę zasięgów jako maximum ze wszystkich routerów.

        Args:
            building (dm.Building): budynek
            routers (List[dm.Router]): lista routerów z obliczonymi kratkami zasięgu (coverage_grid)
            
        Returns:
            ranges (np.ndarray): globalna siatka zasięgów (maximum ze wszystkich routerów)
        """
        
        # NARAZIE POMIJAM ILOSC PIĘTER WYSTACZY DODAC FOR PO PIĘTRACH POTEM
        pietro = self.Floor_list[0]
        H, W = pietro.wall.shape
        
        global_map = np.zeros((H, W), dtype=float)
        
        # Dla każdego routera agreguj jego kratkę zasięgu do mapy globalnej
        for router in routers:
            # Pomiń routery bez obliczonej kratki
            if router.coverage_grid is None or router.grid_corner is None:
                continue
            
            local_grid = router.coverage_grid
            start_row, start_col = router.grid_corner
            
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


class Router:
    def __init__(self, Power: float, Max_users: int, Max_range: int):
        self.power = Power
        self.max_users = Max_users
        self.position = None
        self.coverage_grid = None
        self.grid_corner = None
        self.max_range = Max_range
        
    def __repr__(self):
        return f"{self.position}"

    def calculate_coverage(self, building: Building):
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
        local_router_square = np.zeros((self.max_range, self.max_range))
        
        #x, y współrzędne lewego górnego rogu 
        left_upper_x = self.position.x - self.max_range // 2
        left_upper_y = self.position.y - self.max_range // 2
        
        for i in range(self.max_range):
            for j in range(self.max_range):
                if (left_upper_x + i, left_upper_y + j) != (self.position.x, self.position.y):
                    local_router_square[i, j] = 10**(building.goal_function_point(Point(left_upper_x + i, left_upper_y + j, 0), self.position, 2)/10)
                else:
                    local_router_square[i, j] = 3 #WARTOŚĆ SYGNAŁU W MIEJSCU RUTERA
        
        self.coverage_grid = local_router_square
        self.grid_corner = (left_upper_x, left_upper_y)
    
             
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

    def greedy_initial_solution(self):
        """
        Tworzy rozwiązanie początkowe metodą zachłanną.
        Wstawia routery tam, gdzie jest największe 'niezaspokojone' zapotrzebowanie.
        """        
        # Resetujemy rozwiązanie
        num_possible = len(self.building.router_possible)
        self.current_solution = [-1] * num_possible
        used_positions = set()
        
        # Kopia mapy potrzeb - będziemy ją modyfikować (zmniejszać wagi tam, gdzie już jest zasięg)
        # Zakładamy pracę na piętrze 0
        current_needs = self.building.Floor_list[0].cover.copy() 
        
        # Iterujemy po dostępnych routerach
        for r_idx, router in enumerate(self.available_routers):
            best_pos = -1
            best_score = -float('inf')
            
            # Sprawdzamy każdą możliwą pozycję (dla przyspieszenia można sprawdzać co N-tą)
            for pos_idx, point in enumerate(self.building.router_possible):
                if pos_idx in used_positions:
                    continue
                
                # Symulujemy ustawienie routera
                router.position = point
                router.calculate_coverage(self.building)
                
                # Obliczamy 'zysk' dla TYMCZASOWYCH potrzeb (current_needs)
                score = self._calculate_marginal_gain(router, current_needs)
                
                if score > best_score:
                    best_score = score
                    best_pos = pos_idx
            
            # Zatwierdzamy najlepszą pozycję dla tego routera
            if best_pos != -1:
                self.current_solution[best_pos] = r_idx
                used_positions.add(best_pos)
                
                # Ustawiamy router finalnie
                router.position = self.building.router_possible[best_pos]
                router.calculate_coverage(self.building)
                
                # KLUCZOWE: Aktualizujemy mapę potrzeb. 
                # Tam gdzie router dał sygnał, potrzeby spadają do 0.
                self._subtract_needs(router, current_needs)

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
        
    def run(self) -> Tuple[List[int], float, dict]:
        """
        Uruchamia algorytm Tabu Search.
        
        Returns:
            (best_solution, best_value, history)
        """
        # print("=== Start Tabu Search ===")
        self.greedy_initial_solution()
        aspiration_criteria_counter = 0
        for iteration in range(self.max_iterations):
            # Generuj sąsiada
            neighbor = self.local_change()
            
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
        
    