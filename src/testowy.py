import numpy as np
import random
import data_matrices

# --- KONFIGURACJA ---
MAP_SIZE = 50       # Zmień na 256 jeśli jesteś odważny :) 
NUM_ROUTERS = 5     # Więcej routerów = trudniejszy problem
ROUTER_RANGE = 12   # Zasięg routera w kratkach
WALL_DAMPING = 5.0  # Mocne tłumienie ścian

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
        w = random.randint(4, 10)
        h = random.randint(4, 10)
        x = random.randint(1, size - w - 1)
        y = random.randint(1, size - h - 1)
        
        # Rysowanie ścian pokoju (wartość tłumienia)
        # Górna i dolna ściana
        wall_matrix[x:x+w, y] = WALL_DAMPING
        wall_matrix[x:x+w, y+h] = WALL_DAMPING
        # Lewa i prawa ściana
        wall_matrix[x, y:y+h] = WALL_DAMPING
        wall_matrix[x+w, y:y+h] = WALL_DAMPING
        
        # Dodanie "drzwi" (losowa dziura w ścianie)
        if random.random() > 0.5: # Drzwi poziome
            door_x = random.randint(x+1, x+w-2)
            wall_matrix[door_x, y] = 0
        else: # Drzwi pionowe
            door_y = random.randint(y+1, y+h-2)
            wall_matrix[x, door_y] = 0
            
        # Przypisanie wagi pokrycia wewnątrz pokoju (ważne biura mają wyższą wagę)
        importance = random.choice([3, 5, 8, 10]) # 10 = gabinet prezesa :)
        cover_matrix[x+1:x+w, y+1:y+h] = importance
        
        rooms.append((x, y, w, h))

    # 3. Korytarze (mała waga, ale warto mieć zasięg)
    # Wypełniamy puste miejsca wagą 1
    for i in range(size):
        for j in range(size):
            if wall_matrix[i, j] == 0 and cover_matrix[i, j] == 0:
                cover_matrix[i, j] = 1 # Korytarz/Hol

    return wall_matrix, router_matrix, cover_matrix

# --- GENEROWANIE DANYCH ---
print(f"Generowanie mapy {MAP_SIZE}x{MAP_SIZE}...")
wall, router_poss, cover = generate_office_layout(MAP_SIZE, num_rooms=20)

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
    # Tworzymy routery (na razie bez pozycji)
    r = data_matrices.Router(Power=20, Max_users=10, Max_range=ROUTER_RANGE)
    routers_list.append(r)

budynek.available_routers = routers_list

# --- URUCHOMIENIE ALGORYTMU ---
tabu = data_matrices.TabuSearch(
    building=budynek, 
    available_routers=routers_list, 
    max_iterations=50,  # 50 iteracji wystarczy, żeby zobaczyć efekt
    tabu_length=15      # Dłuższa lista tabu dla większej mapy
)

# 1. Rozwiązanie zachłanne
# Aby przyspieszyć Greedy na dużej mapie, warto ograniczyć próbkowanie (opcjonalnie)
# Ale tutaj puszczamy pełne. Może chwilę potrwać.
print("Obliczanie rozwiązania zachłannego (może potrwać)...")
tabu.greedy_initial_solution()
initial_val = tabu.evaluate_solution()
print(f"Start (Greedy): {initial_val:.2f}")

# 2. Tabu Search
print("\nUruchamianie Tabu Search (optymalizacja)...")
# Upewnij się, że masz zaimplementowane metody z poprzednich odpowiedzi:
# - run (wersja Best-of-N lub zwykła)
# - smart_local_change
# - restore_solution_state (jeśli używasz Best-of-N)
# - Building.calculate_router_usefulness

best_sol, best_val, history, asp_cnt = tabu.run()

print("\n=== WYNIKI ===")
print(f"Startowa wartość: {initial_val:.2f}")
print(f"Końcowa wartość:  {best_val:.2f}")
print(f"Poprawa o:        {best_val - initial_val:.2f}")
print(f"Zysk procentowy:  {((best_val - initial_val) / initial_val * 100):.2f}%")