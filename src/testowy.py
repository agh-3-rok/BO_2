import numpy as np
import matplotlib.pyplot as plt
import random

# IMPORTY Z TWOICH PLIKÓW
from data_matrices import Floor, Building, Router, Point
from algorithms import TabuSearch

# --- KONFIGURACJA SYMULACJI ---
MAP_SIZE = 100           # Rozmiar mapy (np. 60x60 kratek)
NUM_ROUTERS = 10         # Liczba routerów
ROUTER_RANGE = 15       # Zasięg routera (promień)
ROUTER_POWER = 20       # Moc routera
MIN_DIST = 20.0         # Minimalna odległość między routerami (ważne dla Twojego algorytmu!)
MAX_ITER = 500        # Liczba iteracji
TABU_LEN = 15           # Długość listy Tabu

def generate_office_layout(size, num_rooms=8):
    """
    Generuje mapę biura: 
    - wall_matrix: ściany (tłumienie)
    - cover_matrix: strefy priorytetowe (biurka, sale konferencyjne)
    - router_matrix: miejsca dozwolone
    """
    wall_matrix = np.zeros((size, size), dtype=float)
    cover_matrix = np.zeros((size, size), dtype=int)
    router_matrix = np.ones((size, size), dtype=int) 

    # 1. Korytarze - bazowy niski priorytet
    cover_matrix.fill(1) 

    # 2. Generowanie pokoi
    for i in range(num_rooms):
        w = random.randint(6, 12)
        h = random.randint(6, 12)
        
        # Znajdź losowe miejsce (z marginesem)
        if size - w - 2 < 1 or size - h - 2 < 1: continue
        x = random.randint(1, size - w - 1)
        y = random.randint(1, size - h - 1)
        
        # Ściany (tłumienie = 3.0)
        wall_matrix[x:x+w, y] = 3.0        
        wall_matrix[x:x+w, y+h] = 3.0      
        wall_matrix[x, y:y+h] = 3.0        
        wall_matrix[x+w, y:y+h] = 3.0      
        
        # Drzwi (wycięcie w ścianie)
        if random.random() > 0.5:
            wall_matrix[x + w//2, y] = 0 # Drzwi poziome
        else:
            wall_matrix[x, y + h//2] = 0 # Drzwi pionowe
            
        # Wnętrze pokoju - RÓŻNE PRIORYTETY
        # Co 3 pokój to "Sala Konferencyjna" z bardzo wysokim priorytetem
        if i % 3 == 0:
            importance = 30  # Bardzo ważne miejsce!
        else:
            importance = 10  # Zwykłe biuro
            
        cover_matrix[x+1:x+w, y+1:y+h] = importance

    return wall_matrix, router_matrix, cover_matrix

def plot_dashboard(building, routers, history, score):
    """
    Wizualizacja wyników w 4 oknach.
    """
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle(f"WiFi Optimization Results\nScore: {score:.2f} | Routers: {len(routers)} | Min Dist: {MIN_DIST}", fontsize=14, fontweight='bold')

    floor = building.Floor_list[0]
    coverage_map = building.agregation_func(routers)
    
    # Współrzędne routerów (Y, X dla imshow)
    rx = [r.position.y for r in routers if r.position]
    ry = [r.position.x for r in routers if r.position]

    # 1. Layout (Ściany)
    ax1 = axes[0, 0]
    ax1.imshow(floor.wall, cmap='Greys', vmin=0, vmax=5)
    ax1.scatter(rx, ry, c='red', marker='P', s=100, edgecolors='black', label='Router')
    # Rysowanie okręgów minimalnej odległości (opcjonalne, dla wizualizacji)
    for x, y in zip(rx, ry):
        circle = plt.Circle((x, y), MIN_DIST, color='red', fill=False, linestyle='--', alpha=0.5)
        ax1.add_patch(circle)
    ax1.set_title("1. Layout & Min Distance Circles")
    ax1.legend(loc='upper right')

    # 2. Mapa Wag (Gdzie zależy nam na zasięgu?)
    ax2 = axes[0, 1]
    im2 = ax2.imshow(floor.cover, cmap='viridis')
    ax2.scatter(rx, ry, c='red', marker='*', s=120, edgecolors='black')
    ax2.set_title("2. Priority Zones (Weights)")
    plt.colorbar(im2, ax=ax2, fraction=0.046, pad=0.04)

    # 3. Heatmapa Zasięgu
    ax3 = axes[1, 0]
    im3 = ax3.imshow(coverage_map, cmap='plasma', vmin=0)
    ax3.scatter(rx, ry, c='cyan', marker='x', s=80)
    ax3.set_title("3. Final Signal Strength")
    plt.colorbar(im3, ax=ax3, fraction=0.046, pad=0.04, label='Signal (dB equivalent)')

    # 4. Wykres zbieżności
    ax4 = axes[1, 1]
    if history and 'best_values' in history:
        iters = history['iterations']
        ax4.plot(iters, history['current_values'], color='lightgray', label='Current')
        ax4.plot(iters, history['best_values'], color='blue', linewidth=2, label='Best Found')
        ax4.set_title("4. Optimization Process")
        ax4.set_xlabel("Iteration")
        ax4.set_ylabel("Score")
        ax4.legend()
        ax4.grid(True, alpha=0.3)

    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.show()

# ==========================================
# MAIN EXECUTION
# ==========================================
if __name__ == "__main__":
    print(f"--- START SYMULACJI ---")
    
    # 1. Generowanie Środowiska
    walls, r_poss, covers = generate_office_layout(MAP_SIZE, num_rooms=10)
    
    pietro0 = Floor(
        wall_matrix=walls,
        router_matrix=r_poss,
        cover_matrix=covers,
        Floor_number=0,
        Floor_thickness=0.3
    )
    
    budynek = Building(
        Floors=[pietro0], 
        Floor_heights=3.0, 
        available_routers=[]
    )

    # 2. Tworzenie Routerów
    routers = [
        Router(Power=ROUTER_POWER, Max_users=20, Max_range=ROUTER_RANGE)
        for _ in range(NUM_ROUTERS)
    ]
    budynek.available_routers = routers

    # 3. Inicjalizacja Algorytmu
    optimizer = TabuSearch(
        building=budynek,
        available_routers=routers,
        tabu_length=TABU_LEN,
        max_iterations=MAX_ITER,
        min_distance=MIN_DIST  # Przekazujemy parametr odległości!
    )

    # 4. Uruchomienie
    print("Uruchamiam Tabu Search...")
    # Metoda run automatycznie wywoła weighted_random_initial_solution
    best_solution, best_score, history, asp_ops = optimizer.run()

    # 5. Wyniki
    start_score = history['best_values'][0] if history['best_values'] else 0
    gain_pct = ((best_score - start_score) / start_score * 100) if start_score > 0 else 0

    print("\n" + "="*40)
    print(f" WYNIKI")
    print("="*40)
    print(f" Start (Weighted Random): {start_score:.2f}")
    print(f" Koniec (Optimized):    {best_score:.2f}")
    print(f" Poprawa:               {gain_pct:.1f}%")
    print(f" Użycia aspiracji:      {asp_ops}")
    print("="*40)

    # 6. Wizualizacja
    print("Rysowanie wykresów...")
    plot_dashboard(budynek, routers, history, best_score)