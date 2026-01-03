from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QGroupBox,
    QRadioButton,
    QPushButton,
    QButtonGroup,
    QLabel,
    QTableWidget,
    QHeaderView,
    QTableWidgetItem
)

from src.data_matrices import Floor
from src.config import SimulationConfig


class TileType:
    NO_TILE = 0
    WALL = 1
    ROUTER = 2
    CALC = 3


@dataclass(frozen=True)
class FloorDefinitionResult:
    floor: Floor
    wall_matrix: np.ndarray
    router_matrix: np.ndarray
    cover_matrix: np.ndarray


class FloorDefineWidget(QWidget):
    """
    Widget do definiowania piętra kafelkami.

    - 1: ściana (czarny) -> wall_matrix[r,c] = wall_value
    - 2: router (niebieski) -> router_matrix[r,c] = True
    - 3: punkt obliczeń (zielony) -> cover_matrix[r,c] = cover_value

    Po kliknięciu "Zatwierdź" emituje signal `confirmed(FloorDefinitionResult)`.
    """

    confirmed = pyqtSignal(object)  # FloorDefinitionResult
    # cancelled = pyqtSignal()

    def __init__(
        self,
        config: SimulationConfig,
        parent: Optional[QWidget] = None,
        *,
        wall_value: float = 5.0,
        cover_value: int = 1,
        tile_px: int = 18,
    ):
        super().__init__(parent)
        self.config = config
        self.wall_value = wall_value
        self.cover_value = cover_value
        self.tile_px = tile_px

        self._current_tile_type = TileType.WALL
        self._pending_floor_number: Optional[int] = None
        self._drag_paint_active = False
        self._last_cell: Optional[tuple[int, int]] = None

        self._build_ui()
        self.table.installEventFilter(self)   
        self.table.viewport().installEventFilter(self)
        self.table.setMouseTracking(True)  # opcjonalnie; z LPM i tak działa, ale pomaga

        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._set_mode(TileType.WALL)
        
        # Startowo "pusto" (brak rozmiaru)
        self.set_enabled(False)

    # ---------- Public API ----------

    def start_new_floor(self, *, floor_number: int, width: int, length: int, thickness: float):
            """
            Przygotowuje siatkę do edycji. Nie dodaje nic do Building – tylko edycja.
            Dopiero `Zatwierdź` emituje gotowe macierze i Floor.
            """
            self._pending_floor_number = floor_number
            self._floor_thickness = thickness

            self._init_grid(width=width, length=length)
            self.set_enabled(True)
            self.table.setFocus()

    def load_floor(
            self,
            *,
            floor_number: int,
            wall_matrix: np.ndarray,
            router_matrix: np.ndarray,
            cover_matrix: np.ndarray,
            thickness: float,
        ):
                self._pending_floor_number = floor_number
                self._floor_thickness = float(thickness)

                length, width = wall_matrix.shape
                self._init_grid(width=width, length=length)

                for r in range(length):
                    for c in range(width):
                        tile_type = TileType.NO_TILE

                        if bool(router_matrix[r, c]):
                            tile_type = TileType.ROUTER
                        elif float(wall_matrix[r, c]) != 0.0:
                            tile_type = TileType.WALL
                        else:
                            cov = int(cover_matrix[r, c])
                            if cov > 0:
                                tile_type = TileType.CALC
                            else:
                                tile_type = TileType.NO_TILE  # także dla -1

                        item = self.table.item(r, c)
                        item.setData(Qt.ItemDataRole.UserRole, tile_type)
                        item.setBackground(self._color_for_tile(tile_type))

                self.set_enabled(True)
                self.table.setFocus()

    def set_enabled(self, enabled: bool):
        self.table.setEnabled(enabled)
        self.btn_confirm.setEnabled(enabled)
        self.lbl_hint.setEnabled(enabled)
        self.rb_empty.setEnabled(enabled)
        self.rb_wall.setEnabled(enabled)
        self.rb_router.setEnabled(enabled)
        self.rb_calc.setEnabled(enabled)

    # ---------- UI ----------

    def _build_ui(self):
        root = QHBoxLayout(self)

        # Lewy panel
        left = QVBoxLayout()
        left.setAlignment(Qt.AlignmentFlag.AlignTop)

        mode_group = QGroupBox("Tryb kafelka (0/1/2/3)")
        mode_layout = QVBoxLayout(mode_group)
        
        self.rb_empty = QRadioButton("0: Brak (zwykły punkt)")
        self.rb_wall = QRadioButton("1: Ściana (czarny)")
        self.rb_router = QRadioButton("2: Router (niebieski)")
        self.rb_calc = QRadioButton("3: Punkty obliczeń (zielony)")

        mode_layout.addWidget(self.rb_empty)
        mode_layout.addWidget(self.rb_wall)
        mode_layout.addWidget(self.rb_router)
        mode_layout.addWidget(self.rb_calc)

        self.mode_buttons = QButtonGroup(self)
        self.mode_buttons.addButton(self.rb_empty, TileType.NO_TILE)
        self.mode_buttons.addButton(self.rb_wall, TileType.WALL)
        self.mode_buttons.addButton(self.rb_router, TileType.ROUTER)
        self.mode_buttons.addButton(self.rb_calc, TileType.CALC)
        self.mode_buttons.idClicked.connect(self._set_mode)

        left.addWidget(mode_group)

        self.lbl_hint = QLabel(
            "Kliknij kafelek, aby ustawić aktualny typ.\n"
            "Skróty: 0/1/2/3. Enter: ustaw na ostatnim kafelku.\n"
            "Przeciągaj LPM po kafelkach, aby malować."
        )
        self.lbl_hint.setWordWrap(True)
        left.addWidget(self.lbl_hint)

        self.btn_confirm = QPushButton("Zatwierdź piętro")
        self.btn_confirm.clicked.connect(self._on_confirm)
        left.addWidget(self.btn_confirm)

        # self.btn_cancel = QPushButton("Anuluj")
        # self.btn_cancel.clicked.connect(self.cancelled.emit)
        # left.addWidget(self.btn_cancel)

        root.addLayout(left, 0)

        # Środek: siatka
        self.table = QTableWidget()

        # blokowanie rozciągania
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        self.table.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)

        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.table.horizontalHeader().setVisible(False)
        self.table.verticalHeader().setVisible(False)
        self.table.cellClicked.connect(self._on_cell_clicked)
        self.table.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        root.addWidget(self.table, 1)

    # ---------- Behavior ----------

    def _apply_square_tile_size(self):
        rows = self.table.rowCount()
        cols = self.table.columnCount()
        if rows <= 0 or cols <= 0:
            return

        vp = self.table.viewport().size()
        # “ile pikseli może mieć kafelek, żeby zmieścić siatkę”
        tile = min(vp.width() // cols, vp.height() // rows)

        # sensowny minimalny rozmiar (żeby nie było 0px)
        tile = max(6, int(tile))

        for r in range(rows):
            self.table.setRowHeight(r, tile)
        for c in range(cols):
            self.table.setColumnWidth(c, tile)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_1:
            self.rb_wall.setChecked(True)
            return
        if key == Qt.Key.Key_2:
            self.rb_router.setChecked(True)
            return
        if key == Qt.Key.Key_3:
            self.rb_calc.setChecked(True)
            return
        if key == Qt.Key.Key_4 or key == Qt.Key.Key_0:
            self.rb_empty.setChecked(True)
            return
        super().keyPressEvent(event)

    def eventFilter(self, obj, event):
        # --- klawiatura: idzie do QTableWidget ---
        if obj is self.table and event.type() == event.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_1:
                self._set_mode(TileType.WALL); return True
            if key == Qt.Key.Key_2:
                self._set_mode(TileType.ROUTER); return True
            if key == Qt.Key.Key_3:
                self._set_mode(TileType.CALC); return True
            if key == Qt.Key.Key_0:
                self._set_mode(TileType.NO_TILE); return True
            # Enter możesz zostawić albo nie
            # if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            #     self._paint_last_or_current_cell(); return True

        # --- mysz: idzie do viewport() ---
        if obj is self.table.viewport():
            et = event.type()

            if et == event.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                self._drag_paint_active = True
                index = self.table.indexAt(event.pos())
                if index.isValid():
                    self._paint_cell(index.row(), index.column())
                return True

            if et == event.Type.MouseMove and self._drag_paint_active:
                index = self.table.indexAt(event.pos())
                if index.isValid():
                    self._paint_cell(index.row(), index.column())
                return True

            if et == event.Type.MouseButtonRelease and event.button() == Qt.MouseButton.LeftButton:
                self._drag_paint_active = False
                return True
        
        if obj is self.table.viewport() and event.type() == event.Type.Resize:
            self._apply_square_tile_size()
            return False
        
        return super().eventFilter(obj, event)

    def _set_mode(self, mode_id: int):
        self._current_tile_type = int(mode_id)
        if self._current_tile_type == TileType.NO_TILE:
            self.rb_empty.setChecked(True)
        elif self._current_tile_type == TileType.WALL:
            self.rb_wall.setChecked(True)
        elif self._current_tile_type == TileType.ROUTER:
            self.rb_router.setChecked(True)
        else:
            self.rb_calc.setChecked(True)

    def _color_for_tile(self, tile_type: int) -> QColor:
        if tile_type == TileType.NO_TILE:
            return QColor("white")
        if tile_type == TileType.WALL:
            return QColor("black")
        if tile_type == TileType.ROUTER:
            return QColor("blue")
        return QColor("green")

    def _init_grid(self, *, width: int, length: int):
        # length = liczba wierszy, width = liczba kolumn
        self.table.clear()
        self.table.setRowCount(length)
        self.table.setColumnCount(width)

        for r in range(length):
            self.table.setRowHeight(r, self.tile_px)
        for c in range(width):
            self.table.setColumnWidth(c, self.tile_px)

        # Domyślnie wszystko jako "puste" (białe)
        for r in range(length):
            for c in range(width):
                item = QTableWidgetItem()
                item.setData(Qt.ItemDataRole.UserRole, TileType.NO_TILE)
                item.setBackground(self._color_for_tile(TileType.NO_TILE))
                self.table.setItem(r, c, item)
        self._apply_square_tile_size()


    def _on_cell_clicked(self, row: int, col: int):
        self._paint_cell(row, col)

    def _paint_cell(self, row: int, col: int):
        item = self.table.item(row, col)
        if item is None:
            return
        item.setData(Qt.ItemDataRole.UserRole, self._current_tile_type)
        item.setBackground(self._color_for_tile(self._current_tile_type))
        self._last_cell = (row, col)
        self.table.setCurrentCell(row, col)

    def _paint_last_or_current_cell(self):
        if self._last_cell is not None:
            row, col = self._last_cell
            self._paint_cell(row, col)
            return

        row = self.table.currentRow()
        col = self.table.currentColumn()
        if row >= 0 and col >= 0:
            self._paint_cell(row, col)

    def _on_confirm(self):
        if self._pending_floor_number is None:
            return

        length = self.table.rowCount()
        width = self.table.columnCount()

        wall_matrix = np.zeros((length, width), dtype=float)
        router_matrix = np.zeros((length, width), dtype=bool)
        cover_matrix = np.zeros((length, width), dtype=int)

        for r in range(length):
            for c in range(width):
                item = self.table.item(r, c)
                tile_type = int(item.data(Qt.ItemDataRole.UserRole))

                if tile_type == TileType.WALL:
                    wall_matrix[r, c] = self.wall_value
                    router_matrix[r, c] = False
                    cover_matrix[r, c] = 0
                elif tile_type == TileType.ROUTER:
                    wall_matrix[r, c] = 0.0
                    router_matrix[r, c] = True
                    cover_matrix[r, c] = 0
                elif tile_type == TileType.NO_TILE:
                    wall_matrix[r, c] = 0.0
                    router_matrix[r, c] = False
                    cover_matrix[r, c] = 0
                else:  # CALC
                    wall_matrix[r, c] = 0.0
                    router_matrix[r, c] = False
                    cover_matrix[r, c] = self.cover_value

        floor = Floor(
            wall_matrix=wall_matrix,
            router_matrix=router_matrix,
            cover_matrix=cover_matrix,
            Floor_number=self._pending_floor_number,
            Floor_thickness=float(self._floor_thickness),
        )

        self.confirmed.emit(
            FloorDefinitionResult(
                floor=floor,
                wall_matrix=wall_matrix,
                router_matrix=router_matrix,
                cover_matrix=cover_matrix,
            )
        )


         # wygaszenie po zatwierdzeniu
        self.set_enabled(False)
        self._pending_floor_number = None
        self._last_cell = None