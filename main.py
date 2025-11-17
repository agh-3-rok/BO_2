#TUTAJ ODPALI SIĘ ALGORYTM PO IMPORCIE FUNKCJI I DANYCH
import numpy as np


from BO_2.src import data_matrices as dm

f = dm.floor(np.array([[0,1],[1,0]]), np.array([[1,0],[0,1]]), np.array([[1,1],[1,1]]))

print(f.wall[0,1])

