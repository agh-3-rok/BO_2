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
        [0, 0, 0, 0, 0, 0, 1, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 0, 0, 0],
        [0, 1, 0, 0, 0, 0, 1, 0],
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

budynek = data_matrices.Building(
    Floors=[pietro],
    Floor_heights=2.5,
)

# print(budynek.router_possible)
# print(budynek.points_to_calculate)
agregation_matrix = np.array(
    [
        [3, 4, 5, 6, 7, 8, 8, 8],
        [4, 4, 5, 6, 7, 8, 9, 8],
        [5, 5, 5, 6, 7, 8, 8, 8],
        [6, 6, 6, 6, 7, 7, 7, 7],
        [7, 7, 7, 7, 7, 7, 7, 7],
        [8, 8, 8, 7, 7, 8, 8, 8],
        [8, 9, 8, 7, 7, 8, 9, 8],
        [8, 8, 8, 7, 7, 8, 8, 8],
    ]
)


macierz = functions.local_router_range(budynek, data_matrices.Point(1,6, 0), 4)
print(macierz)

# Teraz mini testy do funkcji drugiej - agregującej nalezy stworzyć liste krotek - macierz i jej lewy górny róg - to co zwraca local_router_range
local_ranges = [
    (np.array([[7, 7, 7, 7], [8, 8, 8, 7], [8, 9, 8, 7], [8, 8, 8, 7]]), (4, 0)),
    (np.array([[7, 8, 8, 8], [7, 8, 9, 8], [7, 8, 8, 8], [7, 7, 7, 7]]), (0, 4)),
    (np.array([[7, 7, 7, 7], [7, 8, 8, 8], [7, 8, 9, 8], [7, 8, 8, 8]]), (4, 4))
]

# print(functions.goal_function(budynek.Floor_list[0], agregation_matrix))
# print(functions.agregation_func(budynek, local_ranges))
