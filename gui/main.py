import sys
import os
import numpy as np
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QFormLayout, 
                             QSpinBox, QDoubleSpinBox, QGroupBox, QStackedWidget,
                             QDialog, QDialogButtonBox)
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure


# --- KONFIGURACJA ŚCIEŻKI DO BACKENDU ---
# Dodajemy folder 'backend' do ścieżek, żeby Python go widział

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
sys.path.append(project_root)


try:
    from src import data_matrices as bk
    from src.data_matrices import Building, Floor, Router
    from src.algorithms import TabuSearch

except ImportError as e:
    print(f"Błąd importu! Upewnij się, że plik backendu jest w dobrej ścieżce. Info: {e}")
    sys.exit(1)



# --- GUI (Frontend) ---
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # obiekt building przechowany w GUI do obliczeń
        self.building = create_empty_building(floor_heights=3.0)

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
        self.spin_damping.setValue(2.0) # Domyślna wartość z pliku
        self.spin_damping.setSingleStep(0.5)
        form.addRow("Tłumienie podłogi (dB):", self.spin_damping)
        
        # pole 3: Wysokość piętra (m)
        self.spin_floor_height = QDoubleSpinBox()
        self.spin_floor_height.setRange(1.0, 10.0)
        self.spin_floor_height.setValue(3.0) # Domyślna wartość
        self.spin_floor_height.setSingleStep(0.1)
        form.addRow("Wysokość piętra (m):", self.spin_floor_height)

        # pole 2: Długość Tabu
        self.spin_tabu_len = QSpinBox()
        self.spin_tabu_len.setValue(10)
        form.addRow("Długość Tabu:", self.spin_tabu_len)

        # pole 3: Maksymalna liczba iteracji
        self.spin_iters = QSpinBox()
        self.spin_iters.setRange(10, 5000)
        self.spin_iters.setValue(100)
        self.spin_iters.setSingleStep(10)
        form.addRow("Max Iteracji:", self.spin_iters)


        # Przyciski
        group.setLayout(form)
        control_panel.addWidget(group)

        # przycisk pokazania panelu definicji macierzy
        self.btn_show_empty = QPushButton("Pokaż panel definicji")
        self.btn_show_empty.clicked.connect(self.show_definition_page)
        control_panel.addWidget(self.btn_show_empty)


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


        # strona do definicji macierzy 

        # przycisk powrotu do głównego okna
        self.definition_view = QWidget()
        definition_layout = QHBoxLayout(self.definition_view)
        left_panel = QVBoxLayout()
        left_panel.setAlignment(Qt.AlignmentFlag.AlignTop)
        back_btn = QPushButton("Powrót do głównego okna")
        back_btn.clicked.connect(self.show_main_page)
        left_panel.addWidget(back_btn)
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
        self.definition_view.layout().addWidget(floors_group)
        

    def run_optimization(self):
       pass #TODO

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

    def add_floor(self):
        dialog = FloorSizeDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            width, height = dialog.values()
            print(f"Dodaj piętro o rozmiarze {width}x{height}")


# --- DIALOG DO DEFINIOWANIA ROZMIARÓW PIĘTRA ---
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
        self.spin_width.setRange(1, 1000)
        self.spin_width.setValue(20)

        self.spin_height = QSpinBox()
        self.spin_height.setRange(1, 1000)
        self.spin_height.setValue(20)

        layout.addRow("Szerokość (W):", self.spin_width)
        layout.addRow("Wysokość (H):", self.spin_height)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok |
                                   QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def values(self) -> tuple[int, int]:
        return self.spin_width.value(), self.spin_height.value()

def create_empty_building(floor_heights: float = 3.0) -> bk.Building:
    return Building(Floors = [], Floor_heights=floor_heights, available_routers=[])


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())