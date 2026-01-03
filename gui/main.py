import sys
import os
import numpy as np
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout,
    QWidget, QPushButton, QFormLayout,
    QSpinBox, QDoubleSpinBox, QGroupBox, QStackedWidget,
    QDialog, QDialogButtonBox,
    QListWidget, QFileDialog,
)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


# --- KONFIGURACJA ŚCIEŻKI DO BACKENDU ---
# Dodajemy folder 'backend' do ścieżek, żeby Python go widział

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(project_root)

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
except ImportError as e:
    print(f"Błąd importu! Upewnij się, że plik backendu jest w dobrej ścieżce. Info: {e}")
    sys.exit(1)



# --- GUI (Frontend) ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # obiekt building przechowany w GUI do obliczeń
        self.config = SimulationConfig()  # tworzymy bazowy config
        self.building = create_empty_building(self.config) # tworzymy bazowy budynek na configu bazowym 
        self._floor_defs = {}  # floor_number -> FloorDefinitionResult

        self.setWindowTitle("Router Placement - Tabu Search GUI")
        self.resize(1100, 700)

        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        main_view = QWidget()
        layout = QHBoxLayout(main_view)
        self.stack.addWidget(main_view)

        # Lewy panel sterowania, parametry 
        control_panel = QVBoxLayout()
        layout.addLayout(control_panel, 1)

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


        # Przyciski
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
        
        control_panel.addStretch()

        # Prawy panel - wizualizacja
        vis_panel = QVBoxLayout()
        layout.addLayout(vis_panel, 3)

        # Wykres 1: Mapa pokrycia
        self.fig_map = Figure()
        self.canvas_map = FigureCanvas(self.fig_map)
        self.ax_map = self.fig_map.add_subplot(111)
        self.ax_map.set_title("Heatmapa Zasięgu")
        self.heatmap = None
        vis_panel.addWidget(self.canvas_map)

        # Wykres 2: Wykres zbieżności
        self.fig_conv = Figure(figsize=(5, 3))
        self.canvas_conv = FigureCanvas(self.fig_conv)
        self.ax_conv = self.fig_conv.add_subplot(111)
        self.ax_conv.set_title("Funkcja Celu (Best Score)")
        self.line_conv, = self.ax_conv.plot([], [], 'r-')
        vis_panel.addWidget(self.canvas_conv)

        self.worker = None
        self.history_fitness = []


        # strona do definicji macierzy dla pięter

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

        # jeśli lista pięter jest pusta, pokaż przycisk 

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


    # 4 metody do zapisu/wczytania symulacji i synchronizacji UI z configiem

    # pomocnicza metoda służąca do synchronizacji configu z UI
    # przed zapisem symulacji
    def _sync_config_from_ui(self):
        self.config.floor_damping = float(self.spin_damping.value())
        self.config.tabu_length = int(self.spin_tabu_len.value())
        self.config.max_iterations = int(self.spin_iters.value())

    # pomocnicza metoda służąca do synchronizacji UI z configiem
    # po wczytaniu symulacji
    def _sync_ui_from_config(self):
        self.spin_damping.setValue(float(self.config.floor_damping))
        self.spin_tabu_len.setValue(int(self.config.tabu_length))
        self.spin_iters.setValue(int(self.config.max_iterations))

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

        self._sync_ui_from_config()

        # odbuduj cache do edycji klikanej (żeby _on_floor_list_clicked działał zawsze)
        self._floor_defs = {}
        for i, fl in enumerate(self.building.Floor_list):
            self._floor_defs[i] = FloorDefinitionResult(
                floor=fl,
                wall_matrix=fl.wall_matrix,
                router_matrix=fl.router,
                cover_matrix=fl.cover,
            )

        self._refresh_floor_list()
        self.show_definition_page()


    # metdoda uruchamiająca optymalizację
    def run_optimization(self):
       pass #TODO

    # metoda aktualizująca wykresy
    def update_plots(self, iteration, fitness, matrix):
        # 1. Wykres zbieżności
        self.history_fitness.append(fitness)
        self.line_conv.set_data(range(len(self.history_fitness)), self.history_fitness)
        self.ax_conv.set_ylim(min(self.history_fitness)*0.9, max(self.history_fitness)*1.1 + 1)
        self.canvas_conv.draw()

        # 2. Heatmapa
        if self.heatmap is None:
            self.heatmap = self.ax_map.imshow(matrix, cmap='jet', origin='upper', interpolation='nearest')
            self.fig_map.colorbar(self.heatmap, ax=self.ax_map)
        else:
            self.heatmap.set_data(matrix)
            self.heatmap.set_clim(vmin=np.min(matrix), vmax=np.max(matrix)) # Autoskalowanie kolorów
        
        self.canvas_map.draw()


    def show_definition_page(self):
        self.stack.setCurrentWidget(self.definition_view)

    def show_main_page(self):
        self.stack.setCurrentIndex(0)
    
    def _refresh_floor_list(self):
        self.list_floors.blockSignals(True)
        self.list_floors.clear()
        for i in range(len(self.building.Floor_list)):
            self.list_floors.addItem(f"Piętro {i}")
        self.list_floors.blockSignals(False)

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