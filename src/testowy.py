import numpy as np
import data_matrices


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

print(budynek.router_possible)
print(budynek.points_to_calculate)