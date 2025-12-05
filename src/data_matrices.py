# tutaj wstawiam kilka danych

import numpy as np
from typing import List
from math import floor

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


def euclidean_distance(point1: np.ndarray, point2: np.ndarray) -> float:
    return np.sqrt(np.sum((point1 - point2) ** 2))


class Point:
    def __init__(self, x: int, y: int, Floor_number: int):
        self.x = x
        self.y = y
        self.Floor_number = Floor_number

    def __repr__(self):
        return f"{self.x, self.y, self.Floor_number}"


class Building:
    # obiekt przechowujący budynek składający się z pięter
    # zawiera listę pięter

    def __init__(self, Floors: list[Floor], Floor_heights: int):
        self.Floor_list = Floors
        self.router_possible = (
            self.__get_possible_router_positions()
        )  # od razu buduje liste możliwych pozycji routerów dla łatwiejszego dostępu
        self.points_to_calculate = (
            self.__get_points_to_calculate()
        )  # od razu buduje liste punktów do obliczenia zasięgu dla łatwiejszego dostępu
        self.Floor_heights = Floor_heights

    def __get_possible_router_positions(self) -> List:
        """
        Zwraca listę krotek (x, y, Floor_number) z możliwymi pozycjami routerów w całym budynku
        """
        possible_positions = []
        for fl in self.Floor_list:
            for x in range(fl.router.shape[0]):
                for y in range(fl.router.shape[1]):
                    if fl.router[x, y] == 1:  # zakładamy, że 1 oznacza dozwoloną pozycję
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
        return (x**2 + y**2)**0.5

    def point_distance(self, point1: Point, point2: Point) -> float:
        """
        funkcja licząca fizyczny dystans między puntkuami w budynku
        w metrach
        """

        z = self.vertical_distance(point1.Floor_number, point2.Floor_number)
        x = point1.x - point2.x
        y = point1.y - point2.y
        return (x**2 + y**2 + z**2)**0.5

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
        if tg_angle == float('inf'):
            return 0.0, 1.0
        if tg_angle == float('-inf'):
            return 0.0, -1.0
        
        cos_angle = 1 / (1 + tg_angle**2)**0.5
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
        #TODO: obsługa przypadku gdy p1 i p2 są pionowo nad sobą
        #TODO: dostałeś ten sam punkt 2 razy

        # szeregowanie wyższe niższ punkt
        p_lower = p1 if p1.Floor_number < p2.Floor_number else p2
        p_higher = p2 if p1.Floor_number < p2.Floor_number else p1  
        

        # piętro niższe i wyższe
        f1 = p_lower.Floor_number
        f2 = p_higher.Floor_number

        if f1 == f2:
            raise ValueError("Punkty muszą być na różnych piętrach.")

        vertical_distance = self.vertical_distance(f1, f2) # cały pionowy dystans między puntkami podłogi + piętra
        horizontal_distance = self.horizontal_distance(p1, p2) # poziomy dystans między punktami na piętrze

        # tangens kąta nachylenia linii między punktami
        # tu trzeba sprawdzić czy tangens nie jest nieskończony (czy punkty nie sa nad sobą  pionowo)
        if horizontal_distance == 0:
             tg_angle = float('inf')
            #  tutaj trzeba po prostu potraktować że cała droga jest pokonywana na pojedynczej kratce podłogi
            # i pokonuje gruboś piętra na niej
        else:
            tg_angle = vertical_distance / horizontal_distance 

        # wyliczam odległość horyzontalną na każdym z pokonywanych pięter
        if tg_angle == float('inf'):
            horizontal_distance = 0.0
        else:
            horizontal_distance = self.Floor_heights/tg_angle


        # tangens kąta nachylenia linii na piętrze w poziomie
        # ponownie trzeba sprawdzić czy tangens nie jest nieskończony -> w równoległa z OY
        # uwzględniamy znak
        if (p2.x - p1.x) == 0:
            if p2.y - p1.y > 0:
                tg_horizontal = float('inf')
            else:
                tg_horizontal = float('-inf')
        else:
            tg_horizontal = (p2.y - p1.y)/(p2.x - p1.x)  if (p2.x - p1.x) != 0 else float('inf')

        # teraz wyliczam punkty do Breshama na konkretnych piętrach (początek i koniec lini przez piętro żeby nakarmić bresenhama)
        floor_points = [p_lower]
        cos_angle, sin_angle = self.tan_to_cos_and_sin(tg_horizontal) # funkcje tryg wyliczone z tangensa kąta poziomego

        # wliczam zawsze pierwsze, ostatnie pomijam (zakładam, że routery są montowane przy podłodze)
        for f in range(f1, f2):
            last_point = floor_points[-1]

            #uwzględniamy jeszcze grubość podłogi przez którą przechodziliśmy do wyliczenia nastepnego punktu na następnym piętrze

            new_x = last_point.x + horizontal_distance*cos_angle
            new_y = last_point.y + horizontal_distance*sin_angle

            floor_points.append(Point(int(floor(new_x)), int(floor(new_y)), f)) # zaokrąglamy do najniżjszych calkowitych współrzędnych
            # żeby nie wyjść poza macierz piętra

            #uwzględniamy jeszcze grubość podłogi przez którą przechodziliśmy do wyliczenia nastepnego punktu na następnym piętrze
            # które na pewno istnieje
            x_after_floor = new_x + self.Floor_list[f + 1].Floor_thickness * cos_angle / tg_angle
            y_after_floor = new_y + self.Floor_list[f + 1].Floor_thickness * sin_angle / tg_angle
            p_after_floor = Point(int(floor(x_after_floor)), int(floor(y_after_floor)), f + 1)
            floor_points.append(p_after_floor)

        #ostatni punkt nie jest potrzebny on powinien pokrywac się z p_higher

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

        walls = 0 # tłumienie ścian

        #obłsuga przypadku gdy punkty są na tym samym piętrze -> od razu bresenham
        if p1.Floor_number == p2.Floor_number:
            # punkty na tym samym piętrze
            floor = self.Floor_list[p1.Floor_number]
            line_points = self.bresenham_2d(p1.x, p1.y, p2.x, p2.y)
            n = len(line_points) # liczba interpolowanych puntków na linii
            for (x, y) in line_points:
                if 0 <= x < floor.wall.shape[0] and 0 <= y < floor.wall.shape[1]:
                    walls += floor.wall[x, y]# uwzględniam wysokość piętra rozłożoną na liczbę punktów 
            return walls, 0.0

        # punkty na różnych piętrach 
        floor_points, total_floor_thickness = self.calculate_line_floors(p1, p2)

        #musi skakać co 2 bo, punkty po sobie śa na jednym piętrze -> bresenham między nimi
        #TODO : obsługa przypadku gdy punkty są pionowo nad sobą
        for i in range(0, len(floor_points) - 1, 2):
            fp1 = floor_points[i]
            fp2 = floor_points[i + 1]
            floor = self.Floor_list[fp1.Floor_number]
            line_points = self.bresenham_2d(fp1.x, fp1.y, fp2.x, fp2.y)
            n = len(line_points) # liczba interpolowanych puntków na linii
            for (x, y) in line_points:
                if 0 <= x < floor.wall.shape[0] and 0 <= y < floor.wall.shape[1]: 
                    walls += floor.wall[x, y]*(1 + (self.Floor_heights/n)**2)**0.5

        return walls, total_floor_thickness
        
    def get_damping(self, p1: Point, p2: Point, floor_damping_param) -> float:
        """
        funckja licząca tłumienie między piętrami
        Bresenham's line algorithm używany do badania ile ścian przecina linia między punktami
        """

        walls, total_floor_thickness = self.get_all_walls(p1, p2)
        total_damping = walls + floor_damping_param * total_floor_thickness

        return total_damping
    

class Router:
    pass