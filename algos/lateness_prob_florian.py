from utils import *
import math
from scipy.stats import norm


# Модифицированный Spiess-Florian (минимизация вероятности опоздания)

def calculate_lateness_probability(mean_time, std_time, arrival_deadline):
    """
    Рассчитывает вероятность опоздания для заданного времени в пути
    
    Возвращает вероятность НЕ опоздания (вероятность прибытия вовремя)
    """
    if std_time <= 0:
        return 1.0 if mean_time <= arrival_deadline else 0.0
    
    prob_on_time = norm.cdf(arrival_deadline, loc=mean_time, scale=std_time)
    return prob_on_time

def find_optimal_strategy(all_links, all_stops, destination, arrival_deadline):
    if VERBOSE:
        print("Initialization for lateness probability model")

    # Инициализация: вероятность прибытия вовремя из destination равна 1.0
    u = {stop: 1.0 if stop == destination else 0.0 for stop in all_stops}
    f = {stop: 0.0 for stop in all_stops}

    overline_a = []

    links_by_to_node = {}
    for link in all_links:
        if link.to_node in all_stops and link.from_node in all_stops:
            if link.to_node not in links_by_to_node:
                links_by_to_node[link.to_node] = []
            links_by_to_node[link.to_node].append(link)

    # Вместо u[link.to_node] + link.travel_cost, используем вероятность прибытия вовремя
    pq = PriorityQueue()
    for link in all_links:
        if link.to_node in all_stops:
            prob = calculate_lateness_probability(link.mean_travel_time, link.std_travel_time, arrival_deadline)
            pq.push(link, -prob)

    iteration = 0
    max_iterations = 10000

    while iteration < max_iterations:
        link, neg_priority = pq.pop()
        if link is None:
            break
            
        priority = -neg_priority
        
        a = link
        i = a.from_node
        j = a.to_node

        if i not in all_stops or j not in all_stops:
            continue

        # Рассчитываем вероятность прибытия вовремя из остановки i через дугу a
        # Это зависит от:
        # 1. Вероятности прибытия вовремя из остановки j (u[j])
        # 2. Вероятности успешно пройти дугу a (включая ожидание и движение)
        
        waiting_mean = a.headway / 2.0 if a.headway > 0 else 0
        waiting_std = a.headway / math.sqrt(12) if a.headway > 0 else 0
        
        total_mean = waiting_mean + a.mean_travel_time
        total_std = math.sqrt(waiting_std**2 + a.std_travel_time**2)
        
        prob_arrive_via_a = calculate_lateness_probability(total_mean, total_std, arrival_deadline)
    
        new_u_i = u[j] * prob_arrive_via_a
        
        if u[i] >= new_u_i:
            continue

        if VERBOSE:
            print(f"Process: a = ({i}, {j})")
            print(f"  u_i >= u_j * prob_arrive_via_a : {u[i]} < {u[j]} * {prob_arrive_via_a} - FALSE")

        u[i] = new_u_i
        
        freq = INFINITE_FREQUENCY if a.headway <= 0 else 1 / a.headway
        f[i] = freq if freq < INFINITE_FREQUENCY else 1.0
        
        if VERBOSE:
            print(f"  f_a = {freq}")

        overline_a.append(a)

        if i in links_by_to_node:
            for update_link in links_by_to_node[i]:
                if update_link.to_node in all_stops and update_link.from_node in all_stops:

                    waiting_mean_upd = update_link.headway / 2.0 if update_link.headway > 0 else 0
                    waiting_std_upd = update_link.headway / math.sqrt(12) if update_link.headway > 0 else 0

                    total_mean_upd = waiting_mean_upd + update_link.mean_travel_time
                    total_std_upd = math.sqrt(waiting_std_upd**2 + update_link.std_travel_time**2)
                    
                    prob_upd = calculate_lateness_probability(total_mean_upd, total_std_upd, arrival_deadline)
                    pq.update(update_link, -u[i] * prob_upd)

    iteration += 1

    return Strategy(u, f, overline_a)

def assign_demand(all_links, all_stops, optimal_strategy, od_matrix, destination):
    """
    Распределение спроса с использованием стратегии, основанной на вероятности опоздания
    """
    # Сортируем a_set по убыванию вероятности (вместо возрастания стоимости)
    optimal_strategy.a_set = sorted(
        optimal_strategy.a_set,
        key=lambda a: -(optimal_strategy.labels[a.to_node]),
        reverse=True
    )
    return calculate_flow_volumes(all_links, all_stops, optimal_strategy, od_matrix, destination)
    
    
def compute_sf(all_links, all_stops, destination, od_matrix, arrival_deadline):
    """
    Вычисление стратегии с учетом вероятности опоздания
    """
    ops = find_optimal_strategy(all_links, all_stops, destination, arrival_deadline)
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