import numpy as np
import matplotlib.pyplot as plt

# Importy Twoich klas
from config import SimulationConfig
from data_matrices import Building, Floor, Router
from algorithms import TabuSearch 
from enums import TabuStrategy, AspirationStrategy, InitialSolutionStrategy, LocalChangeStrategy

map_size = 30
num_runs = 50

def create_environment(config: SimulationConfig):
    """
    Tworzy środowisko (budynek) na podstawie konfiguracji.
    """
    floors = []
    
    # Tworzymy 2 piętra dla przykładu
    for f in range(2):
        # 1. Macierz ścian (wall_matrix)
        # Puste piętro z ramką dookoła
        wall_matrix = np.zeros((map_size, map_size), dtype=float)
        wall_matrix[0, :] = 5.0
        wall_matrix[-1, :] = 5.0
        wall_matrix[:, 0] = 5.0
        wall_matrix[:, -1] = 5.0
        
        # Dodajemy jakąś ścianę w środku, żeby było ciekawiej
        if f == 0:
            wall_matrix[10:20, 15] = 8.0  # Gruba ściana na parterze
        
        # 2. Macierz możliwych routerów (router_matrix)
        # Wszędzie można (1), chyba że jest ściana
        router_matrix = np.ones((map_size, map_size), dtype=int)
        
        # 3. Macierz priorytetów (cover_matrix)
        # Parter mniej ważny (5), Piętro 1 ważniejsze (50)
        cover_matrix = np.zeros((map_size, map_size), dtype=int)
        priority = 50 if f == 1 else 5
        cover_matrix.fill(priority)
        
        # Tworzymy obiekt Floor
        # WAŻNE: Kolejność argumentów zgodna z Twoim data_matrices.py:
        # __init__(self, wall_matrix, router_matrix, cover_matrix, Floor_number, Floor_thickness)
        new_floor = Floor(
            wall_matrix,    # wall_matrix
            router_matrix,  # router_matrix
            cover_matrix,   # cover_matrix
            f,              # Floor_number
            0.5             # Floor_thickness
        )
        floors.append(new_floor)

    # Tworzymy budynek
    # WAŻNE: Tutaj przekazujemy 'config', bo Twój __init__ w Building tego wymaga
    building = Building(
        Floors=floors, 
        Floor_heights=3.0, 
        available_routers=[], # Routery dodamy za chwilę
        config=config         # <--- Przekazanie configa
    )
    
    return building

def main():
    # 1. Konfiguracja symulacji
    print(">>> Tworzenie konfiguracji...")
    config = SimulationConfig(
        # Parametry środowiska
        num_routers=3,
        router_range=10,
        floor_damping=2.0,
        
        # Parametry algorytmu
        max_iterations=50,
        tabu_length=10,
        min_distance=4.0, # Upewnij się, że ten parametr jest w dataclass Config
        
        # Strategie (korzystamy z Enums)
        tabu_strategy=TabuStrategy.BLOCK_ROUTER_ID,
        aspiration_strategy=AspirationStrategy.LOCAL_GAIN,
        init_strategy=InitialSolutionStrategy.WEIGHTED_RANDOM_INITIALIZATION,
        local_change_strategy=LocalChangeStrategy.SMART_LOCAL_CHANGE,
        
        # Parametry aspiracji
        aspiration_threshold=1.05,
        aspiration_usability_threshold=50.0,
    )

    # 2. Budowa środowiska
    print(">>> Generowanie budynku...")
    building = create_environment(config)
    
    # 3. Tworzenie routerów
    print(f">>> Tworzenie {config.num_routers} routerów...")
    routers = []
    for _ in range(config.num_routers):
        # Power=20, Max_users=100 (przykładowo), Max_range z configa
        r = Router(Power=20.0, Max_users=100, Max_range=config.router_range)
        routers.append(r)
        
    # Przypisanie routerów do budynku
    building.available_routers = routers

    # 4. Inicjalizacja algorytmu Tabu Search
    print(">>> Inicjalizacja algorytmu Tabu Search...")
    solver = TabuSearch(
        building=building,
        available_routers=routers,
        config=config
    )

    # 5. Uruchomienie
    print(">>> START SYMULACJI")
    best_solution, best_value, history, asp_count = solver.run()
    
    print("\n" + "="*40)
    print("KONIEC SYMULACJI")
    print(f"Najlepszy wynik (funkcja celu): {best_value:.2f}")
    print(f"Liczba użytych aspiracji: {asp_count}")
    print("="*40)

    # 6. Prosty wykres wyników
    if history['best_values']:
        plt.figure(figsize=(10, 6))
        plt.plot(history['best_values'], label='Najlepszy wynik', color='green', linewidth=2)
        plt.plot(history['current_values'], label='Obecny wynik', color='red', alpha=0.3, linestyle='--')
        plt.title(f"Przebieg optymalizacji (Smart Local Change)")
        plt.xlabel("Iteracja")
        plt.ylabel("Wartość funkcji celu")
        plt.legend()
        plt.grid(True)
        plt.show()
    else:
        print("Brak historii do wyświetlenia.")

if __name__ == "__main__":
    main()