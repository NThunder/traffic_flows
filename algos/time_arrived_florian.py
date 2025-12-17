from utils import *
import math
from scipy import stats  # Для нормального распределения в модификации

def find_optimal_strategy(all_links, all_stops, destination, T=60.0):
    """
    Модифицированная версия Spiess-Florian: максимизация вероятности прибытия вовремя (reliability).
    
    mean_var[i] = (mean_time, variance_time) — параметры нормального распределения 
                  оставшегося времени от узла i до destination.
    R_i = P(оставшееся время ≤ T) = norm.cdf(T - mean, scale=sqrt(variance))
    """
    # Инициализация: в destination уже на месте
    mean_var = {}
    freqs = {}
    for stop in all_stops:
        if stop == destination:
            mean_var[stop] = (0.0, 0.0)   # mean=0, var=0 → R=1.0
        else:
            mean_var[stop] = (math.inf, 0.0)  # недостижим → R=0.0
        freqs[stop] = 0.0

    attractive_set = []  # \overline{A}

    # Предвычисляем входящие линки по узлам (to_node → список линков, ведущих в него)
    incoming_links = {}
    for link in all_links:
        incoming_links.setdefault(link.to_node, []).append(link)

    # Приоритетная очередь: min-heap по приоритету, где приоритет = -R (чем выше R, тем раньше обрабатываем)
    pq = PriorityQueue()

    # Добавляем в очередь все линки, которые ведут напрямую в destination
    if destination in incoming_links:
        for link in incoming_links[destination]:
            i = link.from_node
            freq = INFINITE_FREQUENCY if link.headway <= 0 else 1.0 / link.headway

            # Ожидание: Uniform(0, headway) → mean = headway/2, var = (headway)^2 / 12
            mean_wait = 0.5 / freq if freq < INFINITE_FREQUENCY else 0.0
            var_wait = (1.0 / freq)**2 / 12.0 if freq < INFINITE_FREQUENCY else 0.0

            tent_mean = mean_wait + link.travel_cost + link.delay_mu + mean_var[destination][0]
            tent_var = var_wait + link.delay_sigma**2 + mean_var[destination][1]

            tent_r = stats.norm.cdf(T - tent_mean, scale=math.sqrt(max(tent_var, 1e-8)))

            # Приоритет = -R (min-heap максимизирует R)
            pq.push(link, -tent_r)

    processed_nodes = set()  # Чтобы избежать бесконечных циклов при плохой сходимости (опционально)

    while True:
        entry = pq.pop()
        if entry[0] is None:
            break
        link, priority = entry
        current_priority_r = -priority  # Текущая оценка R через этот линк

        i = link.from_node  # Узел, который мы пытаемся улучшить
        j = link.to_node    # Уже известный узел

        # Текущая надёжность в i
        curr_mean, curr_var = mean_var[i]
        if curr_mean == math.inf:
            current_r = 0.0
        else:
            current_r = stats.norm.cdf(T - curr_mean, scale=math.sqrt(max(curr_var, 1e-8)))

        # Если текущая R_i уже лучше или равна предлагаемой — пропускаем
        if current_r >= current_priority_r:
            continue

        # Вычисляем параметры через этот линк
        freq = INFINITE_FREQUENCY if link.headway <= 0 else 1.0 / link.headway
        mean_wait = 0.5 / freq if freq < INFINITE_FREQUENCY else 0.0
        var_wait = (1.0 / freq)**2 / 12.0 if freq < INFINITE_FREQUENCY else 0.0

        new_mean_via_link = mean_wait + link.travel_cost + link.delay_mu + mean_var[j][0]
        new_var_via_link = var_wait + link.delay_sigma**2 + mean_var[j][1]


        # Если это первый линк для i
        if freqs[i] == 0.0:
            updated_mean = new_mean_via_link
            updated_var = new_var_via_link
            updated_r = stats.norm.cdf(T - updated_mean, scale=math.sqrt(max(updated_var, 1e-8)))
        else:
            total_freq = freqs[i] + freq
            # Взвешенное среднее для mean
            updated_mean = (freqs[i] * mean_var[i][0] + freq * new_mean_via_link) / total_freq
            # Аппроксимация дисперсии для смеси распределений
            m2_old = mean_var[i][1] + mean_var[i][0]**2
            m2_new = new_var_via_link + new_mean_via_link**2
            updated_m2 = (freqs[i] * m2_old + freq * m2_new) / total_freq
            updated_var = updated_m2 - updated_mean**2
            updated_var = max(updated_var, 0.0)  # Защита от численных ошибок
            updated_r = stats.norm.cdf(T - updated_mean, scale=math.sqrt(max(updated_var, 1e-8)))

        # Если улучшает — принимаем
        if updated_r > current_r + 1e-6:  # Небольшой эпсилон для численной стабильности
            mean_var[i] = (updated_mean, updated_var)
            freqs[i] += freq
            attractive_set.append(link)

            if VERBOSE:
                print(f"Updated node {i}: R = {updated_r:.4f}, mean = {updated_mean:.2f}, std = {math.sqrt(updated_var):.2f}")

            # Обновляем приоритеты всех линков, входящих в i (т.е. те, что могут улучшить предшественников i)
            if i in incoming_links:
                for prev_link in incoming_links[i]:
                    prev_from = prev_link.from_node
                    # Пересчитываем возможную R через prev_link
                    prev_freq = INFINITE_FREQUENCY if prev_link.headway <= 0 else 1.0 / prev_link.headway
                    prev_mean_wait = 0.5 / prev_freq if prev_freq < INFINITE_FREQUENCY else 0.0
                    prev_tent_mean = prev_mean_wait + prev_link.travel_cost + prev_link.delay_mu + updated_mean
                    prev_tent_var = (1.0 / prev_freq)**2 / 12.0 + prev_link.delay_sigma**2 + updated_var
                    prev_tent_var = max(prev_tent_var, 1e-8)
                    prev_tent_r = stats.norm.cdf(T - prev_tent_mean, scale=math.sqrt(prev_tent_var))
                    pq.update(prev_link, -prev_tent_r)

    return Strategy(mean_var, freqs, attractive_set)

def assign_demand(all_links, all_stops, optimal_strategy, od_matrix, destination):
    # Sort a_set by descending expected time (proxy)
    optimal_strategy.a_set = sorted(optimal_strategy.a_set, key=lambda a: -(optimal_strategy.labels[a.to_node][0] + a.travel_cost))

    return calculate_flow_volumes(all_links, all_stops, optimal_strategy, od_matrix, destination)


def compute_sf(all_links, all_stops, destination, od_matrix, T=60):
    ops = find_optimal_strategy(all_links, all_stops, destination, T)
    volumes = assign_demand(all_links, all_stops, ops, od_matrix, destination)
    return SFResult(ops, volumes)

def parse_gtfs(directory, limit=10000):
    stop_times, active_trips, all_stops = parse_gtfs_limited(directory, limit)
    all_links = calculate_links(stop_times, active_trips, all_stops)
    all_links = calculate_headways(stop_times, active_trips, all_links)

    return all_links, all_stops

if __name__ == "__main__":
    directory = "improved-gtfs-moscow-official"
    all_links, all_stops = parse_gtfs(directory)
    od_matrix = { "100457-8017": { "100457-1002179": 1000 } }
    destination = "100457-1002179"
    result = compute_sf(all_links, all_stops, destination, od_matrix)