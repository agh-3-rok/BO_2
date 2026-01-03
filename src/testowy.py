import numpy as np
import matplotlib.pyplot as plt
from data_matrices import Building, Floor, Router
from algorithms import TabuSearch, TabuStrategy, AspirationStrategy, InitialSolutionStrategy, LocalChangeStrategy

# --- KONFIGURACJA TESTU ---
NUM_RUNS = 20           # Liczba powtórzeń
MAX_ITER = 100          
MAP_SIZE = 30
NUM_ROUTERS = 5
ROUTER_RANGE = 10

def create_environment():
    """Tworzy środowisko testowe (2 piętra)."""
    floors = []
    for f in range(2):
        wall = np.zeros((MAP_SIZE, MAP_SIZE))
        wall[10:20, 10:20] = 5.0 
        
        cover = np.zeros((MAP_SIZE, MAP_SIZE), dtype=int)
        if f == 0: cover.fill(5)   
        else:      cover.fill(50)  
        
        router_matrix = np.ones((MAP_SIZE, MAP_SIZE), dtype=int)
        floors.append(Floor(wall, router_matrix, cover, f, 0.5))
        
    building = Building(floors, 3.0, [])
    routers = [Router(20, 20, ROUTER_RANGE) for _ in range(NUM_ROUTERS)]
    building.available_routers = routers
    return building, routers

def run_benchmark():
    # Definicja scenariuszy wykorzystująca NOWE strategie
    scenarios = [
        {
            "name": "1. Blind Random",
            "tabu_strat": TabuStrategy.BLOCK_ROUTER_ID,
            "asp_strat": AspirationStrategy.GLOBAL_BEST,
            "init_strat": InitialSolutionStrategy.RANDOM_INITIALIZATION,
            "move_strat": LocalChangeStrategy.RANDOM_LOCAL_CHANGE,
            "color": "red"
        },
        {
            "name": "2. Smart Start Only",
            "tabu_strat": TabuStrategy.BLOCK_ROUTER_ID,
            "asp_strat": AspirationStrategy.GLOBAL_BEST,
            "init_strat": InitialSolutionStrategy.WEIGHTED_RANDOM_INITIALIZATION,
            "move_strat": LocalChangeStrategy.RANDOM_LOCAL_CHANGE, # Ruchy nadal losowe
            "color": "orange"
        },
        {
            "name": "3. Full Smart (Classic)",
            "tabu_strat": TabuStrategy.BLOCK_ROUTER_ID,
            "asp_strat": AspirationStrategy.GLOBAL_BEST,
            "init_strat": InitialSolutionStrategy.WEIGHTED_RANDOM_INITIALIZATION,
            "move_strat": LocalChangeStrategy.SMART_LOCAL_CHANGE, # Ruchy celowane w najgorsze routery
            "color": "green"
        }
    ]

    results_data = {s["name"]: {"scores": []} for s in scenarios}

    print(f"Rozpoczynam benchmark ({NUM_RUNS} prób)...")
    print("=" * 70)

    for s_idx, sc in enumerate(scenarios):
        print(f"Test: {sc['name']}...", end="", flush=True)
        
        for i in range(NUM_RUNS):
            building, routers = create_environment()
            
            # Inicjalizacja z nowymi parametrami
            opt = TabuSearch(
                building=building,
                available_routers=routers,
                tabu_length=10,
                max_iterations=MAX_ITER,
                min_distance=3.0,
                tabu_strategy=sc['tabu_strat'],
                aspiration_strategy=sc['asp_strat'],
                init_strategy=sc['init_strat'],        # <--- Wybór inicjalizacji
                local_change_strategy=sc['move_strat'] # <--- Wybór ruchu
            )
            
            # Uruchomienie (run sam wywoła odpowiedni init wewnątrz)
            opt.run()
            
            results_data[sc["name"]]["scores"].append(opt.best_value)
            
            if i % 5 == 0: print(".", end="", flush=True)
            
        print(" Gotowe!")

    # --- WYKRES ---
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    score_lists = [results_data[s["name"]]["scores"] for s in scenarios]
    names = [s["name"] for s in scenarios]
    colors = [s["color"] for s in scenarios]
    
    bplot = ax1.boxplot(score_lists, patch_artist=True, labels=names)
    
    for patch, color in zip(bplot['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
        
    ax1.set_title(f"Wpływ Strategii Inicjalizacji i Ruchu na Wynik")
    ax1.set_ylabel("Funkcja Celu")
    ax1.grid(True, linestyle='--', alpha=0.7)
    
    plt.show()

if __name__ == "__main__":
    run_benchmark()