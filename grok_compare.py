import heapq
import math
import csv
from datetime import datetime
import os
from scipy import stats  # Для нормального распределения

# Оригинальный Spiess-Florian (минимизация ожидаемого времени)
class LinkOriginal:
    def __init__(self, from_node, to_node, route_id, travel_cost, headway):
        self.from_node = from_node
        self.to_node = to_node
        self.route_id = route_id
        self.travel_cost = travel_cost
        self.headway = headway

class StrategyOriginal:
    def __init__(self, labels, freqs, a_set):
        self.labels = labels
        self.freqs = freqs
        self.a_set = a_set

def find_optimal_strategy_original(all_links, all_stops, destination):
    u = {stop: 0.0 if stop == destination else MATH_INF for stop in all_stops}
    f = {stop: 0.0 for stop in all_stops}
    overline_a = []
    links_by_to_node = {}
    for link in all_links:
        links_by_to_node.setdefault(link.to_node, []).append(link)
    pq = PriorityQueue()
    for link in all_links:
        pq.push(link, u[link.to_node] + link.travel_cost)
    while True:
        link, priority = pq.pop()
        if link is None or math.isinf(priority) or priority >= MATH_INF:
            break
        a = link
        i = a.from_node
        j = a.to_node
        sum_uc = u[j] + a.travel_cost
        if u[i] < sum_uc:
            continue
        freq = INFINITE_FREQUENCY if a.headway <= 0 else 1 / a.headway
        numerator = f[i] * u[i] + freq * (u[j] + a.travel_cost)
        denominator = f[i] + freq
        u[i] = numerator / denominator if denominator != 0 else ALPHA
        f[i] = denominator
        overline_a.append(a)
        if i in links_by_to_node:
            for update_link in links_by_to_node[i]:
                pq.update(update_link, u[i] + update_link.travel_cost)
    return StrategyOriginal(u, f, overline_a)

# Модифицированный (минимизация вероятности опоздания)
class LinkModified(LinkOriginal):
    def __init__(self, from_node, to_node, route_id, travel_cost, headway, delay_mu=0, delay_sigma=5):
        super().__init__(from_node, to_node, route_id, travel_cost, headway)
        self.delay_mu = delay_mu
        self.delay_sigma = delay_sigma

class StrategyModified:
    def __init__(self, mean_var, freqs, a_set):
        self.mean_var = mean_var
        self.freqs = freqs
        self.a_set = a_set

def find_optimal_strategy_modified(all_links, all_stops, destination, T=60):
    mean_var = {stop: (0.0, 0.0) if stop == destination else (MATH_INF, 0.0) for stop in all_stops}
    f = {stop: 0.0 for stop in all_stops}
    overline_a = []
    links_by_to_node = {}
    for link in all_links:
        links_by_to_node.setdefault(link.to_node, []).append(link)
    pq = PriorityQueue()
    for link in all_links:
        pq.push(link, MATH_INF)
    while True:
        link, priority = pq.pop()
        if link is None or math.isinf(priority) or priority >= MATH_INF:
            break
        a = link
        i = a.from_node
        j = a.to_node
        current_r = stats.norm.cdf(T - mean_var[i][0], scale=math.sqrt(mean_var[i][1]) if mean_var[i][1] > 0 else 0)
        freq = INFINITE_FREQUENCY if a.headway <= 0 else 1 / a.headway
        mean_wait = 0.5 / freq if freq < INFINITE_FREQUENCY else 0
        var_wait = (1/freq)**2 / 12 if freq < INFINITE_FREQUENCY else 0
        new_mean = mean_wait + a.travel_cost + a.delay_mu + mean_var[j][0]
        new_var = var_wait + a.delay_sigma**2 + mean_var[j][1]
        if f[i] == 0:
            tent_mean = new_mean
            tent_var = new_var
        else:
            total_f = f[i] + freq
            tent_mean = (f[i] * mean_var[i][0] + freq * new_mean) / total_f
            tent_var = (f[i] * (mean_var[i][1] + mean_var[i][0]**2) + freq * (new_var + new_mean**2)) / total_f - tent_mean**2
        tent_r = stats.norm.cdf(T - tent_mean, scale=math.sqrt(tent_var) if tent_var > 0 else 0)
        if tent_r <= current_r:
            continue
        mean_var[i] = (tent_mean, tent_var)
        f[i] += freq
        overline_a.append(a)
        if i in links_by_to_node:
            for update_link in links_by_to_node[i]:
                pq.update(update_link, -tent_r)
    return StrategyModified(mean_var, f, overline_a)

# Общая функция assign_demand (работает для обоих)
def assign_demand(all_links, all_stops, optimal_strategy, od_matrix, destination, is_original=True):
    if is_original:
        key_lambda = lambda a: -(optimal_strategy.labels[a.to_node] + a.travel_cost)
    else:
        key_lambda = lambda a: -(optimal_strategy.mean_var[a.to_node][0] + a.travel_cost)
    optimal_strategy.a_set = sorted(optimal_strategy.a_set, key=key_lambda)
    node_volumes = {stop: 0.0 for stop in all_stops}
    for origin in od_matrix:
        if destination in od_matrix[origin]:
            node_volumes[origin] += od_matrix[origin][destination]
            node_volumes[destination] += od_matrix[origin][destination]
    if destination in node_volumes:
        node_volumes[destination] *= -1
    volumes_links = {}
    for link in all_links:
        volumes_links.setdefault(link.from_node, {})[link.to_node] = 0.0
    for a in optimal_strategy.a_set:
        freq = INFINITE_FREQUENCY if a.headway <= 0 else 1 / a.headway
        va = 0.0 if optimal_strategy.freqs[a.from_node] == 0 else (freq / optimal_strategy.freqs[a.from_node]) * node_volumes[a.from_node]
        volumes_links[a.from_node][a.to_node] = va
        node_volumes[a.to_node] += va
    return Volumes(volumes_links, node_volumes)

# Парсинг GTFS (адаптирован для modified links)
def parse_gtfs(directory):
    # ... (тот же код, что и раньше, но использовать LinkModified вместо Link)
    # В конце: link = LinkModified(from_node, to_node, route_id, travel_cost, headway)
    # Возвращает all_links, all_stops

# Сравнение
def compare_approaches(directory, od_matrix, destination, T=60):
    all_links, all_stops = parse_gtfs(directory)  # Assume modified links
    # Оригинальный
    strategy_orig = find_optimal_strategy_original(all_links, all_stops, destination)
    volumes_orig = assign_demand(all_links, all_stops, strategy_orig, od_matrix, destination, is_original=True)
    # Модифицированный
    strategy_mod = find_optimal_strategy_modified(all_links, all_stops, destination, T)
    volumes_mod = assign_demand(all_links, all_stops, strategy_mod, od_matrix, destination, is_original=False)
    # Сравнение
    print("Сравнение распределений потоков (original vs modified):")
    for from_node in volumes_orig.links:
        for to_node in volumes_orig.links[from_node]:
            v_orig = volumes_orig.links[from_node][to_node]
            v_mod = volumes_mod.links.get(from_node, {}).get(to_node, 0.0)
            print(f"Link ({from_node} -> {to_node}): orig={v_orig}, mod={v_mod}, diff={v_mod - v_orig}")
    # Дополнительно: Средняя P(late) или E[t]
    # Для orig: E[t] = strategy_orig.labels[origin]
    # Для mod: P(late) = 1 - stats.norm.cdf(T - strategy_mod.mean_var[origin][0], scale=math.sqrt(strategy_mod.mean_var[origin][1]))

# Пример запуска
# compare_approaches('path_to_gtfs', {'orig1': {'dest': 100}}, 'dest', 60)