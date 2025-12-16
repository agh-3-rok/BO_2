import numpy as np
import data_matrices
import functions



wall_matrix = np.array(
    [
        [5, 5, 5, 5, 5, 5, 5, 5],
        [5, 0, 0, 0, 0, 0, 0, 5],
        [5, 0, 0, 3, 0, 0, 0, 5],
        [5, 0, 0, 3, 3, 3, 3, 5],
        [5, 0, 0, 0, 0, 0, 0, 5],
        [5, 0, 0, 0, 0, 0, 0, 5],
        [5, 0, 0, 0, 0, 0, 0, 5],
        [5, 5, 5, 5, 5, 5, 5, 5],
    ],
    dtype=float,
)

router_matrix = np.array(
    [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 1, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 1, 0, 0],
        [0, 1, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 0, 0, 0, 0],
        [0, 0, 1, 0, 1, 0, 1, 0],
        [0, 1, 0, 1, 1, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ]
)

router_matrix2 = np.ones((router_matrix.shape))

# --- ZMODYFIKOWANE DANE TESTOWE ---

# 1. Mniej oczywista mapa pokrycia (cover)
# Dwa duże skupiska po rogach i jedno kuszące "centrum"
cover_matrix = np.array(
    [
        [5, 5, 5, 0, 0, 0, 4, 4],
        [5, 5, 5, 0, 0, 0, 4, 4],
        [5, 5, 5, 0, 0, 0, 4, 4],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 6, 6, 0, 0, 0], # <--- Pułapka: To jest kuszący środek (waga 6)
        [0, 0, 0, 6, 6, 0, 0, 0], # Zachłanny może chcieć wziąć to pierwsze
        [3, 3, 3, 0, 0, 0, 3, 3],
        [3, 3, 3, 0, 0, 0, 3, 3],
    ],
    dtype=int,
)

# Reszta bez zmian...
pietro = data_matrices.Floor(
    wall_matrix=wall_matrix, # Możesz użyć starej macierzy ścian
    router_matrix=router_matrix2, # Możesz użyć starej macierzy pozycji
    cover_matrix=cover_matrix,
    Floor_number=1,
    Floor_thickness=0.3,
)

budynek = data_matrices.Building(
    Floors=[pietro],
    Floor_heights=2.5,
    available_routers=[]
)

# 2. OGRANICZONA LICZBA ROUTERÓW (Tylko 2!)
# To zmusi algorytm do szukania kompromisów, zamiast pokrycia wszystkiego.
ruter1 = data_matrices.Router(Power=10, Max_users=5, Max_range=4) # Zmniejszyłem też lekko zasięg
ruter1.position = data_matrices.Point(1, 1, 0)
ruter1.calculate_coverage(building=budynek)

ruter2 = data_matrices.Router(Power=10, Max_users=5, Max_range=4)
ruter2.position = data_matrices.Point(6, 1, 0)
ruter2.calculate_coverage(building=budynek)

# Uwaga: Tylko 2 routery na liście!
available_routers = [ruter1, ruter2] 
budynek.available_routers = available_routers

# ... Reszta kodu uruchamiająca Tabu Search ...
tabu = data_matrices.TabuSearch(
    building=budynek, 
    available_routers=available_routers, # Przekazujemy tylko 2
    max_iterations=50, 
    tabu_length=5
)

print("=== START: Greedy Solution ===")
tabu.greedy_initial_solution()
initial_val = tabu.evaluate_solution()
print(f"Rozwiązanie początkowe: {tabu.current_solution}")
print(f"Wartość początkowa: {initial_val}")

print("\n=== START: Tabu Search Run ===")
best_sol, best_val, history, asp_count = tabu.run()

print(f"\nNajlepsze znalezione: {best_sol}")
print(f"Wartość końcowa: {best_val}")
print(f"Poprawa o: {best_val - initial_val}")
    
    