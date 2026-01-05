import sys
import os
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QFormLayout,
    QSpinBox, QDoubleSpinBox, QGroupBox, QStackedWidget,
    QDialog, QDialogButtonBox,
    QListWidget, QFileDialog,
    QMessageBox, QLabel, QComboBox
)

from PyQt6.QtCore import QThread, pyqtSignal, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

import matplotlib as mpl
from matplotlib import colors as mcolors

# --- KONFIGURACJA ŚCIEŻKI DO BACKENDU ---
# Dodajemy folder 'backend' do ścieżek, żeby Python go widział

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(project_root)

""" --- IMPORTY WŁASNYCH PLIKÓW --- """
try:
    from gui.floor_define import FloorDefineWidget
    from gui.persistance import snapshot_to_npz, snapshot_from_npz
    from gui.floor_define import FloorDefinitionResult
except ImportError:
    print("Nie można zaimportować modułu z folderu GUI. Upewnij się, że plik jest w dobrej ścieżce.")
    sys.exit(1)

try:
    from src import data_matrices as bk
    from src.data_matrices import Building, Floor, Router
    from src.algorithms import TabuSearch
    from src.config import SimulationConfig
    from src.enums import (
    ObjectiveStrategy,
    TabuStrategy,
    AspirationStrategy,
    InitialSolutionStrategy,
    LocalChangeStrategy,
)
except ImportError as e:
    print(f"Błąd importu! Upewnij się, że plik backendu jest w dobrej ścieżce. Info: {e}")
    sys.exit(1)


""" WORKERK -> SŁUŻY DO URUCHOMIENIA TABU SEARCH W WĄTKU TŁA """
class TabuWorker(QThread):
    progress = pyqtSignal(int, float, float, object)  # iteration, best, current, heatmap_or_None
    finished_ok = pyqtSignal(object, float, object, int)  # best_solution, best_value, history, aspiration_cnt
    failed = pyqtSignal(str)

    def __init__(self, tabu: TabuSearch, *, progress_every = 1, heatmap_every = 10, heatmap_floor_idx = 0):
        super().__init__()
        self.tabu = tabu
        self.progress_every = progress_every
        self.heatmap_every = heatmap_every
        self.heatmap_floor_idx = heatmap_floor_idx

    def run(self):
        # try:
        #     def cb(iteration, best, current, heatmap):
        #         self.progress.emit(iteration, best, current, heatmap)

        #     best_sol, best_val, hist, asp = self.tabu.run(
        #         on_progress=cb,
        #         progress_every=self.progress_every,
        #         heatmap_every=self.heatmap_every,
        #         heatmap_floor_idx=self.heatmap_floor_idx,
        #     )
        #     self.finished_ok.emit(best_sol, float(best_val), hist, int(asp))
        # except Exception as e:
        #     self.failed.emit(str(e))
        
        try:
            best_sol, best_val, hist, asp = self.tabu.run()
            self.finished_ok.emit(best_sol, float(best_val), hist, int(asp))
        except Exception as e:
            self.failed.emit(str(e))


# --- GUI (Frontend) OKNO APLIKACJI ---
class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()

        # obiekt building przechowany w GUI do obliczeń
        
        self.config = SimulationConfig()  # tworzymy bazowy config
        self.building = create_empty_building(self.config) # tworzymy bazowy budynek na configu bazowym 
        
        # self._refresh_heatmap_floor_list() # SYNCHRO

        # pola służące do przechowywania stanu optymalizacji -- wątek i historia fitness
        self.worker = None
        self.history__iters = []
        self.history_fitness = []
        self.history_current = []

        self._tabu_last = None  # ostatni obiekt tabu (po optymalizacji)

        # nie pamietam co to 
        self._floor_defs = {}  # floor_number -> FloorDefinitionResult

        self.setWindowTitle("Router Placement - Tabu Search GUI")
        self.resize(1100, 700)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        main_view = QWidget()
        layout = QHBoxLayout(main_view)
        self.stack.addWidget(main_view)


        """ Pola do ustawiania parametrów symulacji"""
        # --- Lewy panel sterowania, parametry  ---
        control_panel = QVBoxLayout()
        layout.addLayout(control_panel, 1)

         # --- Panel wyboru strategii algorytmu ---
        algo_group = QGroupBox("Wersja algorytmu")
        algo_form = QFormLayout()

        self.combo_objective = QComboBox()
        self.combo_tabu = QComboBox()
        self.combo_aspiration = QComboBox()
        self.combo_init = QComboBox()
        self.combo_local_change = QComboBox()

        def _fill_enum(combo: QComboBox, enum_cls, current):
            combo.blockSignals(True)
            combo.clear()
            for e in enum_cls:
                combo.addItem(e.name, e)
            # ustaw aktualną wartość
            idx = combo.findData(current)
            if idx >= 0:
                combo.setCurrentIndex(idx)
            combo.blockSignals(False)

        _fill_enum(self.combo_objective, ObjectiveStrategy, self.config.objective_strategy)
        _fill_enum(self.combo_tabu, TabuStrategy, self.config.tabu_strategy)
        _fill_enum(self.combo_aspiration, AspirationStrategy, self.config.aspiration_strategy)
        _fill_enum(self.combo_init, InitialSolutionStrategy, self.config.init_strategy)
        _fill_enum(self.combo_local_change, LocalChangeStrategy, self.config.local_change_strategy)

        algo_form.addRow("Funkcja celu:", self.combo_objective)
        algo_form.addRow("Tabu strategy:", self.combo_tabu)
        algo_form.addRow("Aspiration:", self.combo_aspiration)
        algo_form.addRow("Init:", self.combo_init)
        algo_form.addRow("Local change:", self.combo_local_change)

        algo_group.setLayout(algo_form)
        control_panel.addWidget(algo_group)

        group = QGroupBox("Parametry")
        form = QFormLayout()

        # pole 1: Tłumienie podłogi
        self.spin_damping = QDoubleSpinBox()
        self.spin_damping.setRange(0.0, 50.0)
        self.spin_damping.setValue(self.config.floor_damping) # Domyślna wartość z pliku
        self.spin_damping.setSingleStep(0.5)
        form.addRow("Tłumienie podłogi (dB):", self.spin_damping)

        # pole 2: Długość Tabu
        self.spin_tabu_len = QSpinBox()
        self.spin_tabu_len.setValue(self.config.tabu_length)
        form.addRow("Długość Tabu:", self.spin_tabu_len)

        # pole 3: Maksymalna liczba iteracji
        self.spin_iters = QSpinBox()
        self.spin_iters.setRange(10, 5000)
        self.spin_iters.setValue(self.config.max_iterations)
        self.spin_iters.setSingleStep(10)
        form.addRow("Max Iteracji:", self.spin_iters)

        # pole 4: Liczba routerów
        self.spin_num_routers = QSpinBox()
        self.spin_num_routers.setRange(1, 100)  # dobierz max jak chcesz
        self.spin_num_routers.setValue(int(self.config.num_routers))
        self.spin_num_routers.setSingleStep(1)
        form.addRow("Liczba routerów:", self.spin_num_routers)

        """ Przyciski """
        group.setLayout(form)
        control_panel.addWidget(group)

        # przycisk pokazania panelu definicji macierzy
        self.btn_show_empty = QPushButton("Pokaż panel definicji")
        self.btn_show_empty.clicked.connect(self.show_definition_page)
        control_panel.addWidget(self.btn_show_empty)


        # przyciski zapisu/wczytania symulacji
        self.btn_save_sim = QPushButton("Zapisz symulację")
        self.btn_save_sim.clicked.connect(self.save_simulation)
        control_panel.addWidget(self.btn_save_sim)

        self.btn_load_sim = QPushButton("Wczytaj symulację")
        self.btn_load_sim.clicked.connect(self.load_simulation)
        control_panel.addWidget(self.btn_load_sim)

        # Przycisk uruchomienia optymalizacji
        self.btn_run = QPushButton("URUCHOM OPTYMALIZACJĘ")
        self.btn_run.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 10px;")
        self.btn_run.clicked.connect(self.run_optimization)
        control_panel.addWidget(self.btn_run)

        # Etykieta do wyświetlania najlepszego wyniku
        self.lbl_best_value = QLabel("Najlepszy zasięg: —")
        control_panel.addWidget(self.lbl_best_value)

        control_panel.addStretch()


        """ Prawy panel - wizualizacja """
        vis_panel = QVBoxLayout()
        layout.addLayout(vis_panel, 3)

        # Wykres 1: Mapa pokrycia + lista pięter
        self.fig_map = Figure()
        self.canvas_map = FigureCanvas(self.fig_map)
        self.ax_map = self.fig_map.add_subplot(111)
        self.ax_map.set_title("Heatmapa Zasięgu")
        # self.heatmap = None
        self.heatmap_img = None
        self.walls_img = None
        self.points_img = None
        self.heatmap_cbar = None
        self._map_shape = None

        heat_row = QHBoxLayout()
        vis_panel.addLayout(heat_row)

        # po lewej: heatmapa
        heat_row.addWidget(self.canvas_map, 1)

        # po prawej: lista pięter
        heat_floors_group = QGroupBox("Piętra (heatmapa)")
        heat_floors_group.setMaximumWidth(180)
        heat_floors_layout = QVBoxLayout()
        self.list_heatmap_floors = QListWidget()
        self.list_heatmap_floors.currentRowChanged.connect(self._on_heatmap_floor_changed)
        heat_floors_layout.addWidget(self.list_heatmap_floors)
        heat_floors_group.setLayout(heat_floors_layout)

        heat_row.addWidget(heat_floors_group, 0)


        # Wykresy 2/3: Ratio + Goal (obok siebie)
        conv_row = QHBoxLayout()
        vis_panel.addLayout(conv_row)

        # --- Ratio (lewo) ---
        self.fig_ratio = Figure(figsize=(5, 3))
        self.canvas_ratio = FigureCanvas(self.fig_ratio)
        self.ax_ratio = self.fig_ratio.add_subplot(111)
        self.ax_ratio.set_title("Ratio pokrycia (Best/Current)")
        self.line_ratio_best, = self.ax_ratio.plot([], [], "r-", label="best")
        self.line_ratio_current, = self.ax_ratio.plot([], [], "b-", label="current")
        self.ax_ratio.legend(loc="best")
        conv_row.addWidget(self.canvas_ratio, 1)

        # --- Goal (prawo) ---
        self.fig_goal = Figure(figsize=(5, 3))
        self.canvas_goal = FigureCanvas(self.fig_goal)
        self.ax_goal = self.fig_goal.add_subplot(111)
        self.ax_goal.set_title("Goal / Funkcja celu (Best/Current)")
        self.line_goal_best, = self.ax_goal.plot([], [], "r-", label="best")
        self.line_goal_current, = self.ax_goal.plot([], [], "b-", label="current")
        self.ax_goal.legend(loc="best")
        conv_row.addWidget(self.canvas_goal, 1)


        """ Strona do definicji macierzy dla pięter """

        # przycisk powrotu do głównego okna
        self.definition_view = QWidget()
        definition_layout = QHBoxLayout(self.definition_view)
        left_panel = QVBoxLayout()
        left_panel.setAlignment(Qt.AlignmentFlag.AlignTop)
        back_btn = QPushButton("Powrót do głównego okna")
        back_btn.clicked.connect(self.show_main_page)
        left_panel.addWidget(back_btn)
    
        # lista pięter
        floors_list_group = QGroupBox("Lista pięter")
        floors_list_layout = QVBoxLayout()
        self.list_floors = QListWidget()
        self.list_floors.itemClicked.connect(self._on_floor_list_clicked)
        floors_list_layout.addWidget(self.list_floors)
        floors_list_group.setLayout(floors_list_layout)
        left_panel.addWidget(floors_list_group)


        definition_layout.addLayout(left_panel)
        definition_layout.addStretch()
        self.stack.addWidget(self.definition_view)



        # przycisk dodaj piętro
        floors_group = QGroupBox("Operacje na piętrach")
        floors_layout = QVBoxLayout()
        self.btn_add_floor = QPushButton("Dodaj piętro")
        self.btn_add_floor.clicked.connect(self.add_floor)
        floors_layout.addWidget(self.btn_add_floor)
        floors_group.setLayout(floors_layout)
        left_panel.addWidget(floors_group)
        

        # widget do definiowania piętra
        self.floor_define = FloorDefineWidget(self.config, parent=self)
        definition_layout.insertWidget(1, self.floor_define, 1)
        self.floor_define.confirmed.connect(self._on_floor_defined)

        self._refresh_heatmap_floor_list() # SYNCHRO

    # metoda wywoływana po zatwierdzeniu definicji piętra w panelu definicji -> akutalizuje budynek
    def _on_floor_defined(self, result):
        fl_num = int(result.floor.Floor_number)
        self._floor_defs[fl_num] = result

        if fl_num < len(self.building.Floor_list):
            self.building.Floor_list[fl_num] = result.floor
            # odśwież cache w Building (bo replace nie wywołuje __get_*):
            self.building.router_possible = self.building._Building__get_possible_router_positions()
            self.building.points_to_calculate = self.building._Building__get_points_to_calculate()
        else:
            self.building.add_floor(result.floor)

        self._refresh_floor_list()
        self.list_floors.setCurrentRow(fl_num)
        self._refresh_heatmap_floor_list()

    # 4 metody do zapisu/wczytania symulacji i synchronizacji UI z configiem

    # pomocnicza metoda służąca do synchronizacji configu z UI
    # przed zapisem symulacji
    def _sync_config_from_ui(self):
        self.config.floor_damping = float(self.spin_damping.value())
        self.config.tabu_length = int(self.spin_tabu_len.value())
        self.config.max_iterations = int(self.spin_iters.value())
        self.config.num_routers = int(self.spin_num_routers.value())

        # strategie
        self.config.objective_strategy = self.combo_objective.currentData()
        self.config.tabu_strategy = self.combo_tabu.currentData()
        self.config.aspiration_strategy = self.combo_aspiration.currentData()
        self.config.init_strategy = self.combo_init.currentData()
        self.config.local_change_strategy = self.combo_local_change.currentData()

    # pomocnicza metoda służąca do synchronizacji UI z configiem
    # po wczytaniu symulacji
    def _sync_ui_from_config(self):
        # parametry liczbowe
        self.spin_damping.setValue(float(self.config.floor_damping))
        self.spin_tabu_len.setValue(int(self.config.tabu_length))
        self.spin_iters.setValue(int(self.config.max_iterations))
        self.spin_num_routers.setValue(int(self.config.num_routers))

        # strategie
        def _set_combo(combo: QComboBox, value):
            idx = combo.findData(value)
            if idx >= 0:
                combo.setCurrentIndex(idx)

        _set_combo(self.combo_objective, self.config.objective_strategy)
        _set_combo(self.combo_tabu, self.config.tabu_strategy)
        _set_combo(self.combo_aspiration, self.config.aspiration_strategy)
        _set_combo(self.combo_init, self.config.init_strategy)
        _set_combo(self.combo_local_change, self.config.local_change_strategy)
        

    # metoda używana przy zapisie symulacji
    def save_simulation(self):
        self._sync_config_from_ui()

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz symulację",
            "",
            "BO2 Simulation (*.npz)",
        )
        if not path:
            return

        snapshot_to_npz(path, config=self.config, building=self.building)

    # metoda używana przy wczytaniu symulacji
    def load_simulation(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Wczytaj symulację",
            "",
            "BO2 Simulation (*.npz)",
        )
        if not path:
            return

        config, building = snapshot_from_npz(path)

        self.config = config
        self.building = building

        # SYNCHRONIZACJA UI
        self._refresh_heatmap_floor_list()
        self._sync_ui_from_config()

        # odbuduj cache do edycji klikanej (żeby _on_floor_list_clicked działał zawsze)
        self._floor_defs = {}
        self._refresh_heatmap_floor_list()
        for i, fl in enumerate(self.building.Floor_list):
            self._floor_defs[i] = FloorDefinitionResult(
                floor=fl,
                wall_matrix=fl.wall_matrix,
                router_matrix=fl.router,
                cover_matrix=fl.cover,
            )

        self._refresh_floor_list()
        self.show_definition_page()


    """ Metoda uruchamiająca optymalizację Tabu Search w wątku tła"""
    def run_optimization(self):
        if not self.building.Floor_list:
            return  # brak pięter -> nie ma co liczyć

        self._sync_config_from_ui()

        # Zbuduj routery (minimalny sensowny default)
        routers = [
            Router(Power=0.0, Max_users=10, Max_range=int(self.config.router_range))
            for _ in range(int(self.config.num_routers))
        ]

        tabu = TabuSearch(self.building, routers, self.config)
        self._tabu_last = tabu
        # reset wykresu zbieżności i danyh itp po porzedniej optymalizacji
        self.history_iters = []
        self.history_best = []
        self.history_current = []

        # reset ratio
        self.ax_ratio.clear()
        self.ax_ratio.set_title("Ratio pokrycia (Best/Current)")
        self.line_ratio_best, = self.ax_ratio.plot([], [], "r-", label="best")
        self.line_ratio_current, = self.ax_ratio.plot([], [], "b-", label="current")
        self.ax_ratio.legend(loc="best")
        self.canvas_ratio.draw()

        # reset goal
        self.ax_goal.clear()
        self.ax_goal.set_title("Goal / Funkcja celu (Best/Current)")
        self.line_goal_best, = self.ax_goal.plot([], [], "r-", label="best")
        self.line_goal_current, = self.ax_goal.plot([], [], "b-", label="current")
        self.ax_goal.legend(loc="best")
        self.canvas_goal.draw()


        # uruchamiamy wątek 
        self.worker = TabuWorker(tabu, progress_every=1, heatmap_every=10, heatmap_floor_idx=0)

        # podłącz sygnały
        # self.worker.progress.connect(self._on_algo_progress)
        self.worker.finished_ok.connect(self._on_algo_finished)
        self.worker.failed.connect(self._on_algo_failed)
        
        self.worker.start()



    """ Metoda aktualizująca heatmapę na wykresie  to się rzadziej robi żeby nie latało za bardzo GUI"""
    # def update_heat(self, iteration, fitness, matrix):

    #     #  Heatmapa
    #     if self.heatmap is None:
    #         self.heatmap = self.ax_map.imshow(matrix, cmap='jet', origin='upper', interpolation='nearest')
    #         self.fig_map.colorbar(self.heatmap, ax=self.ax_map)
    #     else:
    #         self.heatmap.set_data(matrix)
    #         self.heatmap.set_clim(vmin=np.min(matrix), vmax=np.max(matrix)) # Autoskalowanie kolorów
        
    #     self.canvas_map.draw()
    def update_heat(self, floor_idx: int, matrix: np.ndarray):
        if matrix is None:
            return

        # jeśli zmienił się rozmiar macierzy (inne piętro), rekonstruujemy warstwy
        if self.heatmap_img is None or (self._map_shape is not None and self._map_shape != matrix.shape):
            self._reset_map_layers()
            self._map_shape = matrix.shape

            self.heatmap_img = self.ax_map.imshow(
                matrix,
                cmap=mpl.colormaps["jet"],
                origin="upper",
                interpolation="nearest",
            )
            self.heatmap_cbar = self.fig_map.colorbar(self.heatmap_img, ax=self.ax_map)

            # punkty obliczeń (cover > 0) – zielone kwadraty, półprzezroczyste
            points_cmap = mcolors.ListedColormap(["lime"])
            points_cmap.set_bad(alpha=0.0)
            points_overlay = self._make_points_overlay(floor_idx, matrix.shape)
            self.points_img = self.ax_map.imshow(
                points_overlay,
                cmap=points_cmap,
                origin="upper",
                interpolation="nearest",
                alpha=0.35,
                vmin=0.0,
                vmax=1.0,
            )

            # ściany (wall_matrix > 0) – czarne
            walls_cmap = mcolors.ListedColormap(["black"])
            walls_cmap.set_bad(alpha=0.0)
            walls_overlay = self._make_walls_overlay(floor_idx, matrix.shape)
            self.walls_img = self.ax_map.imshow(
                walls_overlay,
                cmap=walls_cmap,
                origin="upper",
                interpolation="nearest",
                alpha=1.0,
                vmin=0.0,
                vmax=1.0,
            )
        else:
            self.heatmap_img.set_data(matrix)
            self.heatmap_img.set_clim(vmin=float(np.nanmin(matrix)), vmax=float(np.nanmax(matrix)))

            if self.points_img is not None:
                self.points_img.set_data(self._make_points_overlay(floor_idx, matrix.shape))
            if self.walls_img is not None:
                self.walls_img.set_data(self._make_walls_overlay(floor_idx, matrix.shape))

        self.canvas_map.draw()

    def _get_map_building(self):
        return self._tabu_last.building if self._tabu_last is not None else self.building

    def _reset_map_layers(self):
        if self.heatmap_cbar is not None:
            self.heatmap_cbar.remove()
            self.heatmap_cbar = None

        self.ax_map.clear()
        self.ax_map.set_title("Heatmapa Zasięgu")
        self.heatmap_img = None
        self.walls_img = None
        self.points_img = None
        self._map_shape = None

    def _make_walls_overlay(self, floor_idx: int, shape):
        bld = self._get_map_building()
        if floor_idx < 0 or floor_idx >= len(bld.Floor_list):
            return np.full(shape, np.nan, dtype=float)

        wall = np.asarray(bld.Floor_list[floor_idx].wall_matrix, dtype=float)
        mask = wall > 1e-12  # ściana = tłumienie > 0
        return np.where(mask, 1.0, np.nan).astype(float)

    def _make_points_overlay(self, floor_idx: int, shape):
        bld = self._get_map_building()
        if floor_idx < 0 or floor_idx >= len(bld.Floor_list):
            return np.full(shape, np.nan, dtype=float)

        cover = np.asarray(bld.Floor_list[floor_idx].cover)
        mask = cover > 0  # dokładnie te punkty liczą się w funkcji celu/ratio
        return np.where(mask, 1.0, np.nan).astype(float)

    # metoda odświeżająca listę pięter w panelu heatmapy
    def _refresh_heatmap_floor_list(self):
        self.list_heatmap_floors.blockSignals(True)
        self.list_heatmap_floors.clear()
        for i in range(len(self.building.Floor_list)):
            self.list_heatmap_floors.addItem(f"Piętro {i}")
        self.list_heatmap_floors.blockSignals(False)

        if self.list_heatmap_floors.count() > 0 and self.list_heatmap_floors.currentRow() < 0:
            self.list_heatmap_floors.setCurrentRow(0)

    # metoda wywoływana po zmianie piętra w liście heatmapy
    def _on_heatmap_floor_changed(self, row: int):
        if row < 0:
            return
        if self._tabu_last is None:
            return
        if row >= len(self._tabu_last.building.Floor_list):
            return

        heat = self._tabu_last.building.agregation_func_for_floor(row, self._tabu_last.available_routers)
        best_val = float(getattr(self._tabu_last, "best_value", 0.0))
        # self.update_heat(0, best_val, heat)
        self.update_heat(row, heat)

    def _on_algo_progress(self, iteration: int, best: float, current: float, heatmap):
        # zbieranie danych
        self.history_iters.append(int(iteration))
        self.history_best.append(float(best))
        self.history_current.append(float(current))

        iters = [int(x) for x in self.history.get("iterations", [])]

        best_goal = [float(x) for x in self.history.get("best_values", [])]
        curr_goal = [float(x) for x in self.history.get("current_values", [])]

        best_ratio = [float(x) for x in self.history.get("best_ratio", [])]
        curr_ratio = [float(x) for x in self.history.get("current_ratio", [])]

        # update linii (X = iteration)
        self.line_best.set_data(self.history_iters, self.history_best)
        self.line_current.set_data(self.history_iters, self.history_current)

        # skale osi
        if self.history_iters:
            self.ax_conv.set_xlim(min(self.history_iters), max(self.history_iters))

        all_y = self.history_best + self.history_current
        if all_y:
            lo = min(all_y)
            hi = max(all_y)
            if lo == hi:
                lo -= 1.0
                hi += 1.0
            self.ax_conv.set_ylim(lo * 0.98, hi * 1.02)

        self.canvas_conv.draw()

        # heatmapa (opcjonalnie)
        if heatmap is not None:
            floor_idx = self.list_heatmap_floors.currentRow()
            if floor_idx < 0:
                floor_idx = 0
            self.update_heat(floor_idx, heatmap)


    # FUNKCJA OBŁUGUJĄCE KONIEC ALORYTMU
    def _on_algo_finished(self, best_solution, best_value, history, aspiration_cnt):
        
        # rysowanie ze wszystkiego na końcu
        iters = [int(x) for x in history.get("iterations", [])]

        best_goal = [float(x) for x in history.get("best_goal", [])]
        curr_goal = [float(x) for x in history.get("current_goal", [])]

        # best_values = [float(x) for x in history.get("best_goal", history.get("best_values", []))]
        # curr_values = [float(x) for x in history.get("current_goal", history.get("current_values", []))]

        best_ratio = [float(x) for x in history.get("best_ratio", [])]
        curr_ratio = [float(x) for x in history.get("current_ratio", [])]


        # --- Ratio (lewo) ---
        self.ax_ratio.clear()
        self.ax_ratio.set_title("Ratio pokrycia (Best/Current)")
        self.ax_ratio.plot(iters, best_ratio, "r-", label="best")
        self.ax_ratio.plot(iters, curr_ratio, "b-", label="current")
        self.ax_ratio.legend(loc="best")
        if iters:
            self.ax_ratio.set_xlim(0, max(iters))
        # ratio naturalnie w [0,1]
        self.ax_ratio.set_ylim(0.0, 1.05)
        self.canvas_ratio.draw()

        # --- Goal (prawo) ---
        self.ax_goal.clear()
        self.ax_goal.set_title("Goal / Funkcja celu (Best/Current)")
        self.ax_goal.plot(iters, best_goal, "r-", label="best")
        self.ax_goal.plot(iters, curr_goal, "b-", label="current")
        self.ax_goal.legend(loc="best")
        if iters:
            self.ax_goal.set_xlim(0, max(iters))

        all_y = best_goal + curr_goal
        if all_y:
            lo, hi = min(all_y), max(all_y)
            if lo == hi:
                lo -= 1.0
                hi += 1.0
            self.ax_goal.set_ylim(lo * 0.98, hi * 1.02)

        self.canvas_goal.draw()

        # Heatmapa tylko raz na końcu 
        if hasattr(self, "_tabu_last") and self._tabu_last is not None:
            # heat = self._tabu_last.building.agregation_func_for_floor(0, self._tabu_last.available_routers)
            # self.update_heat(iters[-1] if iters else 0, best_value, heat)
            floor_idx = self.list_heatmap_floors.currentRow()
            if floor_idx < 0:
                floor_idx = 0
            heat = self._tabu_last.building.agregation_func_for_floor(floor_idx, self._tabu_last.available_routers)
            self.update_heat(floor_idx, heat)
        

        # okienko z komunikatem o zakończeniu
        self.lbl_best_value.setText(f"Najlepsze rozwiązanie: {best_value:.6g}")

        QMessageBox.information(
            self,
            "Koniec",
            f"Algorytm zakończony.\n\nBest value: {best_value:.6g}\nAspirations: {aspiration_cnt}",
        )

        # opcjonalnie: posprzątaj wątek
        self.worker = None
    
    # BEKOWA WIADOMOŚĆ O BŁĘDZIE
    def _on_algo_failed(self, msg: str):
        print("Algorytm wywalił się:", msg)

    # FUNKCJA POKAZUJĄCA PANEL DEFINICJI
    def show_definition_page(self):
        self.stack.setCurrentWidget(self.definition_view)

    # FUNKCJA POKAZUJĄCA GŁÓWNE OKNO
    def show_main_page(self):
        self.stack.setCurrentIndex(0)
    
    # metoda odświeżająca listę pięter w panelu definicji
    def _refresh_floor_list(self):
        self.list_floors.blockSignals(True)
        self.list_floors.clear()
        for i in range(len(self.building.Floor_list)):
            self.list_floors.addItem(f"Piętro {i}")
        self.list_floors.blockSignals(False)

    # metoda wywoływana po kliknięciu na piętro w liście
    def _on_floor_list_clicked(self, item):
        text = item.text()  # "Piętro X"
        floor_number = int(text.split()[-1])

        # preferuj zapisane definicje z GUI (pewne nazwy macierzy)
        if floor_number in self._floor_defs:
            res = self._floor_defs[floor_number]
            self.floor_define.load_floor(
                floor_number=floor_number,
                wall_matrix=res.wall_matrix,
                router_matrix=res.router_matrix,
                cover_matrix=res.cover_matrix,
                thickness=res.floor.Floor_thickness,
            )
        else:
            fl = self.building.Floor_list[floor_number]
            self.floor_define.load_floor(
                floor_number=floor_number,
                wall_matrix=fl.wall_matrix,
                router_matrix=fl.router,
                cover_matrix=fl.cover,
                thickness=fl.Floor_thickness,
            )

        self.show_definition_page()


    # metoda dodająca nowe piętro i odpalająca kafelki 
    def add_floor(self):
        if len(self.building.Floor_list) == 0:
            dialog = FloorSizeDialog(self)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            width, length, height = dialog.values()
            self.config.floor_width = width
            self.config.floor_length = length
            self.config.floor_heights = float(height)
        else:
            width = self.config.floor_width
            length = self.config.floor_length

        floor_number = len(self.building.Floor_list)
        self.floor_define.start_new_floor(
            floor_number=floor_number,
            width=width,
            length=length,
            thickness=0.5,
        )
        self.show_definition_page()
        self._refresh_floor_list()

# --- DIALOG DO DEFINIOWANIA ROZMIARÓW PIĘTRA ---
# funkcja wykorzystywana w zasadzie raz przy dodawanaiu pierwszego piętra
class FloorSizeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nowe piętro")
        self.setObjectName("floorDialog")

        self.setStyleSheet("""
            QDialog#floorDialog {
                border: 2px solid #FF9800;
                border-radius: 8px;
                background-color: #ffffff;
            }
        """)
        layout = QFormLayout(self)

        self.spin_width = QSpinBox()
        self.spin_width.setRange(1, 100)
        self.spin_width.setValue(self.parent().config.floor_width)

        self.spin_length = QSpinBox()
        self.spin_length.setRange(1, 100)
        self.spin_length.setValue(self.parent().config.floor_length)
        
        self.spin_height = QDoubleSpinBox()
        self.spin_height.setRange(0.0, 10.0)
        self.spin_height.setValue(self.parent().config.floor_heights) # Domyślna wartość z pliku
        self.spin_height.setSingleStep(0.5)
  
        layout.addRow("Szerokość (m):", self.spin_width)
        layout.addRow("Długość (m):", self.spin_length)
        layout.addRow("Wysokość (m):", self.spin_height)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[int, int, int]:
        return self.spin_width.value(), self.spin_length.value(), self.spin_height.value()


def create_empty_building(config: SimulationConfig) -> bk.Building:
    # funkcja pomocniczna inicjalizująca obiekt Building z pusty
    return bk.Building(Floors = [], Floor_heights=config.floor_heights, available_routers=[], config=config)


def create_empty_floor(width: int, length: int, fl_num: int, config: SimulationConfig) -> Floor:
    # funkcja pomocniczna tworząca puste piętro o zadanych rozmiarach

    return Floor(
        wall_matrix = np.zeros((length, width), dtype=float) ,
        router_matrix = np.zeros((length, width), dtype=bool),
        cover_matrix = np.zeros((length, width), dtype=int),
        Floor_number = fl_num, # to i tak nie jest używane nigdy 
        Floor_thickness = config.floor_heights
        )


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())