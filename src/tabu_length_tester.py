import sys
import os
import copy
import random
import numpy as np
import matplotlib.pyplot as plt

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import SimulationConfig
from src.data_matrices import Building, Floor, Router
from src.algorithms import TabuSearch
from src.enums import (
    TabuStrategy,
    AspirationStrategy,
    InitialSolutionStrategy,
    LocalChangeStrategy,
    ObjectiveStrategy,
)

# Parametry testów
MAP_FILE = None  # None = generuj losową mapę, lub podaj ścieżkę do .npz
MAP_SIZE = 100
NUM_RUNS_PER_LENGTH = 10
TABU_LENGTHS = [5, 10, 15, 20, 25, 30, 40, 50, 55, 60]

# Parametry generowania losowych map (gdy MAP_FILE = None)
ROUTER_COVERAGE_RATIO = 0.8  # 80% komórek dostępnych dla routerów
COVER_POINTS_RATIO = 0.6     # 60% komórek to punkty do pokrycia
COVER_VALUE_RANGE = (10, 100)  # Zakres wartości punktów pokrycia

# Stałe konfiguracje strategii
ASP_STRATEGY = AspirationStrategy.GLOBAL_BEST
INIT_STRATEGY = InitialSolutionStrategy.RANDOM_INITIALIZATION
LOCAL_STRATEGY = LocalChangeStrategy.SMART_LOCAL_CHANGE
OBJECTIVE_FUNCTION = ObjectiveStrategy.WEIGHTED_SIGNAL_SUM


def create_environment(config: SimulationConfig) -> Building:
    """Wczytuje budynek z pliku npz lub generuje losową mapę."""
    if MAP_FILE is not None:
        try:
            data = np.load(MAP_FILE, allow_pickle=True)
            
            # Format GUI
            if "floor_count" in data:
                floor_count = int(data["floor_count"])
                floor_heights = float(data["floor_heights"])
                
                floors = []
                for f in range(floor_count):
                    wall_matrix = data[f"wall_{f}"]
                    router_matrix = data[f"router_{f}"].astype(int)
                    cover_matrix = data[f"cover_{f}"].astype(int)
                    thickness = float(data[f"thickness_{f}"])
                    
                    floors.append(
                        Floor(
                            wall_matrix=wall_matrix,
                            router_matrix=router_matrix,
                            cover_matrix=cover_matrix,
                            Floor_number=f,
                            Floor_thickness=thickness,
                        )
                    )
                
                building = Building(
                    Floors=floors,
                    Floor_heights=floor_heights,
                    available_routers=[],
                    config=config,
                )
                return building
            
            # Format map_generator
            elif "num_floors" in data:
                num_floors = int(data["num_floors"])
                wall_matrices = data["wall_matrices"]
                router_matrices = data["router_matrices"]
                cover_matrices = data["cover_matrices"]
                
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
                
                building = Building(
                    Floors=floors,
                    Floor_heights=3.0,
                    available_routers=[],
                    config=config,
                )
                return building
            else:
                raise ValueError("Nieznany format pliku npz")
                
        except Exception as e:
            print(f"⚠ Nie można wczytać {MAP_FILE}: {e}")
            print("Generuję losową mapę...\n")
    
    # Generowanie losowej mapy z pokojami
    floors = []
    for f in range(2):
        # Podstawowa mapa (wszystkie komórki dostępne)
        wall_matrix = np.zeros((MAP_SIZE, MAP_SIZE), dtype=float)
        router_matrix = np.zeros((MAP_SIZE, MAP_SIZE), dtype=int)
        cover_matrix = np.zeros((MAP_SIZE, MAP_SIZE), dtype=int)
        
        # Obramowanie jako ściany zewnętrzne
        wall_matrix[0, :] = 5.0
        wall_matrix[-1, :] = 5.0
        wall_matrix[:, 0] = 5.0
        wall_matrix[:, -1] = 5.0
        
        # Generowanie losowych pokoi (prostokątnych obszarów ze ścianami)
        num_rooms = np.random.randint(3, 7)
        for _ in range(num_rooms):
            room_w = np.random.randint(15, 35)
            room_h = np.random.randint(15, 35)
            room_x = np.random.randint(5, MAP_SIZE - room_w - 5)
            room_y = np.random.randint(5, MAP_SIZE - room_h - 5)
            
            # Ściany pokoju (grubość 1)
            wall_matrix[room_y, room_x:room_x+room_w] = 2.0
            wall_matrix[room_y+room_h-1, room_x:room_x+room_w] = 2.0
            wall_matrix[room_y:room_y+room_h, room_x] = 2.0
            wall_matrix[room_y:room_y+room_h, room_x+room_w-1] = 2.0
            
            # Drzwi (przerwy w ścianach)
            door_side = np.random.randint(0, 4)
            if door_side == 0 and room_w > 4:  # górna ściana
                door_pos = room_x + np.random.randint(2, room_w-2)
                wall_matrix[room_y, door_pos:door_pos+2] = 0.0
            elif door_side == 1 and room_w > 4:  # dolna ściana
                door_pos = room_x + np.random.randint(2, room_w-2)
                wall_matrix[room_y+room_h-1, door_pos:door_pos+2] = 0.0
            elif door_side == 2 and room_h > 4:  # lewa ściana
                door_pos = room_y + np.random.randint(2, room_h-2)
                wall_matrix[door_pos:door_pos+2, room_x] = 0.0
            elif door_side == 3 and room_h > 4:  # prawa ściana
                door_pos = room_y + np.random.randint(2, room_h-2)
                wall_matrix[door_pos:door_pos+2, room_x+room_w-1] = 0.0
        
        # Router matrix: miejsca gdzie można postawić routery (80% komórek)
        available_cells = (wall_matrix == 0)
        num_router_cells = int(np.sum(available_cells) * ROUTER_COVERAGE_RATIO)
        available_indices = np.argwhere(available_cells)
        if len(available_indices) > num_router_cells:
            selected = np.random.choice(len(available_indices), num_router_cells, replace=False)
            for idx in selected:
                y, x = available_indices[idx]
                router_matrix[y, x] = 1
        else:
            router_matrix[available_cells] = 1
        
        # Cover matrix: punkty do pokrycia (60% komórek) z losowymi wartościami
        num_cover_cells = int(np.sum(available_cells) * COVER_POINTS_RATIO)
        if len(available_indices) > num_cover_cells:
            selected = np.random.choice(len(available_indices), num_cover_cells, replace=False)
            for idx in selected:
                y, x = available_indices[idx]
                cover_matrix[y, x] = np.random.randint(COVER_VALUE_RANGE[0], COVER_VALUE_RANGE[1])
        else:
            cover_matrix[available_cells] = np.random.randint(COVER_VALUE_RANGE[0], COVER_VALUE_RANGE[1])

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


def build_config(tabu_length: int, tabu_strategy: TabuStrategy) -> SimulationConfig:
    """Tworzy konfigurację z konkretną długością tabu."""
    return SimulationConfig(
        num_routers=25,
        router_range=25,
        floor_damping=2.0,
        max_iterations=200,
        tabu_length=tabu_length,
        min_distance=10,
        tabu_strategy=tabu_strategy,
        aspiration_strategy=ASP_STRATEGY,
        init_strategy=INIT_STRATEGY,
        local_change_strategy=LOCAL_STRATEGY,
        objective_strategy=OBJECTIVE_FUNCTION,
        aspiration_threshold=1.05,
        aspiration_usability_threshold=50.0,
    )


def setup_solver(cfg: SimulationConfig) -> TabuSearch:
    building = create_environment(cfg)
    routers = [Router(Power=20.0, Max_users=100, Max_range=cfg.router_range) for _ in range(cfg.num_routers)]
    building.available_routers = routers
    return TabuSearch(building=building, available_routers=routers, config=cfg)


def main():
    random.seed(123)
    np.random.seed(123)

    print(f"Testowanie wpływu długości listy tabu")
    if MAP_FILE:
        print(f"Mapa wczytana z: {MAP_FILE}")
    else:
        print(f"Generowanie losowych map dla każdego uruchomienia")
        print(f"  - Router coverage: {ROUTER_COVERAGE_RATIO*100:.0f}%")
        print(f"  - Cover points: {COVER_POINTS_RATIO*100:.0f}%")
        print(f"  - Cover value range: {COVER_VALUE_RANGE}")
    print(f"Testowane strategie tabu: BLOCK_AREA_RADIUS i BLOCK_ROUTER_ID")
    print(f"Testowane długości tabu: {TABU_LENGTHS}")
    print(f"Powtórzeń dla każdej długości: {NUM_RUNS_PER_LENGTH}\n")

    # Wyniki dla obu strategii
    results_area_radius = {}
    results_router_id = {}
    
    tabu_strategies = [
        (TabuStrategy.BLOCK_AREA_RADIUS, results_area_radius, "BLOCK_AREA_RADIUS"),
        (TabuStrategy.BLOCK_ROUTER_ID, results_router_id, "BLOCK_ROUTER_ID"),
    ]

    for tabu_strategy, results_dict, strategy_name in tabu_strategies:
        print(f"\n{'='*70}")
        print(f"Testowanie: {strategy_name}")
        print(f"{'='*70}\n")
        
        total_runs = len(TABU_LENGTHS) * NUM_RUNS_PER_LENGTH
        current_run = 0

        for tabu_len in TABU_LENGTHS:
            results_dict[tabu_len] = {
                "best_vals": [],
                "tabu_rejects": [],
                "asp_counts": [],
            }

            print(f"\n--- Testowanie tabu_length = {tabu_len} ---")

            for run_idx in range(NUM_RUNS_PER_LENGTH):
                current_run += 1
                seed = 2000 + tabu_len * 100 + run_idx
                random.seed(seed)
                np.random.seed(seed)

                print(f"  [{current_run}/{total_runs}] Uruchomienie {run_idx + 1}/{NUM_RUNS_PER_LENGTH}... ", end="", flush=True)

                try:
                    cfg = build_config(tabu_len, tabu_strategy)
                    solver = setup_solver(copy.deepcopy(cfg))
                    best_sol, best_val, history, asp_cnt = solver.run()

                    series = history.get("best_values", [])
                    tabu_reject_series = history.get("tabu_reject_cnt", [])

                    if series:
                        final_best = series[-1]
                        results_dict[tabu_len]["best_vals"].append(final_best)
                        results_dict[tabu_len]["asp_counts"].append(asp_cnt)

                        if tabu_reject_series:
                            results_dict[tabu_len]["tabu_rejects"].append(tabu_reject_series[-1])
                        else:
                            results_dict[tabu_len]["tabu_rejects"].append(0)

                        print(f"✓ Wynik: {final_best:.4g}")
                    else:
                        print(f"⚠ Brak wyników (historia pusta)")

                except Exception as e:
                    print(f"❌ BŁĄD: {type(e).__name__}: {e}")

        # Analiza wyników dla tej strategii
        print("\n" + "="*70)
        print(f"PODSUMOWANIE: {strategy_name}")
        print("="*70)
        print(f"{'Tabu Len':<10} {'Best':<12} {'Mean':<12} {'Std':<12} {'TabuRej':<12} {'AspCount':<12}")
        print("-"*70)

        for tabu_len in TABU_LENGTHS:
            vals = results_dict[tabu_len]["best_vals"]
            tabu_rej = results_dict[tabu_len]["tabu_rejects"]
            asp_cnt = results_dict[tabu_len]["asp_counts"]

            if vals:
                mean_val = np.mean(vals)
                std_val = np.std(vals)
                best_val = np.max(vals)
                mean_tabu = np.mean(tabu_rej)
                mean_asp = np.mean(asp_cnt)

                print(f"{tabu_len:<10} {best_val:<12.4g} {mean_val:<12.4g} {std_val:<12.4g} {mean_tabu:<12.1f} {mean_asp:<12.1f}")
            else:
                print(f"{tabu_len:<10} {'N/A':<12} {'N/A':<12} {'N/A':<12} {'N/A':<12} {'N/A':<12}")

    # Przygotowanie danych do 2x2 wykresu
    # BLOCK_AREA_RADIUS
    tabu_lens_area = []
    means_area = []
    stds_area = []
    bests_area = []

    for tabu_len in TABU_LENGTHS:
        vals = results_area_radius[tabu_len]["best_vals"]
        if vals:
            tabu_lens_area.append(tabu_len)
            means_area.append(np.mean(vals))
            stds_area.append(np.std(vals))
            bests_area.append(np.max(vals))

    # BLOCK_ROUTER_ID
    tabu_lens_router = []
    means_router = []
    stds_router = []
    bests_router = []

    for tabu_len in TABU_LENGTHS:
        vals = results_router_id[tabu_len]["best_vals"]
        if vals:
            tabu_lens_router.append(tabu_len)
            means_router.append(np.mean(vals))
            stds_router.append(np.std(vals))
            bests_router.append(np.max(vals))

    # Wykresy 2x2
    fig, axes = plt.subplots(2, 2, figsize=(18, 12))

    # Górny lewy: BLOCK_AREA_RADIUS Mean
    ax = axes[0, 0]
    ax.errorbar(tabu_lens_area, means_area, yerr=stds_area, marker='o', linestyle='-', linewidth=2.5,
                markersize=10, capsize=6, color='blue', label='Mean ± Std')
    ax.set_xlabel('Tabu Length', fontsize=13)
    ax.set_ylabel('Objective Value', fontsize=13)
    ax.set_title('BLOCK_AREA_RADIUS: Mean Performance', fontsize=15, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=12)

    # Górny prawy: BLOCK_AREA_RADIUS Best
    ax = axes[0, 1]
    ax.plot(tabu_lens_area, bests_area, marker='s', linestyle='-', linewidth=2.5,
            markersize=10, color='red', label='Best')
    ax.set_xlabel('Tabu Length', fontsize=13)
    ax.set_ylabel('Objective Value', fontsize=13)
    ax.set_title('BLOCK_AREA_RADIUS: Best Performance', fontsize=15, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=12)

    # Dolny lewy: BLOCK_ROUTER_ID Mean
    ax = axes[1, 0]
    ax.errorbar(tabu_lens_router, means_router, yerr=stds_router, marker='o', linestyle='-', linewidth=2.5,
                markersize=10, capsize=6, color='blue', label='Mean ± Std')
    ax.set_xlabel('Tabu Length', fontsize=13)
    ax.set_ylabel('Objective Value', fontsize=13)
    ax.set_title('BLOCK_ROUTER_ID: Mean Performance', fontsize=15, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=12)

    # Dolny prawy: BLOCK_ROUTER_ID Best
    ax = axes[1, 1]
    ax.plot(tabu_lens_router, bests_router, marker='s', linestyle='-', linewidth=2.5,
            markersize=10, color='red', label='Best')
    ax.set_xlabel('Tabu Length', fontsize=13)
    ax.set_ylabel('Objective Value', fontsize=13)
    ax.set_title('BLOCK_ROUTER_ID: Best Performance', fontsize=15, fontweight='bold')
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=12)

    plt.tight_layout()
    print(f"\n✓ Wykresy 2x2 gotowe")
    plt.show()


if __name__ == "__main__":
    main()
