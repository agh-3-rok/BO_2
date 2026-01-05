import sys
import os
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.data_matrices import Building, Floor, Router
from src.config import SimulationConfig


def generate_rooms(map_size: int, room_size: int = 10, wall_thickness: int = 1) -> tuple[np.ndarray, np.ndarray]:
    """
    Generuje macierze pokoi z losowym pokryciem i otworami.
    
    Args:
        map_size: rozmiar mapy (map_size x map_size)
        room_size: rozmiar jednego pokoju
        wall_thickness: grubość ścian
    
    Returns:
        wall_matrix, cover_matrix
    """
    wall_matrix = np.zeros((map_size, map_size), dtype=float)
    cover_matrix = np.zeros((map_size, map_size), dtype=int)
    
    # Ściany na obwodzie
    wall_matrix[0:wall_thickness, :] = 8.0
    wall_matrix[-wall_thickness:, :] = 8.0
    wall_matrix[:, 0:wall_thickness] = 8.0
    wall_matrix[:, -wall_thickness:] = 8.0
    
    # Generuj pokoje w siatce
    usable_size = map_size - 2 * wall_thickness
    room_with_wall = room_size + wall_thickness
    
    for row in range(0, usable_size, room_with_wall):
        for col in range(0, usable_size, room_with_wall):
            start_row = wall_thickness + row
            start_col = wall_thickness + col
            end_row = min(start_row + room_size, map_size - wall_thickness)
            end_col = min(start_col + room_size, map_size - wall_thickness)
            
            # Losowa wartość pokrycia dla tego pokoju (od 20 do 100)
            room_cover_value = np.random.randint(20, 101)
            cover_matrix[start_row:end_row, start_col:end_col] = room_cover_value
            
            # Losowe dziury/okna w pokoju (10-30% pokoju)
            if np.random.random() > 0.3:
                num_holes = np.random.randint(0, 3)
                for _ in range(num_holes):
                    hole_size = np.random.randint(2, max(3, (end_row - start_row) // 3))
                    hole_row = np.random.randint(start_row + 1, max(start_row + 2, end_row - hole_size))
                    hole_col = np.random.randint(start_col + 1, max(start_col + 2, end_col - hole_size))
                    hole_r_end = min(hole_row + hole_size, end_row)
                    hole_c_end = min(hole_col + hole_size, end_col)
                    cover_matrix[hole_row:hole_r_end, hole_col:hole_c_end] = 0
            
            # Ściany między pokojami (jeśli są miejsca na ściany)
            if end_row + wall_thickness < map_size - wall_thickness:
                wall_matrix[end_row:end_row + wall_thickness, start_col:end_col] = 5.0
                # Losowe drzwi w ścianach (20% szansy)
                if np.random.random() > 0.8:
                    door_col = np.random.randint(start_col + 1, end_col - 1)
                    wall_matrix[end_row, door_col] = 0.0
                    
            if end_col + wall_thickness < map_size - wall_thickness:
                wall_matrix[start_row:end_row, end_col:end_col + wall_thickness] = 5.0
                # Losowe drzwi w ścianach (20% szansy)
                if np.random.random() > 0.8:
                    door_row = np.random.randint(start_row + 1, end_row - 1)
                    wall_matrix[door_row, end_col] = 0.0
    
    return wall_matrix, cover_matrix


def generate_building(
    map_size: int = 50,
    num_floors: int = 2,
    room_size: int = 10,
    wall_thickness: int = 1,
) -> Building:
    """
    Generuje budynek z pokojami.
    
    Args:
        map_size: rozmiar mapy (map_size x map_size)
        num_floors: liczba pięter
        room_size: rozmiar pokoju
        wall_thickness: grubość ścian
    
    Returns:
        Building object
    """
    config = SimulationConfig(
        num_routers=8,
        router_range=20,
        floor_damping=2.0,
        max_iterations=40,
        tabu_length=10,
        min_distance=4.0,
    )
    
    floors = []
    for f in range(num_floors):
        wall_matrix, cover_matrix = generate_rooms(map_size, room_size, wall_thickness)
        
        router_matrix = np.ones((map_size, map_size), dtype=int)
        
        floors.append(
            Floor(
                wall_matrix=wall_matrix,
                router_matrix=router_matrix,
                cover_matrix=cover_matrix,
                Floor_number=f,
                Floor_thickness=0.5,
            )
        )
    
    return Building(
        Floors=floors,
        Floor_heights=3.0,
        available_routers=[],
        config=config,
    )


def save_map_to_npz(
    filepath: str,
    map_size: int = 50,
    num_floors: int = 2,
    room_size: int = 10,
    wall_thickness: int = 1,
    cover_value: int = 50,
):
    """
    Generuje mapę i zapisuje do pliku npz.
    
    Args:
        filepath: ścieżka do pliku npz
        map_size: rozmiar mapy
        num_floors: liczba pięter
        room_size: rozmiar pokoju
        wall_thickness: grubość ścian
        cover_value: wartość w cover_matrix
    """
    building = generate_building(map_size, num_floors, room_size, wall_thickness, cover_value)
    
    # Przygotuj dane do zapisu
    wall_matrices = []
    router_matrices = []
    cover_matrices = []
    
    for floor in building.Floor_list:
        wall_matrices.append(floor.wall_matrix)
        router_matrices.append(floor.router)
        cover_matrices.append(floor.cover)
    
    # Zapisz
    np.savez(
        filepath,
        map_size=map_size,
        num_floors=num_floors,
        room_size=room_size,
        wall_thickness=wall_thickness,
        cover_value=cover_value,
        wall_matrices=wall_matrices,
        router_matrices=router_matrices,
        cover_matrices=cover_matrices,
    )
    print(f"✓ Mapa zapisana: {filepath}")


def load_map_from_npz(filepath: str) -> Building:
    """
    Wczytuje mapę z pliku npz.
    
    Args:
        filepath: ścieżka do pliku npz
    
    Returns:
        Building object
    """
    data = np.load(filepath, allow_pickle=True)
    
    map_size = int(data["map_size"])
    num_floors = int(data["num_floors"])
    cover_value = int(data["cover_value"])
    
    wall_matrices = data["wall_matrices"]
    router_matrices = data["router_matrices"]
    cover_matrices = data["cover_matrices"]
    
    config = SimulationConfig(
        num_routers=8,
        router_range=20,
        floor_damping=2.0,
        max_iterations=40,
        tabu_length=10,
        min_distance=4.0,
    )
    
    floors = []
    for f in range(num_floors):
        floors.append(
            Floor(
                wall_matrix=wall_matrices[f],
                router_matrix=router_matrices[f],
                cover_matrix=cover_matrices[f],
                Floor_number=f,
                Floor_thickness=0.5,
            )
        )
    
    return Building(
        Floors=floors,
        Floor_heights=3.0,
        available_routers=[],
        config=config,
    )


if __name__ == "__main__":
    # Przykład użycia
    map_size = 100  # Zmień tutaj rozmiar mapy
    num_floors = 1
    room_size = 30
    
    # Generuj budynek
    building = generate_building(
        map_size=map_size,
        num_floors=num_floors,
        room_size=room_size
    )
    
    # Wyświetl mapy z heatmapą cover_matrix
    fig, axes = plt.subplots(1, num_floors, figsize=(8 * num_floors, 6))
    
    if num_floors == 1:
        axes = [axes]
    
    for floor_idx, floor in enumerate(building.Floor_list):
        ax = axes[floor_idx]
        
        # Heatmapa cover_matrix
        im = ax.imshow(floor.cover, cmap="viridis", origin="upper", interpolation="nearest")
        
        # Nałóż ściany jako białe linie
        wall_mask = floor.wall_matrix > 0
        ax.contour(wall_mask.astype(float), levels=[0.5], colors="white", linewidths=2)
        
        ax.set_title(f"Piętro {floor_idx} (Cover Map)")
        ax.set_xlabel("X")
        ax.set_ylabel("Y")
        fig.colorbar(im, ax=ax, label="Cover value")
    
    plt.suptitle(f"Mapa budynku: {map_size}x{map_size}, Pokoje: {room_size}")
    plt.tight_layout()
    plt.show()
    
    # # Zapisywanie map (zakomentowane)
    # maps_dir = Path(__file__).parent.parent / "maps"
    # maps_dir.mkdir(exist_ok=True)
    # 
    # configs = [
    #     {"map_size": 30, "num_floors": 2, "room_size": 8, "cover_value": 50},
    #     {"map_size": 50, "num_floors": 2, "room_size": 10, "cover_value": 50},
    #     {"map_size": 80, "num_floors": 3, "room_size": 12, "cover_value": 50},
    # ]
    # 
    # for cfg in configs:
    #     filename = f"map_{cfg['map_size']}x{cfg['num_floors']}.npz"
    #     filepath = maps_dir / filename
    #     save_map_to_npz(filepath, **cfg)
