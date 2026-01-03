import numpy as np
import matplotlib.pyplot as plt
import pandas as pd # Opcjonalnie do ładnej tabelki, ale użyjemy printa jeśli nie masz pandas
from data_matrices import Building, Floor, Router
from algorithms import TabuSearch, TabuStrategy, AspirationStrategy

# --- KONFIGURACJA TESTU ---
NUM_RUNS = 30           # Ile razy powtórzyć każdy test (im więcej tym rzetelniej)
MAX_ITER = 100          # Liczba iteracji w jednym przebiegu
MAP_SIZE = 30
NUM_ROUTERS = 5
ROUTER_RANGE = 10

def create_environment():
    """Tworzy czyste środowisko testowe (2 piętra)."""
    floors = []
    for f in range(2):
        wall = np.zeros((MAP_SIZE, MAP_SIZE))
        # Proste ściany
        wall[10:20, 10:20] = 5.0 
        
        cover = np.zeros((MAP_SIZE, MAP_SIZE), dtype=int)
        if f == 0: cover.fill(5)   # Parter niski priorytet
        else:      cover.fill(50)  # Piętro wysoki priorytet
        
        router_matrix = np.ones((MAP_SIZE, MAP_SIZE), dtype=int)
        floors.append(Floor(wall, router_matrix, cover, f, 0.5))
        
    building = Building(floors, 3.0, [])
    routers = [Router(20, 20, ROUTER_RANGE) for _ in range(NUM_ROUTERS)]
    building.available_routers = routers
    return building, routers

def run_benchmark():
    # Definicja scenariuszy do porównania
    scenarios = [
        {
            "name": "1. Classic",
            "tabu": TabuStrategy.BLOCK_ROUTER_ID,
            "asp": AspirationStrategy.GLOBAL_BEST,
            "color": "gray"
        },
        {
            "name": "2. Spatial Tabu",
            "tabu": TabuStrategy.BLOCK_AREA_RADIUS,
            "asp": AspirationStrategy.GLOBAL_BEST,
            "color": "blue"
        },
        {
            "name": "3. Full Modern",
            "tabu": TabuStrategy.BLOCK_AREA_RADIUS,
            "asp": AspirationStrategy.LOCAL_GAIN,
            "color": "green"
        }
    ]

    results_data = {s["name"]: {"scores": [], "aspirations": []} for s in scenarios}

    print(f"Rozpoczynam benchmark: {NUM_RUNS} uruchomień dla każdego z {len(scenarios)} scenariuszy...")
    print("=" * 70)

    for s_idx, scenario in enumerate(scenarios):
        print(f"Testowanie: {scenario['name']}...", end="", flush=True)
        
        for i in range(NUM_RUNS):
            # 1. Czyste środowisko dla każdego uruchomienia
            building, routers = create_environment()
            
            # 2. Inicjalizacja
            opt = TabuSearch(
                building=building,
                available_routers=routers,
                tabu_length=15,
                max_iterations=MAX_ITER,
                min_distance=3.0,
                tabu_strategy=scenario['tabu'],
                aspiration_strategy=scenario['asp']
            )
            
            # 3. Uruchomienie (bez printów w środku run() żeby nie śmiecić)
            # Warto zakomentować printy w optimizer.py na czas benchmarku!
            opt.weighted_random_initial_solution() # Start
            # Reset flagi rozwiązania startowego wewnątrz, symulacja czystego startu
            opt.current_solution = list(opt.best_solution)
            
            # Run
            _, best_val, _, asp_cnt = opt.run()
            
            # Zbieranie danych
            results_data[scenario["name"]]["scores"].append(best_val)
            results_data[scenario["name"]]["aspirations"].append(asp_cnt)
            
            # Kropka postępu
            if i % 5 == 0: print(".", end="", flush=True)
            
        print(" Gotowe!")

    # --- RAPORT ---
    print("\n" + "=" * 70)
    print(f"{'SCENARIO':<20} | {'AVG SCORE':<10} | {'MAX SCORE':<10} | {'AVG ASPIRATIONS'}")
    print("-" * 70)
    
    for name, data in results_data.items():
        avg_score = np.mean(data["scores"])
        max_score = np.max(data["scores"])
        avg_asp = np.mean(data["aspirations"])
        print(f"{name:<20} | {avg_score:<10.1f} | {max_score:<10.1f} | {avg_asp:.2f}")

    # --- WYKRESY ---
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    # 1. Boxplot wyników (Pokazuje stabilność i jakość)
    score_lists = [results_data[s["name"]]["scores"] for s in scenarios]
    names = [s["name"] for s in scenarios]
    colors = [s["color"] for s in scenarios]
    
    bplot = ax1.boxplot(score_lists, patch_artist=True, labels=names)
    
    # Kolorowanie boxplota
    for patch, color in zip(bplot['boxes'], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)
        
    ax1.set_title(f"Rozkład Wyników (Score) - {NUM_RUNS} prób")
    ax1.set_ylabel("Funkcja Celu (Im więcej tym lepiej)")
    ax1.grid(True, linestyle='--', alpha=0.7)

    # 2. Barplot aspiracji (Pokazuje czy mechanizm działa)
    avg_asps = [np.mean(results_data[s["name"]]["aspirations"]) for s in scenarios]
    bars = ax2.bar(names, avg_asps, color=colors, alpha=0.7)
    
    ax2.set_title("Średnia liczba użyć Kryterium Aspiracji")
    ax2.set_ylabel("Liczba zaakceptowanych ruchów Tabu")
    ax2.bar_label(bars, fmt='%.2f')
    
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    run_benchmark()