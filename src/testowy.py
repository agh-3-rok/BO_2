import numpy as np
import data_matrices
import algorithms



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

cover_matrix = np.array(
    [
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 3, 3, 0, 3, 3, 5, 0],
        [0, 3, 3, 0, 4, 4, 5, 0],
        [0, 3, 3, 0, 0, 0, 0, 0],
        [0, 4, 4, 3, 3, 4, 4, 0],
        [0, 5, 4, 3, 3, 5, 5, 0],
        [0, 5, 4, 3, 3, 5, 5, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
    ],
    dtype=int,
)


pietro = data_matrices.Floor(
    wall_matrix=wall_matrix,
    router_matrix=router_matrix,
    cover_matrix=cover_matrix,
    Floor_number=1,
    Floor_thickness=0.3,
)

# Dostępne routery do wykorzystania
available_routers = [
    data_matrices.Router(Power=10, Max_users=5, Max_range=5),
    data_matrices.Router(Power=10, Max_users=5, Max_range=5),
    data_matrices.Router(Power=10, Max_users=5, Max_range=5),
]

budynek = data_matrices.Building(
    Floors=[pietro],
    Floor_heights=2.5,
    available_routers=available_routers
)

# Tworzenie routerów w poszczególnych pozycjach
ruter1 = data_matrices.Router(Power=10, Max_users=5, Max_range=5)
ruter1.position = data_matrices.Point(1, 1, 0)
ruter1.calculate_coverage(building=budynek)

ruter2 = data_matrices.Router(Power=10, Max_users=5, Max_range=5)
ruter2.position = data_matrices.Point(6, 1, 0)
ruter2.calculate_coverage(building=budynek)

ruter3 = data_matrices.Router(Power=10, Max_users=5, Max_range=5)
ruter3.position = data_matrices.Point(6, 6, 0)
ruter3.calculate_coverage(building=budynek)

tabu = algorithms.TabuSearch(building=budynek, available_routers=[ruter1, ruter2, ruter3], max_iterations=100, tabu_length=10)

tabu.weighted_random_initial_solution()
print(tabu.current_solution)
print(tabu.evaluate_solution())
best_solution, best_value, history, aspiration_cnt = tabu.run()
print(best_solution)
print(best_value)
print(aspiration_cnt)

    