import numpy as np
import random
import data_matrices
import algorithms
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors

# --- KONFIGURACJA ---
MAP_SIZE = 50      # Rozmiar mapy (np. 100x100)
NUM_ROUTERS = 5     # Liczba routerów do rozmieszczenia
ROUTER_RANGE = 50   # Zasięg routera (promień w kratkach)
WALL_DAMPING = 2.0  # Współczynnik tłumienia ścian
ROUTER_POWER = 30   # Moc routera w dBm
STEP = 100          # Co ile kratek skacze metoda greedy
MAX_ITERATIONS = 1000 # Liczba iteracji algorytmu


def generate_office_layout(size, num_rooms=15):
    """
    Generuje losową mapę biura z pokojami i korytarzami.
    """
    # 1. Puste mapy
    wall_matrix = np.zeros((size, size), dtype=float)
    cover_matrix = np.zeros((size, size), dtype=int)
    router_matrix = np.ones((size, size), dtype=int) # Router wszędzie dozwolony
    
    # 2. Generowanie pokoi
    rooms = []
    for _ in range(num_rooms):
        # Losowe wymiary pokoju
        w = random.randint(5, int(size * 0.25))
        h = random.randint(5, int(size * 0.25))
        # Losowa pozycja (upewniamy się, że mieści się na mapie)
        if size - w - 2 < 1 or size - h - 2 < 1: continue # Zabezpieczenie dla małych map
        x = random.randint(1, size - w - 1)
        y = random.randint(1, size - h - 1)
        
        # Rysowanie ścian pokoju (wartość tłumienia)
        wall_matrix[x:x+w+1, y] = WALL_DAMPING       # Górna
        wall_matrix[x:x+w+1, y+h] = WALL_DAMPING     # Dolna
        wall_matrix[x, y:y+h+1] = WALL_DAMPING       # Lewa
        wall_matrix[x+w, y:y+h+1] = WALL_DAMPING     # Prawa
        
        # Dodanie "drzwi" (losowa dziura w ścianie)
        if random.random() > 0.5: # Drzwi poziome (w górnej lub dolnej ścianie)
            door_x = random.randint(x+1, x+w-1)
            wall_y = y if random.random() > 0.5 else y+h
            wall_matrix[door_x, wall_y] = 0
        else: # Drzwi pionowe (w lewej lub prawej ścianie)
            door_y = random.randint(y+1, y+h-1)
            wall_x = x if random.random() > 0.5 else x+w
            wall_matrix[wall_x, door_y] = 0
            
        # Przypisanie wagi pokrycia wewnątrz pokoju
        importance = random.choice([2, 4, 6, 8, 10])
        cover_matrix[x+1:x+w, y+1:y+h] = importance
        
        rooms.append((x, y, w, h))

    # 3. Korytarze (mała waga, ale warto mieć zasięg)
    # Wypełniamy puste miejsca (gdzie nie ma ściany ani pokoju) wagą 1
    mask_empty = (wall_matrix == 0) & (cover_matrix == 0)
    cover_matrix[mask_empty] = 1

    return wall_matrix, router_matrix, cover_matrix

# ==========================================
# NOWA, LEPSZA FUNKCJA WIZUALIZACJI
# ==========================================
def plot_results_improved(building, routers, score):
    """
    Zaawansowana wizualizacja wyników:
    1. Mapa ścian (czarno-biała) + pozycje routerów.
    2. Mapa wag pokrycia (kolorowa) + pozycje routerów.
    3. Heatmapa zasięgu (plasma) + pozycje routerów.
    """
    fig, axes = plt.subplots(1, 3, figsize=(20, 7))
    
    # Tytuł główny dla całej figury
    fig.suptitle(f"Wynik optymalizacji WiFi\nMap: {MAP_SIZE}x{MAP_SIZE} | Routers: {len(routers)} | Final Score: {score:.2f}", 
                 fontsize=16, fontweight='bold', y=0.98)

    # --- Przygotowanie danych ---
    wall_data = building.Floor_list[0].wall
    cover_data = building.Floor_list[0].cover
    coverage_map = building.agregation_func(routers)
    
    # Zbierz współrzędne aktywnych routerów do nałożenia na wykresy
    # UWAGA: matplotlib imshow używa konwencji (kolumna, wiersz) czyli (Y, X)
    router_coords_xy = []
    for r in routers:
        if r.position is not None:
            # r.position.y to kolumna, r.position.x to wiersz
            router_coords_xy.append((r.position.y, r.position.x))

    # --- WYKRES 1: Ściany i przeszkody ---
    # Używamy 'Greys_r' (odwrócone szarości): białe tło, czarne ściany
    im1 = axes[0].imshow(wall_data, cmap='Greys_r', interpolation='nearest', vmin=0)
    axes[0].set_title('1. Layout & Obstacles\n(White=Space, Dark=Wall)', fontsize=12, fontweight='bold')
    axes[0].axis('off')
    
    # Nałożenie markerów routerów
    if router_coords_xy:
        rx, ry = zip(*router_coords_xy)
        axes[0].scatter(rx, ry, c='red', marker='*', s=150, edgecolors='black', linewidth=1, label='Router')
        axes[0].legend(loc='upper right')

    # Pasek koloru dla ścian
    cbar1 = plt.colorbar(im1, ax=axes[0], fraction=0.046, pad=0.04)
    cbar1.set_label('Damping Factor', rotation=270, labelpad=15)

    # --- WYKRES 2: Wagi pokrycia (Cover Weights) ---
    # Używamy 'viridis' - klasyczna, czytelna paleta
    im2 = axes[1].imshow(cover_data, cmap='viridis', interpolation='nearest')
    axes[1].set_title('2. Coverage Priorities (Weights)\n(Higher = More Important)', fontsize=12, fontweight='bold')
    axes[1].axis('off')
    
    # Nałożenie markerów routerów
    if router_coords_xy:
        axes[1].scatter(rx, ry, c='red', marker='*', s=150, edgecolors='black', linewidth=1)

    # Pasek koloru dla wag
    cbar2 = plt.colorbar(im2, ax=axes[1], fraction=0.046, pad=0.04)
    cbar2.set_label('Priority Weight', rotation=270, labelpad=15)

    # --- WYKRES 3: Heatmapa Zasięgu (Final Coverage) ---
    # Używamy 'plasma' lub 'jet' dla efektownego wyglądu sygnału radiowego
    # Ustawiamy vmin=0, żeby tło było jednolite, a vmax trochę powyżej średniej dla kontrastu
    vmax_val = np.percentile(coverage_map[coverage_map > 0], 95) if np.any(coverage_map > 0) else 1
    im3 = axes[2].imshow(coverage_map, cmap='plasma', interpolation='bilinear', vmin=0, vmax=vmax_val)
    axes[2].set_title('3. Final Signal Heatmap\n(Brighter = Stronger Signal)', fontsize=12, fontweight='bold')
    axes[2].axis('off')

    # Nałożenie markerów routerów (tutaj np. cyjan dla kontrastu z plasmą)
    if router_coords_xy:
        axes[2].scatter(rx, ry, c='cyan', marker='*', s=180, edgecolors='black', linewidth=1.5, zorder=10)

    # Pasek koloru dla zasięgu
    cbar3 = plt.colorbar(im3, ax=axes[2], fraction=0.046, pad=0.04)
    cbar3.set_label('Signal Strength (Aggregated)', rotation=270, labelpad=15)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95]) # Miejsce na tytuł główny
    plt.show()

# ==========================================
# GŁÓWNY KOD URUCHOMIENIOWY
# ==========================================

# --- GENEROWANIE DANYCH ---
print(f"Generowanie mapy {MAP_SIZE}x{MAP_SIZE}...")
# Poprawiłem wywołanie funkcji generate_office_layout (używała globalnego MAP_SIZE zamiast argumentu size)
wall, router_poss, cover = generate_office_layout(MAP_SIZE, num_rooms=18)

pietro = data_matrices.Floor(
    wall_matrix=wall,
    router_matrix=router_poss,
    cover_matrix=cover,
    Floor_number=0,
    Floor_thickness=0.3,
)

budynek = data_matrices.Building(
    Floors=[pietro],
    Floor_heights=3.0,
    available_routers=[]
)

# Tworzenie routerów
routers_list = []
for i in range(NUM_ROUTERS):
    r = data_matrices.Router(Power=ROUTER_POWER, Max_users=10, Max_range=ROUTER_RANGE)
    routers_list.append(r)

budynek.available_routers = routers_list

# --- URUCHOMIENIE ALGORYTMU ---
# Upewnij się, że w TabuSearch masz metody:
# - greedy_initial_solution (zamiast initial_solution, jest dużo lepsza)
# - smart_local_change
# - restore_solution_state
# Oraz w Building metodę calculate_router_usefulness

tabu = algorithms.TabuSearch(
    building=budynek, 
    available_routers=routers_list, 
    max_iterations=MAX_ITERATIONS,  # Mniej iteracji na dużej mapie dla testu
    tabu_length=10
)

print("-" * 40)
print("1. Obliczanie rozwiązania ZACHŁANNEGO (Greedy)...")
print("To może chwilę potrwać na dużej mapie...")
# Zalecam użycie greedy_initial_solution jeśli ją zaimplementowałeś


tabu.weighted_random_initial_solution() # lub tabu.initial_solution() - greedy lepsze wykorzystuje uzytecznosc rutera, jako argument przyujmuje krok z jakim ustawia rutery
initial_val = tabu.evaluate_solution()
print(initial_val)

print(f"-> Wartość startowa: {initial_val:.2f}")

print("\n" + "-" * 40)
print("2. Uruchamianie TABU SEARCH (Optymalizacja)...")
print(f"Szukanie poprawy przez {tabu.max_iterations} iteracji...")

# Zakładam, że Twoja metoda run() zwraca te 4 wartości
best_sol, best_val, history, asp_cnt = tabu.run()

print("\n" + "="*40)
print("   WYNIKI KOŃCOWE   ")
print("="*40)
print(f"Startowa wartość: {initial_val:.1f}")
print(f"Końcowa wartość:  {best_val:.1f}")
improvement = best_val - initial_val
print(f"Poprawa o:        {improvement:+.1f}")
if initial_val > 0:
    print(f"Zysk procentowy:  {((improvement) / initial_val * 100):+.2f}%")

# --- WIZUALIZACJA ---
print("\nGenerowanie wizualizacji...")
# Upewnij się, że przekazujesz listę routerów, która ma zaktualizowane pozycje
# (Twoja metoda run powinna to zapewniać na końcu działania)
plot_results_improved(budynek, routers_list, best_val)