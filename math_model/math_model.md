## Problem: optymalizacja rozkładu n routerów na piętrze (2D)

### Cel
Rozmieścić n routerów w dwuwymiarowej siatce piętra budynku tak, aby maksymalizować wygenerowany zasięg tam, gdzie jest on pożądany, oraz minimalizować tam, gdzie jest niepożądany, z uwzględnieniem ścian i ich tłumienia.

---

## Dane wejściowe
- `M_{i,j}` — bit mapa (macierz) rozmiaru N × M:
	- elementy `M_{i,j}` to współczynniki kary i nagrody określające, gdzie chcemy mieć silny zasięg (dodatnie wagi) oraz gdzie go nie chcemy (ujemne / niskie wagi).
	- dodatkowo mapa zawiera informację o położeniu ścian (np. binarnie) oraz ewentualnie grubości ścian `d` w miejscach, gdzie występują.
- `n` — liczba routerów do rozmieszczenia.
- `a` — stała fizyczna określająca siłę sygnału źródła (bez tłumienia).
- `b` — stała tłumienia związana ze ścianami (może być skalarna lub zależna od materiału).
- (opcjonalnie) rozdzielczość siatki, ograniczenia pozycji (np. tylko miejsca bez ścian), minimalne odległości między routerami.

---

## Zmienne decyzyjne i notacja
- `X_k = (x_k, y_k)` — współrzędne k-tego routera; razem tworzą macierz `X_{k,l}` o rozmiarze n×2 (k = 1..n, l ∈ {x,y}).
- Dla punktu siatki o indeksach `(i, j)` definiujemy odległość euklidesową do routera k:
	$$
	r_{(i,j),k} = \left\| (i,j) - X_k \right\|_2 = \sqrt{(i - x_k)^2 + (j - y_k)^2}.
	$$

---

## Model zasięgu

### 1) Zasięg bez uwzględnienia ścian
Dla punktu `(i,j)` oraz routera `k`, zasięg (moc) bez przeszkód definiujemy jako:
$$
ZM(i,j,k) = \frac{a}{r_{(i,j),k}}.
$$
(Uwaga: w praktyce można użyć innego spadku z odległością, np. `a / r^2` lub logarytmicznego modelu; tu przyjmujemy podany wzór.)

### 2) Ujęcie tłumienia przez ściany
Jeżeli linia łącząca router `k` i punkt `(i,j)` przecina jedną lub więcej ścian, uwzględniamy tłumienie. Dla każdej ścianki przecinającej trasę możemy mieć jej grubość `d_p` i współczynnik tłumienia `b_p`; ogólnie tworzy to łączny efekt tłumienia.

- Ogólna zapisowa postać: zmieniamy stałą `a` na `a'` zależnie od natężenia tłumienia wzdłuż trasy:
	$$
	a' = A\big(a,\{b_p,d_p\}_{p\in \text{ścieżka}}\big).
	$$
- Typowy model (eksponencjalne tłumienie) to:
	$$
	a' = a \cdot \exp\Big(-\sum_{p\in \text{ścieżka}} b_p \, d_p\Big).
	$$
	(Tu sumujemy produkty współczynnika tłumienia i grubości dla każdej przeciętej ścianki.)

Wtedy zasięg z uwzględnieniem ścian od routera `k` w punkcie `(i,j)` zapisujemy jako funkcję:
$$
ZP(i,j,k; X) = \frac{a'(i,j,k;X)}{r_{(i,j),k}}.
$$
gdzie `a'` zależy od routera `k`, punktu `(i,j)` i aktualnego rozmieszczenia routerów lub konfiguracji środowiska `X` (w praktyce zależy jedynie od trasy między `X_k` i `(i,j)`, więc od `X_k`).

---

## Agregacja sygnału od wielu routerów
Dla danego punktu `(i,j)` uzyskujemy sygnał jako maksimum z wartości od wszystkich routerów (przyjmujemy, że sygnały się nie sumują liniowo, a interesuje nas dominujący router):
$$
Z(i,j; X) = \max_{k=1,\dots,n} ZP(i,j,k; X).
$$

(Alternatywnie można rozważyć sumę ważoną, sumę energetyczną itp. — tu zachowujemy oryginalną definicję `max`.)

---

## Funkcja celu
Mając mapę wag `M_{i,j}`, definiujemy funkcję celu jako ważoną sumę zasięgów po wszystkich punktach siatki:
$$
f(X) = \sum_{i=1}^{N} \sum_{j=1}^{M} \; M_{i,j} \; Z(i,j; X).
$$

Celem optymalizacji jest maksymalizacja `f(X)` względem położeń `X = {X_k}_{k=1}^n`:
$$
\maximize_{X} \; f(X)
\quad\text{przy odpowiednich ograniczeniach (np. `X_k` wewnątrz obszaru, dyskretna siatka, brak kolizji z przeszkodami).}
$$

---

## Ograniczenia i uwagi implementacyjne
- Pozycje routerów `X_k` zwykle ograniczamy do punktów siatki `(i,j)` bez ścian lub do ciągłego obszaru wewnątrz pomieszczenia.
- Zasięg modelowany jest odwrotnie proporcjonalnie do odległości; przy `r = 0` warto zdefiniować `r_min`, by uniknąć dzielenia przez zero.
- Obliczanie `a'` wymaga wykrycia, które ścianki przecinają segment łączący `X_k` i punkt `(i,j)`. Należy zastosować algorytm rysowania linii na siatce (np. Bresenham) lub analizę geometryczną z poligonami ścian.
- Złożoność obliczeniowa: dla każdego kroku oceny funkcji celu trzeba policzyć `ZP` dla `n` routerów i dla `N×M` punktów → `O(n·N·M)` per ocena; przy skomplikowanej detekcji ścian koszt wzrasta.
- Dyskretyzacja: jeżeli `X_k` są dyskretne (przyjmują pozycje na siatce), problem jest kombinatoryczny; jeżeli są ciągłe, to problem jest problemem optymalizacji ciągłej z zwartym zbiorem dopuszczalnym.

---

## Propozycje metod optymalizacji
Ze względu na nieliniowość i potencjalne niegładkości (max, dyskretne przeszkody) sugerowane podejścia:
- Metody heurystyczne/metaheurystyki: algorytmy genetyczne (GA), Particle Swarm Optimization (PSO), Simulated Annealing (SA).
- Metody lokalnego przeszukiwania z restartami (hill-climbing, tabu search).
- Jeśli `X` dyskretne i rozmiary małe, można spróbować przeszukania wyczerpującego lub algorytmów aproksymacyjnych.
- Przy modelu ciągłym i gładkim (np. jeśli zastąpimy `max` sumą), można użyć algorytmów gradientowych (jeśli możliwe różniczkowanie) lub metod pochodnych-uzależnionych.

---

## Przykładowe uwagi praktyczne i edge-cases
- Punkty z `M_{i,j} << 0` (silna kara): algorytm powinien unikać generowania zasięgu w tych obszarach, co można uzyskać przez nadanie ujemnych wartości w `M_{i,j}`.
- Ściany o zmiennych materiałach: `b_p` może zależeć od segmentu ściany; `a'` liczymy z sumarycznego tłumienia.
- Bliskie routery: można dodać karę za zbyt bliskie ustawienie dwóch routerów (regularyzacja).
- Brak linii widzenia (np. pełne zasłonięcie): w modelu eksponencjalnym tłumienie może praktycznie zablokować sygnał (`a' ≈ 0`).
- Unikać dzielenia przez 0 — wprowadzić `r_min`.

---

## Krótka specyfikacja wejścia/wyjścia (kontrakt)
- Wejście:
	- macierz `M_{i,j}` (N×M) z wagami i informacją o ścianach,
	- liczba routerów `n`,
	- parametry `a`, `b` (i ewentualne parametry materiałów ścian).
- Wyjście:
	- `X` — macierz n×2 z koordynatami routerów,
	- wartość funkcji celu `f(X)`.
- Kryteria sukcesu:
	- znalezienie konfiguracji `X` maksymalizującej `f(X)` w dopuszczalnym czasie/zasobach,
	- spełnienie ograniczeń (brak umieszczenia routera w niedozwolonym miejscu).

---