from enum import Enum

class TabuStrategy(Enum):
    BLOCK_ROUTER_ID = 1      # Zablokuj konkretny ID routera 
    BLOCK_AREA_RADIUS = 2    # Zablokuj stare miejsce i jego okolicę 

class AspirationStrategy(Enum):
    GLOBAL_BEST = 1          # Akceptuj tylko jeśli pobijesz najlepszy wynik
    LOCAL_GAIN = 2           # Akceptuj jeśli pobijesz najlepszy wynik lub jeśli router drastycznie zyskał
    
class InitialSolutionStrategy(Enum):
    RANDOM_INITIALIZATION = 1               # Ta metoda inicjalizacji rozrzuca rutery w losowe miejsca na mapie
    WEIGHTED_RANDOM_INITIALIZATION = 2      # Ta inicjalizacja bierze również pod uwagę macierz cover i na jej podstawie losowo rozrzuca rutery 
# z większym prawdopodobieństwem w miejscach gdzie są one bardziej potrzebne

class LocalChangeStrategy(Enum):
    RANDOM_LOCAL_CHANGE = 1     # Lokalna zmiana polega na przeniesieniu losowego rutera w dowolne wolne miejsce
    SMART_LOCAL_CHANGE = 2      # Lokalna zmiana polega na przenoszeniu ruterów, które mają najgorszą użyteczność liczoną przy wykorzystaniu macierzy cover
    