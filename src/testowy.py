import numpy as np
import matplotlib.pyplot as plt
import copy

# Upewnij się, że pliki data_matrices.py i optimizer.py są w tym samym folderze
from data_matrices import Building, Floor, Router
from algorithms import TabuSearch, TabuStrategy, AspirationStrategy

# --- KONFIGURACJA ---
MAP_SIZE = 30           # Rozmiar mapy (30x30 kratek)
NUM_FLOORS = 2          # Liczba pięter
NUM_ROUTERS = 4         # Liczba routerów
ROUTER_POWER = 20       # Moc routera
ROUTER_RANGE = 10       # Promień zasięgu
MIN_DIST = 3.0          # Min. dystans między routerami
MAX_ITER = 120          # Liczba iteracji na test

def create_test_environment():
    """
    Tworzy budynek z 2 piętrami o różnych priorytetach.
    Piętro 0: Korytarze (mało ważne).
    Piętro 1: Biura (bardzo ważne).
    """
    floors = []
    
    for f in range(NUM_FLOORS):
        # 1. Ściany (puste pudełko + słupek na środku)
        wall_matrix = np.zeros((MAP_SIZE, MAP_SIZE), dtype=float)
        # Ściany zewnętrzne
        wall_matrix[0, :] = 5.0
        wall_matrix[-1, :] = 5.0
        wall_matrix[:, 0] = 5.0
        wall_matrix[:, -1] = 5.0
        # Przeszkoda na środku
        mid = MAP_SIZE // 2
        wall_matrix[mid-2:mid+2, mid-2:mid+2] = 5.0
        
        # 2. Priorytety (Importance)
        cover_matrix = np.zeros((MAP_SIZE, MAP_SIZE), dtype=int)
        router_matrix = np.ones((MAP_SIZE, MAP_SIZE), dtype=int)
        
        if f == 0:
            # Parter - priorytet 5 (mały)
            cover_matrix.fill(5)
        else:
            # Piętro 1 - priorytet 50 (duży) -> Routery powinny uciekać tutaj!
            cover_matrix.fill(50) 
            
            # Dodatkowo super ważny pokój w rogu piętra 1
            cover_matrix[5:10, 5:10] = 200

        floors.append(Floor(wall_matrix, router_matrix, cover_matrix, Floor_number=f, Floor_thickness=0.5))

    building = Building(floors, Floor_heights=3.0, available_routers=[])
    routers = [Router(ROUTER_POWER, 20, ROUTER_RANGE) for _ in range(NUM_ROUTERS)]
    building.available_routers = routers
    
    return building, routers

def plot_results(building, routers, title):
    """Wizualizacja wyników dla wszystkich pięter."""
    fig, axes = plt.subplots(1, NUM_FLOORS, figsize=(12, 5))
    if NUM_FLOORS == 1: axes = [axes]
    
    fig.suptitle(title, fontsize=14, fontweight='bold')
    
    for f_idx, ax in enumerate(axes):
        # Pobierz mapę sygnału (uwzględnia 3D)
        signal_map = building.agregation_func_for_floor(f_idx, routers)
        floor_obj = building.Floor_list[f_idx]
        
        # Rysuj sygnał
        im = ax.imshow(signal_map, cmap='plasma', vmin=0, vmax=100) # vmax dostosuj do skali
        
        # Rysuj ściany
        ax.imshow(floor_obj.wall, cmap='Greys', alpha=0.3)
        
        # Rysuj routery
        for r in routers:
            if r.position:
                py, px = r.position.y, r.position.x
                if r.position.Floor_number == f_idx:
                    # Router na tym piętrze
                    ax.scatter(py, px, c='lime', marker='P', s=150, edgecolors='black', label='Router Here')
                else:
                    # Router na innym piętrze (Ghost)
                    ax.scatter(py, px, c='gray', marker='x', s=50, alpha=0.5, label='Router Other Floor')
                    
        ax.set_title(f"Floor {f_idx} (Max Priority: {np.max(floor_obj.cover)})")
        ax.invert_yaxis()

    plt.tight_layout()
    plt.show()

def run_scenario(name, building, routers, t_strat, a_strat):
    """Uruchamia pojedynczy scenariusz testowy."""
    print(f"\n>>> TEST: {name}")
    print(f"    Tabu Strategy: {t_strat.name}")
    print(f"    Aspi Strategy: {a_strat.name}")
    
    # RESET ROUTERÓW (Bardzo ważne!)
    for r in routers:
        r.position = None
        r.coverage_layers = {}
    
    # Inicjalizacja Optymalizatora
    optimizer = TabuSearch(
        building=building,
        available_routers=routers,
        tabu_length=15,
        max_iterations=MAX_ITER,
        min_distance=MIN_DIST,
        tabu_strategy=t_strat,          # <--- Wybór strategii
        aspiration_strategy=a_strat     # <--- Wybór aspiracji
    )
    
    # Uruchomienie
    # Wymuszamy start losowy, żeby mieć punkt odniesienia
    optimizer.weighted_random_initial_solution()
    start_val = optimizer.best_value
    
    # Fix po ręcznym inicie
    optimizer.current_solution = list(optimizer.best_solution) 
    
    # Run
    best_sol, best_val, history, asp_cnt = optimizer.run()
    
    gain = ((best_val - start_val) / start_val * 100) if start_val > 0 else 0
    
    print("-" * 50)
    print(f"    Start Score: {start_val:.1f}")
    print(f"    End Score:   {best_val:.1f}")
    print(f"    Gain:        {gain:+.1f}%")
    print(f"    Aspirations: {asp_cnt} (Ile razy złamano Tabu)")
    print("-" * 50)
    
    return best_val, asp_cnt, history

# --- MAIN ---
if __name__ == "__main__":
    building, routers = create_test_environment()
    
    # SCENARIUSZ 1: Klasyczny (Konserwatywny)
    # Blokujemy router po ID, aspiracja tylko przy rekordzie świata
    val1, asp1, hist1 = run_scenario(
        "CLASSIC SETUP", 
        building, routers,
        TabuStrategy.BLOCK_ROUTER_ID, 
        AspirationStrategy.GLOBAL_BEST
    )
    plot_results(building, routers, "Classic Results (Conservative)")

    # SCENARIUSZ 2: Nowoczesny (Agresywny)
    # Blokujemy obszar (radius), aspiracja przy lokalnym zysku routera
    val2, asp2, hist2 = run_scenario(
        "MODERN SETUP", 
        building, routers,
        TabuStrategy.BLOCK_AREA_RADIUS, 
        AspirationStrategy.LOCAL_GAIN
    )
    plot_results(building, routers, "Modern Results (New Strategies)")
    
    # Porównanie wykresów zbieżności
    plt.figure(figsize=(10, 6))
    plt.plot(hist1['best_values'], label=f'Classic (Asp={asp1})', linestyle='--')
    plt.plot(hist2['best_values'], label=f'Modern (Asp={asp2})', linewidth=2)
    plt.title("Optimization Convergence Comparison")
    plt.xlabel("Iteration")
    plt.ylabel("Total Score")
    plt.legend()
    plt.grid(True)
    plt.show()