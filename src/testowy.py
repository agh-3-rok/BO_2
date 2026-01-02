import numpy as np
import matplotlib.pyplot as plt
import random
import copy

# IMPORTY (Zakładam, że masz pliki data_matrices.py i optimizer.py)
from data_matrices import Floor, Building, Router
from algorithms import TabuSearch

# --- KONFIGURACJA SYMULACJI ---
MAP_SIZE = 100        # Mniejsza mapa dla szybszych testów
NUM_ROUTERS = 5
ROUTER_RANGE = 15
ROUTER_POWER = 20
MIN_DIST = 20          
MAX_ITER = 500         # Iteracje na jedno uruchomienie
TABU_LEN = 12

NUM_RUNS = 20            # <--- ILE RAZY URUCHOMIĆ ALGORYTM NA TEJ SAMEJ MAPIE

def generate_office_layout(size, num_rooms=8):
    """Generuje mapę biura (kod bez zmian)."""
    wall_matrix = np.zeros((size, size), dtype=float)
    cover_matrix = np.zeros((size, size), dtype=int)
    router_matrix = np.ones((size, size), dtype=int) 
    cover_matrix.fill(1) 

    for i in range(num_rooms):
        w = random.randint(6, 12)
        h = random.randint(6, 12)
        if size - w - 2 < 1 or size - h - 2 < 1: continue
        x = random.randint(1, size - w - 1)
        y = random.randint(1, size - h - 1)
        
        wall_matrix[x:x+w, y] = 3.0        
        wall_matrix[x:x+w, y+h] = 3.0      
        wall_matrix[x, y:y+h] = 3.0        
        wall_matrix[x+w, y:y+h] = 3.0      
        
        if random.random() > 0.5: wall_matrix[x + w//2, y] = 0 
        else: wall_matrix[x, y + h//2] = 0 
            
        if i % 3 == 0: importance = 30  
        else: importance = 10 
        cover_matrix[x+1:x+w, y+1:y+h] = importance

    return wall_matrix, router_matrix, cover_matrix

def plot_dashboard(building, routers, history, score, run_id):
    """Wizualizacja wyników."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"BEST RESULT (Found in Run #{run_id+1})\nScore: {score:.2f}", fontsize=14, fontweight='bold')

    floor = building.Floor_list[0]
    coverage_map = building.agregation_func(routers)
    rx = [r.position.y for r in routers if r.position]
    ry = [r.position.x for r in routers if r.position]

    # 1. Layout
    axes[0, 0].imshow(floor.wall, cmap='Greys', vmin=0, vmax=5)
    axes[0, 0].scatter(rx, ry, c='red', marker='P', s=100, edgecolors='black')
    for x, y in zip(rx, ry):
        circle = plt.Circle((x, y), MIN_DIST, color='red', fill=False, linestyle='--', alpha=0.5)
        axes[0, 0].add_patch(circle)
    axes[0, 0].set_title("Layout")

    # 2. Priority
    axes[0, 1].imshow(floor.cover, cmap='viridis')
    axes[0, 1].scatter(rx, ry, c='red', marker='*', s=100)
    axes[0, 1].set_title("Priority Zones")

    # 3. Heatmap
    im3 = axes[1, 0].imshow(coverage_map, cmap='plasma', vmin=0)
    axes[1, 0].scatter(rx, ry, c='cyan', marker='x', s=80)
    axes[1, 0].set_title("Signal Strength")
    plt.colorbar(im3, ax=axes[1, 0])

    # 4. Convergence (Tego konkretnego przebiegu)
    if history:
        axes[1, 1].plot(history['iterations'], history['best_values'], color='blue', linewidth=2)
        axes[1, 1].set_title("Optimization History (Best Run)")
        axes[1, 1].grid(True)

    plt.tight_layout()
    plt.show()

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print(f"--- START SYMULACJI WIELOKROTNEJ ---")
    
    # ---------------------------------------------------------
    # 1. GENEROWANIE MAPY (TYLKO RAZ!)
    # ---------------------------------------------------------
    print("Generowanie mapy budynku...")
    walls, r_poss, covers = generate_office_layout(MAP_SIZE, num_rooms=10)
    
    pietro0 = Floor(walls, r_poss, covers, Floor_number=0, Floor_thickness=0.3)
    budynek = Building([pietro0], Floor_heights=3.0, available_routers=[])
    
    # Tworzymy obiekty routerów (będziemy ich używać wielokrotnie)
    routers = [Router(ROUTER_POWER, 20, ROUTER_RANGE) for _ in range(NUM_ROUTERS)]
    budynek.available_routers = routers

    # Zmienne do przechowywania globalnie najlepszego wyniku
    global_best_score = float('-inf')
    global_best_solution = None # Lista indeksów
    global_best_history = None
    best_run_id = -1

    # ---------------------------------------------------------
    # 2. PĘTLA URUCHOMIENIOWA (MULTISTART)
    # ---------------------------------------------------------
    print(f"\nRozpoczynam {NUM_RUNS} niezależnych przebiegów algorytmu na tej samej mapie.")
    print("-" * 60)
    print(f"{'RUN':<5} | {'START':<10} | {'BEST':<10} | {'GAIN':<8} | {'ASPIRATIONS'}")
    print("-" * 60)

    for i in range(NUM_RUNS):
        # A. RESET STANU ROUTERÓW
        # Musimy wyczyścić pozycje z poprzedniego przebiegu, żeby Weighted Random zadziałało od nowa
        for r in routers:
            r.position = None
            r.coverage_grid = None

        # B. Inicjalizacja nowej instancji algorytmu
        optimizer = TabuSearch(
            building=budynek,
            available_routers=routers,
            tabu_length=TABU_LEN,
            max_iterations=MAX_ITER,
            min_distance=MIN_DIST
        )

        # C. Uruchomienie (run() sam wywoła weighted_random_initial_solution)
        # Przechwytujemy wynik początkowy (start_val) ręcznie dla statystyk, 
        # bo run() zwraca best_value końcowe.
        optimizer.initial_solution() 
        start_val = optimizer.best_value
        
        # Resetujemy flagi wewnątrz obiektu, bo wywołaliśmy init ręcznie
        optimizer.current_solution = optimizer.best_solution
        
        # Właściwy start
        best_sol, best_val, history, asp_cnt = optimizer.run()

        # D. Logowanie wyników
        gain = ((best_val - start_val) / start_val * 100) if start_val != 0 else 0
        print(f"#{i+1:<4} | {start_val:<10.1f} | {best_val:<10.1f} | {gain:+.1f}%   | {asp_cnt}")

        # E. Sprawdzenie czy to rekord globalny
        if best_val > global_best_score:
            global_best_score = best_val
            # Musimy skopiować listę rozwiązania (wektor indeksów), a nie obiekty!
            global_best_solution = list(best_sol)
            global_best_history = copy.deepcopy(history)
            best_run_id = i

    # ---------------------------------------------------------
    # 3. PODSUMOWANIE I RYSOWANIE
    # ---------------------------------------------------------
    print("-" * 60)
    print(f"NAJLEPSZY WYNIK: {global_best_score:.2f} (Znaleziony w przebiegu #{best_run_id+1})")
    
    # F. Odtworzenie najlepszego stanu na mapie
    # (Bo ostatni przebieg pętli mógł być słaby, a my chcemy narysować ten najlepszy)
    print("\nPrzywracanie najlepszej konfiguracji do wizualizacji...")
    
    # Reset
    for r in routers:
        r.position = None
        r.coverage_grid = None
        
    # Ustawienie wg global_best_solution
    if global_best_solution:
        for pos_idx, r_id in enumerate(global_best_solution):
            if r_id != -1:
                pt = budynek.router_possible[pos_idx]
                routers[r_id].position = pt
                routers[r_id].calculate_coverage(budynek)

    # G. Rysowanie
    plot_dashboard(budynek, routers, global_best_history, global_best_score, best_run_id)