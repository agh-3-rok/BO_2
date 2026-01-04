from __future__ import annotations # To rozwiązuje problem kolejności klas
import numpy as np
from typing import List
from math import floor
from .config import SimulationConfig


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

        self.wall_matrix = wall_matrix
        self.wall = wall_matrix  # alias dla starszego kodu (agregacja / bresenham)
        self.router = router_matrix
        self.cover = cover_matrix
        self.Floor_number = Floor_number  # to w sumie nie jest potrzebn
        self.Floor_thickness = Floor_thickness


class Building:
    # obiekt przechowujący budynek składający się z pięter
    # zawiera listę pięter

    def __init__(
        self, Floors: list[Floor], 
        Floor_heights: float, 
        available_routers: list[Router], 
        config: SimulationConfig
    ):  

        self.Floor_list = Floors
        self.router_possible = (
            self.__get_possible_router_positions()
        )  # od razu buduje liste możliwych pozycji routerów dla łatwiejszego dostępu
        self.points_to_calculate = (
            self.__get_points_to_calculate()
        )  # od razu buduje liste punktów do obliczenia zasięgu dla łatwiejszego dostępu
        self.Floor_heights = config.floor_heights # wysokość piętra w metrach -> parametr Floor_heights z configu bierzemy, nie ma potrzeby dawać go ososbno
        self.available_routers = available_routers # TODO co to jest XD?
        self.config = config
        
    def add_floor(self, floor: Floor):
        self.Floor_list.append(floor)
        # aktualizujemy listę możliwych pozycji routerów i punktów do obliczenia
        self.router_possible = self.__get_possible_router_positions()
        self.points_to_calculate = self.__get_points_to_calculate()

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
        
        damping = self.get_damping(point, router, self.config.floor_damping)
        
        # Przykładowa formuła na sygnał w dB
        signal_db = - (20 * np.log10(distance) + damping) + router_power

        # TODO trzeba uwzględnić jeszcze jaki to jest router o jakiej mocy!
        # czyli po prostu dodać do signal_db wartość mocy routera w dB
        
        return signal_db
    
    def agregation_func_for_floor(self, floor_idx: int, routers: List[Router]) -> np.ndarray:
        """
        Funkcja realizuje wzór na agregację/max sygnału, wykorzystując obiekty Router z ich kratkami zasięgu.
        Oblicza całą siatkę zasięgów jako maximum ze wszystkich routerów.

        Args:
            building (dm.Building): budynek
            routers (List[dm.Router]): lista routerów z obliczonymi kratkami zasięgu (coverage_grid)
            
        Returns:
            ranges (np.ndarray): globalna siatka zasięgów (maximum ze wszystkich routerów)
        """
        
        target_floor = self.Floor_list[floor_idx]
        H, W = target_floor.wall.shape
        
        global_map = np.zeros((H, W), dtype=float)
        
        # dla każdego rutera agreguje się jego kratkę zasięgu
        for router in routers:
            # rutery nieustawione są pomijane
            if router.position is None or not router.coverage_layers:
                continue
            
            #sprawdzamy gdzie jest ruter a gdzie piętro dla któego liczymy
            router_floor = router.position.Floor_number
            delta = floor_idx - router_floor
            
            #sprawdzamy czy ten ruter ma w ogóle policzone dla naszego piętra
            if delta in router.coverage_layers:
                local_grid = router.coverage_layers[delta]
                start_row, start_col = router.grid_corner
            
                # wymiary małego wycinka
                h_local, w_local = local_grid.shape

                # sprawdzamy gdzie wycinek realnie zaczyna się i kończy na mapie globalnej
                global_r_start = max(0, start_row)
                global_r_end = min(H, start_row + h_local)
                global_c_start = max(0, start_col)
                global_c_end = min(W, start_col + w_local)

                # sprawdzamy które fragmenty wycinka lokalnego odpowiadają tym zakresom
                # (Jeśli start_row < 0 musimy uciąć początek wycinka lokalnego)
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



    def calculate_router_usefulness(self) -> List[float]:
        """
        Oblicza "przydatność" każdego routera z listy self.available_routers.
        Przydatność = Suma (Siła Sygnału * Waga Pokrycia) w zasięgu routera.
        
        Returns:
            List[float]: Lista wyników punktowych dla każdego routera (indeksy zgodne z listą routerów).
        """
        scores = []
        
        for router in self.available_routers:
            # Jeśli router nie jest ustawiony, jego użyteczność to 0
            if router.position is None or router.coverage_layers is None:
                scores.append(0.0)
                continue
                
            # Pobieramy piętro, na którym jest router
            floor_idx = router.position.Floor_number
            # Zabezpieczenie, gdyby router miał złe piętro
            if floor_idx >= len(self.Floor_list):
                scores.append(0.0)
                continue
                
            pietro = self.Floor_list[floor_idx]
            
            # Wymiary mapy budynku (piętra)
            H_map, W_map = pietro.cover.shape
            
            # Wymiary małej kratki routera
            local_grid = router.coverage_layers[0]
            start_row, start_col = router.grid_corner # Lewy górny róg na mapie globalnej
            h_local, w_local = local_grid.shape
            
            # Zakresy na mapie głównej (ograniczone wymiarami piętra)
            global_r_start = max(0, start_row)
            global_r_end = min(H_map, start_row + h_local)
            global_c_start = max(0, start_col)
            global_c_end = min(W_map, start_col + w_local)
            
            # Jeśli router jest całkowicie poza mapą (teoretycznie niemożliwe, ale bezpieczne)
            if global_r_start >= global_r_end or global_c_start >= global_c_end:
                scores.append(0.0)
                continue
                
            # Przeliczamy te zakresy na współrzędne wewnątrz małej kratki routera
            local_r_start = global_r_start - start_row
            local_r_end = local_r_start + (global_r_end - global_r_start)
            local_c_start = global_c_start - start_col
            local_c_end = local_c_start + (global_c_end - global_c_start)
            
            # Wycinamy odpowiednie fragmenty
            cover_slice = pietro.cover[global_r_start:global_r_end, global_c_start:global_c_end]
            signal_slice = local_grid[local_r_start:local_r_end, local_c_start:local_c_end]
            
            # Mnożymy element po elemencie (Waga * Sygnał) i sumujemy wszystko
            # To daje jedną liczbę określającą, jak bardzo ten router jest potrzebny
            score = np.sum(cover_slice * signal_slice)
            
            scores.append(float(score))
            
        return scores


class Router:
    def __init__(self, Power: float, Max_users: int, Max_range: int):
        self.power = Power
        self.max_users = Max_users
        self.position = None
        self.coverage_layers = {}
        self.grid_corner = None
        self.max_range = Max_range
        
    def __repr__(self):
        return f"{self.position}"

    def calculate_coverage(self, building: Building):
        """
        Oblicza zasięg od pojedynczego ruter, w jego istotnym otoczeniu. Wartości oblicza się w dB. 
        Teraz liczy dla 3d, czyli będzie zwracać słownik w którym dla klucza np. 0 - zwroci kratke pietra na ktorym jest ruter
        dla klucza 1 - zwroci kratkę na piętrze o jeden ponad nim, a dla -1 na piętrze poniżej.
        
        Liczbę pięter dla których sie liczy należy ustawić w tej funkcji jako floor_offsets
        """ 
        
        self.coverage_layers = {}
        
        # tutaj ustawia się dla ilu pięter liczyć, 3 piętra powinny wystarczyc przez silne tlumienie na stropach
        floor_offsets = [0, -1, 1]
        
        # piętro na którym jest ruter
        current_floor_idx = self.position.Floor_number
        
        
        #x, y współrzędne lewego górnego rogu 
        left_upper_x = self.position.x - self.max_range // 2
        left_upper_y = self.position.y - self.max_range // 2
        
        for delta_f in floor_offsets:
            target_floor_idx = current_floor_idx + delta_f
            
            # Sprawdź, czy takie piętro w ogóle istnieje w budynku
            if target_floor_idx < 0 or target_floor_idx >= len(building.Floor_list):
                continue
                
            # pusta kratka dla danego piętra
            local_router_square = np.zeros((self.max_range, self.max_range))
        
            for i in range(self.max_range):
                for j in range(self.max_range):
                    
                    # punkt na danym piętrze dla którego będziemy liczyć
                    target_point = Point(left_upper_x + i, left_upper_y + j, target_floor_idx)
                    
                    # jeśli jest to punkt w którym stoi ruter to ustawiamy w tym miejscu jego moc
                    if delta_f == 0 and (left_upper_x + i, left_upper_y + j) == (self.position.x, self.position.y):
                        val_db = self.power
                    else:
                        # obliczanie dla reszty punktów
                        val_db = building.goal_function_point(target_point, self.position, self.power)
                    
                    # konwersja na moc liniową zeby latiwej liczyc agreagacje
                    local_router_square[i, j] = 10**(val_db / 10.0)
            
            # zapis wartswy do slownika
            self.coverage_layers[delta_f] = local_router_square
            self.grid_corner = (left_upper_x, left_upper_y)