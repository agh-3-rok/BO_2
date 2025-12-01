import data_matrices as dm

#FUNKCJE 


# funkcja celu wyliczana w punkcie
def goal_function_point(building: dm.Building, point: dm.Point) -> float:
    """
    liczymy w decybelach zatem logarytmy zwraca w dB
    dostaje building i punnkt i liczy wartosc zasiegu w punkcie
    """ 
    pass


# funkcja celu w całości budynku
"""
2 warianty:
- liczysz wszystko
- próbujuesz przyspieszyć liczenie z thresholdem - czyli tylko stosunkowo bliskie
- ewentualnie inny sposób na ułatwienie oblieczeń
"""
def goal_function_building(building: dm.Building) -> float:
    """
    Dostaje building i liczy wszystko 
    z uwzglednieniem wag w punktach -> z building.cover 

    """

    pass

