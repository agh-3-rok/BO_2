from dataclasses import dataclass
from .enums import TabuStrategy, AspirationStrategy, InitialSolutionStrategy, LocalChangeStrategy, ObjectiveStrategy

@dataclass
class SimulationConfig:
    """Klasa przechowująca wszystkie parametry symulacji w jednym miejscu."""
    
    # --- Parametry Algorytmu Tabu Search ---
    # objective_strategy: ObjectiveStrategy = ObjectiveStrategy.    
    objective_strategy: ObjectiveStrategy = ObjectiveStrategy.THRESHOLD_COVERAGE

    tabu_strategy: TabuStrategy = TabuStrategy.BLOCK_ROUTER_ID
    aspiration_strategy: AspirationStrategy = AspirationStrategy.LOCAL_GAIN
    # init_strategy: InitialSolutionStrategy = InitialSolutionStrategy.WEIGHTED_RANDOM_INITIALIZATION
    init_strategy: InitialSolutionStrategy = InitialSolutionStrategy.RANDOM_INITIALIZATION
    # local_change_strategy: LocalChangeStrategy = LocalChangeStrategy.SMART_LOCAL_CHANGE
    local_change_strategy: LocalChangeStrategy = LocalChangeStrategy.RANDOM_LOCAL_CHANGE

    max_iterations: int = 100
    tabu_length: int = 10
    
    # Parametry specyficzne dla strategii
    block_area_radius: float = 5.0                  # obszar jaki blokuje się gdy jako tabu wybieramy wlasnie blokowanie obszaru (podaje sie promień obszaru)
    aspiration_threshold: float = 1.05              # parametr o ile % musi być lepiej (1.3 = 30% poprawy)
    aspiration_usability_threshold: float = 50.0    # parametr który mówi jak musi się poprawić ruter który wcześniej był bezużyteczny

    # --- Parametry Środowiska / Budynku ---
    num_routers: int = 5                            # Liczba ruterów do umieszczenia
    router_range: int = 39                          # Zasięg rutera (kratki w macierzy)  
    coverage_threshold_db: float = -60.0            # Próg sygnału (dBm) powyżej którego punkt jest uznawany za pokryty (basic - skalowanie)
    coverage_threshold_step_db: float = 3.0         # Krok sygnału (dBm)

    floor_damping: float = 2.0                  # Tłumienie stropu (fizyka)
    min_distance: float = 4.0                   # Minimalna odległość między ruterami
    floor_heights: float = 3.0                  # Wysokość piętra domyślna (metry)
    floor_width: int = 20                       # Szerokość piętra (metry)
    floor_length: int = 20                      # Długość piętra (metry)
    floor_thickness: float = 0.3                # Grubość stropu (metry)