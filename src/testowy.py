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


# Teraz mini testy do funkcji drugiej - agregującej nalezy stworzyć liste krotek - macierz i jej lewy górny róg - to co zwraca local_router_range
local_ranges = [
    (np.array([[7, 7, 7, 7], [8, 8, 8, 7], [8, 9, 8, 7], [8, 8, 8, 7]]), (4, 0)),
    (np.array([[7, 8, 8, 8], [7, 8, 9, 8], [7, 8, 8, 8], [7, 7, 7, 7]]), (0, 4)),
    (np.array([[7, 7, 7, 7], [7, 8, 8, 8], [7, 8, 9, 8], [7, 8, 8, 8]]), (4, 4))
]



router_square1, router_point1 = functions.local_router_range(budynek, router_point=data_matrices.Point(1,6, 0), R_max=5)
router_square2, router_point2 = functions.local_router_range(budynek, router_point=data_matrices.Point(6,1, 0), R_max=5)
router_square3, router_point3 = functions.local_router_range(budynek, router_point=data_matrices.Point(6,6, 0), R_max=5)

local_ragnes2 = [(router_square1, router_point1), (router_square2, router_point2), (router_square3, router_point3)]

print(router_point1)
print(router_point2)
print(router_point3)

print(router_square1)
print(router_square2)
print(router_square3)

agregation_matrix = functions.agregation_func(budynek, local_ragnes2)
print(agregation_matrix)

print(functions.goal_function(budynek.Floor_list[0], agregation_matrix))
