import sys
import os
import copy
import random
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import SimulationConfig
from src.data_matrices import Building, Floor, Router
from src.algorithms import TabuSearch
from src.enums import (
    TabuStrategy,
    AspirationStrategy,
    InitialSolutionStrategy,
    LocalChangeStrategy,
)

MAP_SIZE = 100
NUM_RUNS_PER_CFG = 50
MAP_FILE = None  # Ustaw nazwę pliku .npz, np. "maps/map_50x2.npz" lub None aby użyć domyślnej mapy


def create_environment(config: SimulationConfig) -> Building:
    """Wczytuje budynek z pliku npz lub generuje domyślny."""
    if MAP_FILE is not None:
        try:
            data = np.load(MAP_FILE, allow_pickle=True)
            
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
            print(f"✓ Wczytana mapa z: {MAP_FILE}\n")
            return building
        except Exception as e:
            print(f"⚠ Nie można wczytać {MAP_FILE}: {e}")
            print("Używam domyślnej mapy...\n")
    
    # Domyślna mapa
    floors = []
    for f in range(2):
        wall_matrix = np.zeros((MAP_SIZE, MAP_SIZE), dtype=float)
        wall_matrix[0, :] = 5.0
        wall_matrix[-1, :] = 5.0
        wall_matrix[:, 0] = 5.0
        wall_matrix[:, -1] = 5.0
        
        if f == 0:
            wall_matrix[10:20, 15] = 8.0
            wall_matrix[25, 10:30] = 6.0
            wall_matrix[15:35, 25] = 7.0
            wall_matrix[30:40, 35] = 5.0
        else:
            wall_matrix[5:15, 20] = 6.0
            wall_matrix[20, 15:35] = 7.0
            wall_matrix[30:45, 10] = 8.0
            wall_matrix[35, 25:40] = 5.0

        router_matrix = np.ones((MAP_SIZE, MAP_SIZE), dtype=int)

        cover_matrix = np.zeros((MAP_SIZE, MAP_SIZE), dtype=int)
        cover_matrix.fill(50 if f == 1 else 5)

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


def build_config(tabu: TabuStrategy, asp: AspirationStrategy, init: InitialSolutionStrategy, local: LocalChangeStrategy) -> SimulationConfig:
    base = SimulationConfig(
        num_routers=8,
        router_range=9,
        floor_damping=2.0,
        max_iterations=40,
        tabu_length=10,
        min_distance=4.0,
        tabu_strategy=tabu,
        aspiration_strategy=asp,
        init_strategy=init,
        local_change_strategy=local,
        aspiration_threshold=1.05,
        aspiration_usability_threshold=50.0,
    )
    return base


def setup_solver(cfg: SimulationConfig) -> TabuSearch:
    building = create_environment(cfg)
    routers = [Router(Power=20.0, Max_users=100, Max_range=cfg.router_range) for _ in range(cfg.num_routers)]
    building.available_routers = routers
    return TabuSearch(building=building, available_routers=routers, config=cfg)


def main():
    random.seed(123)
    np.random.seed(123)

    tabu_variants = [TabuStrategy.BLOCK_ROUTER_ID, TabuStrategy.BLOCK_AREA_RADIUS]
    asp_variants = [AspirationStrategy.GLOBAL_BEST, AspirationStrategy.LOCAL_GAIN]
    init_variants = [InitialSolutionStrategy.WEIGHTED_RANDOM_INITIALIZATION, InitialSolutionStrategy.RANDOM_INITIALIZATION]
    local_variants = [LocalChangeStrategy.SMART_LOCAL_CHANGE, LocalChangeStrategy.RANDOM_LOCAL_CHANGE]

    results = {}  # key: (tabu, asp, init, local) -> dict with lists

    combos = []
    for tabu in tabu_variants:
        for asp in asp_variants:
            for init in init_variants:
                for local in local_variants:
                    combos.append((tabu, asp, init, local))

    best_overall_value = -np.inf
    best_overall_solver = None
    best_overall_key = None

    for idx, (tabu, asp, init, local) in enumerate(combos):
        cfg = build_config(tabu, asp, init, local)
        key = (tabu, asp, init, local)
        results[key] = {
            "best_vals": [],
            "tabu_rejects": [],
            "asp_counts": [],
        }

        for run_idx in range(NUM_RUNS_PER_CFG):
            seed = 1000 + idx * 100 + run_idx
            random.seed(seed)
            np.random.seed(seed)

            solver = setup_solver(copy.deepcopy(cfg))
            best_sol, best_val, history, asp_cnt = solver.run()
            
            series = history.get("best_values", [])
            tabu_reject_series = history.get("tabu_reject_cnt", [])
            
            if series:
                final_best = series[-1]
                results[key]["best_vals"].append(final_best)
                results[key]["asp_counts"].append(asp_cnt)
                
                if tabu_reject_series:
                    results[key]["tabu_rejects"].append(tabu_reject_series[-1])
                else:
                    results[key]["tabu_rejects"].append(0)
                
                if final_best > best_overall_value:
                    best_overall_value = final_best
                    best_overall_solver = solver
                    best_overall_key = key

    # Przygotuj macierz do heatmapy: wiersze = tabu strategy, kolumny = kombinacje (asp, init, local)
    row_labels = [t.name for t in tabu_variants]
    col_labels = []
    for asp in asp_variants:
        for init in init_variants:
            for local in local_variants:
                col_labels.append(f"{asp.name[:3]}-{init.name.split('_')[0]}-{local.name.split('_')[0]}")

    data_mean = np.zeros((len(row_labels), len(col_labels)))
    data_best = np.zeros((len(row_labels), len(col_labels)))
    data_tabu = np.zeros((len(row_labels), len(col_labels)))
    data_asp = np.zeros((len(row_labels), len(col_labels)))

    for r, tabu in enumerate(tabu_variants):
        for c, (asp, init, local) in enumerate([(a, i, l) for a in asp_variants for i in init_variants for l in local_variants]):
            res = results.get((tabu, asp, init, local), {})
            vals = res.get("best_vals", [])
            tabu_rej = res.get("tabu_rejects", [])
            asp_cnt = res.get("asp_counts", [])
            
            data_mean[r, c] = np.mean(vals) if vals else np.nan
            data_best[r, c] = np.max(vals) if vals else np.nan
            data_tabu[r, c] = np.mean(tabu_rej) if tabu_rej else np.nan
            data_asp[r, c] = np.mean(asp_cnt) if asp_cnt else np.nan

    # Tworzenie adnotacji wieloliniowych
    annot_array = np.empty((len(row_labels), len(col_labels)), dtype=object)
    for r in range(len(row_labels)):
        for c in range(len(col_labels)):
            annot_array[r, c] = (
                f"Best: {data_best[r, c]:.4g}\n"
                f"Mean: {data_mean[r, c]:.4g}\n"
                f"Tabu: {data_tabu[r, c]:.2f}\n"
                f"Asp: {data_asp[r, c]:.2f}"
            )

    df = pd.DataFrame(data_best, index=row_labels, columns=col_labels)

    fig1 = plt.figure(figsize=(16, 6))
    sns.heatmap(
        df,
        annot=annot_array,
        fmt="",
        cmap="rocket_r",
        cbar=True,
        linewidths=0.5,
        linecolor="white",
        annot_kws={"fontsize": 7},
    )
    plt.title(f"Statystyki z {NUM_RUNS_PER_CFG} uruchomień (MAP={MAP_SIZE}x{MAP_SIZE})")
    plt.xlabel("Asp / Init / Local")
    plt.ylabel("Tabu strategy")
    plt.tight_layout()

    # Mapa pokrycia najlepszego rozwiązania
    if best_overall_solver is not None:
        fig2 = plt.figure(figsize=(10, 5))
        
        for floor_idx in range(len(best_overall_solver.building.Floor_list)):
            ax = fig2.add_subplot(1, len(best_overall_solver.building.Floor_list), floor_idx + 1)
            heatmap_data = best_overall_solver.building.agregation_func_for_floor(
                floor_idx, best_overall_solver.available_routers
            )
            
            # Nałóż ściany jako białe obszary
            floor = best_overall_solver.building.Floor_list[floor_idx]
            wall_mask = floor.wall_matrix > 0
            heatmap_with_walls = heatmap_data.copy()
            heatmap_with_walls[wall_mask] = np.max(heatmap_data) * 1.2  # ściany jako jasne obszary
            
            im = ax.imshow(heatmap_with_walls, cmap="jet", origin="upper", interpolation="nearest")
            ax.set_title(f"Piętro {floor_idx}")
            fig2.colorbar(im, ax=ax)
        
        fig2.suptitle(
            f"Najlepsza mapa pokrycia (value={best_overall_value:.6g})\n"
            f"Konfiguracja: Tabu={best_overall_key[0].name}, Asp={best_overall_key[1].name}, "
            f"Init={best_overall_key[2].name}, Local={best_overall_key[3].name}"
        )
        plt.tight_layout()

    plt.show()

    plt.tight_layout()
    plt.show()


if __name__ == "__main__":
    main()