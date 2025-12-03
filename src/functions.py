import data_matrices as dm
import numpy as np

#FUNKCJE 

FLOOR_DAMPING_PARAM = 2.0  #przykładowa wartość tłumienia podłogi między piętrami

# funkcja celu pomocnicza wyliczana w punkcie
def goal_function_point(building: dm.Building, point: dm.Point, router: dm.Point, router_power: float = 0) \
     -> float:
    """
    dostaje building i punkt obliczeń i router od którego liczymy
    liczymy w decybelach zatem logarytmy zwraca w dB
    dostaje building i punnkt i liczy wartosc zasiegu w punkcie
    """ 
    
    distance = building.get_distance(point, router)
    if distance == 0:
          raise ValueError("Distance between point and router cannot be zero.")
    
    damping = building.get_damping(point, router, FLOOR_DAMPING_PARAM)
    
    # Przykładowa formuła na sygnał w dB
    signal_db = - (20 * np.log10(distance) + damping) + router_power

    # TODO trzeba uwzględnić jeszcze jaki to jest router o jakiej mocy!
    # czyli po prostu dodać do signal_db wartość mocy routera w dB
    
    return signal_db
    


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

