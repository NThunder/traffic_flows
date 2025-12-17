from utils import *
import math
from scipy import stats  # Для нормального распределения в модификации

def find_optimal_strategy(all_links, all_stops, destination, T=60):
    if VERBOSE:
        print("1.1 Initialization")
    # mean_var: dict[stop: (mean, var)] for remaining time ~ N(mean, sqrt(var))
    mean_var = {stop: (0.0, 0.0) if stop == destination else (MATH_INF, 0.0) for stop in all_stops} # Вместо labels: dict[stop: (mean, var)]
    f = {stop: 0.0 for stop in all_stops}

    overline_a = []

    # Precompute links by ToNode
    links_by_to_node = {}
    for link in all_links:
        if link.to_node not in links_by_to_node:
            links_by_to_node[link.to_node] = []
        links_by_to_node[link.to_node].append(link)

    # Priority queue: Используем -R для max (min-heap как max-heap)
    pq = PriorityQueue()
    for link in all_links:
        # Initial priority: -P(on time) ≈ -(T - mean)/sqrt(var), но init с inf mean → low R
        pq.push(link, MATH_INF)  # Placeholder, update later

    while True:
        link, priority = pq.pop()
        if link is None or math.isinf(priority) or priority >= MATH_INF:
            break

        a = link
        i = a.from_node
        j = a.to_node

        # Compute current R_i = stats.norm.cdf(T - mean_var[i][0], 0, math.sqrt(mean_var[i][1]) if var>0 else inf)
        current_r = stats.norm.cdf(T - mean_var[i][0], scale=math.sqrt(mean_var[i][1]) if mean_var[i][1] > 0 else 0)

        # Wait approx: Для Exp, но Uniform(0, headway) для var
        freq = INFINITE_FREQUENCY if a.headway <= 0 else 1 / a.headway
        mean_wait = 0.5 / freq if freq < INFINITE_FREQUENCY else 0
        var_wait = (1/freq)**2 / 12 if freq < INFINITE_FREQUENCY else 0

        new_mean = mean_wait + a.travel_cost + a.delay_mu + mean_var[j][0]
        new_var = var_wait + a.delay_sigma**2 + mean_var[j][1]

        # Предполагаем улучшение если new_r > current_r, но для weighted
        # Compute tentative new_mean_var
        if f[i] == 0:
            tent_mean = new_mean
            tent_var = new_var
        else:
            total_f = f[i] + freq
            tent_mean = (f[i] * mean_var[i][0] + freq * new_mean) / total_f
            # Var for mixture approx
            tent_var = (f[i] * (mean_var[i][1] + mean_var[i][0]**2) + freq * (new_var + new_mean**2)) / total_f - tent_mean**2

        tent_r = stats.norm.cdf(T - tent_mean, scale=math.sqrt(tent_var) if tent_var > 0 else 0)

        if tent_r <= current_r:  # Не улучшает reliability
            continue

        # Update
        mean_var[i] = (tent_mean, tent_var)
        f[i] += freq
        overline_a.append(a)

        if VERBOSE:
            print(f"Process: a = ({i}, {j})")
            print(f"  Updated R_i = {tent_r}")

        # Update PQ: priority = -tent_r (для max)
        if i in links_by_to_node:
            for update_link in links_by_to_node[i]:
                # New priority for incoming: -R_i
                pq.update(update_link, -tent_r)

        if VERBOSE:
            print("Node mean_var:")
            for s in all_stops:
                print(f"{s} -> (mean, var) = {mean_var[s]}")

    return Strategy(mean_var, f, overline_a)

def assign_demand(all_links, all_stops, optimal_strategy, od_matrix, destination):
    # Sort a_set by descending expected time (proxy)
    optimal_strategy.a_set = sorted(optimal_strategy.a_set, key=lambda a: -(optimal_strategy.mean_var[a.to_node][0] + a.travel_cost))

    node_volumes = {stop: 0.0 for stop in all_stops}
    for origin in od_matrix:
        if destination in od_matrix[origin]:
            node_volumes[origin] += od_matrix[origin][destination]
            node_volumes[destination] += od_matrix[origin][destination]
    if destination in node_volumes:
        node_volumes[destination] *= -1

    volumes_links = {}
    for link in all_links:
        if link.from_node not in volumes_links:
            volumes_links[link.from_node] = {}
        volumes_links[link.from_node][link.to_node] = 0.0

    for a in optimal_strategy.a_set:
        freq = INFINITE_FREQUENCY if a.headway <= 0 else 1 / a.headway
        if optimal_strategy.freqs[a.from_node] == 0:
            va = 0.0
        else:
            va = (freq / optimal_strategy.freqs[a.from_node]) * node_volumes[a.from_node]
        if VERBOSE:
            print(f"Assigning demand for link: ({a.from_node}, {a.to_node})")
            print(f"  v_({a.from_node}, {a.to_node}) = {va}")
            print(f"  V_{a.to_node} += {va}")
        volumes_links[a.from_node][a.to_node] = va
        node_volumes[a.to_node] += va

    if VERBOSE:
        print("Final node volumes:")
        for k in node_volumes:
            print(f"  V_{k} = {node_volumes[k]}")

    return Volumes(volumes_links, node_volumes)

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