from utils import *
import math
from scipy import stats

def find_optimal_strategy(all_links, all_stops, destination, T=60.0):
    """
    Модифицированная версия Spiess-Florian: максимизация вероятности прибытия вовремя (reliability).
    
    mean_var[i] = (mean_time, variance_time) — параметры нормального распределения
                  оставшегося времени от узла i до destination.
    R_i = P(оставшееся время ≤ T) = norm.cdf(T - mean, scale=sqrt(variance))
    """
    if VERBOSE:
        print("Initialization for arrive time model")

    mean_var = {}
    freqs = {}
    for stop in all_stops:
        if stop == destination:
            mean_var[stop] = (0.0, 0.0)   # mean=0, var=0 → R=1.0
        else:
            mean_var[stop] = (math.inf, 0.0)  # недостижим → R=0.0
        freqs[stop] = 0.0

    attractive_set = []

    incoming_links = {}
    for link in all_links:
        incoming_links.setdefault(link.to_node, []).append(link)

    pq = PriorityQueue2()

    if destination in incoming_links:
        for link in incoming_links[destination]:
            i = link.from_node
            freq = INFINITE_FREQUENCY if link.headway <= 0 else 1.0 / link.headway

            mean_wait = 1 / freq if freq < INFINITE_FREQUENCY else 0.0
            var_wait = 1 / freq if freq < INFINITE_FREQUENCY else 0.0

            tent_mean = mean_wait + link.travel_cost  + mean_var[destination][0]
            tent_var = var_wait + mean_var[destination][1]

            tent_r = stats.norm.cdf(T - tent_mean, scale=math.sqrt(max(tent_var, 1e-8)))

            pq.push(link, -tent_r, tent_mean)

    while True:
        entry = pq.pop()
        if entry[0] is None:
            break
        link, priority, orig_priority = entry
        current_priority_r = -priority
        mean_travel_time_priority = orig_priority

        i = link.from_node
        j = link.to_node

        curr_mean, curr_var = mean_var[i]
        if curr_mean == math.inf:
            current_r = 0.0
        else:
            current_r = stats.norm.cdf(T - curr_mean, scale=math.sqrt(max(curr_var, 1e-8)))

        # sum_uc = mean_travel_time_priority

        if abs(current_r - current_priority_r) <= EPSILON and curr_mean < mean_travel_time_priority:
            continue
        
        if current_r > current_priority_r:
            continue

        if VERBOSE:
            print(f"Process: a = ({i}, {j})")
            print(f"  current_r >= current_priority_r : {current_r} < {current_priority_r} - FALSE")

        freq = INFINITE_FREQUENCY if link.headway <= 0 else 1.0 / link.headway
        mean_wait = 1 / freq if freq < INFINITE_FREQUENCY else 0.0
        var_wait = 1 / freq if freq < INFINITE_FREQUENCY else 0.0

        new_mean_via_link = mean_wait + link.travel_cost + mean_var[j][0]
        new_var_via_link = var_wait + mean_var[j][1]

        if VERBOSE:
            print(f"  f_a = {freq}")
            print(f"  mean_wait = {mean_wait}")
            print(f"  var_wait = {var_wait}")
            print(f"  new_mean_via_link = {new_mean_via_link}")
            print(f"  new_var_via_link = {new_var_via_link}")

        if freqs[i] == 0.0:
            updated_mean = new_mean_via_link
            updated_var = new_var_via_link
            updated_r = stats.norm.cdf(T - updated_mean, scale=math.sqrt(max(updated_var, 1e-8)))
        else:
            total_freq = freqs[i] + freq
            
            updated_mean = (freqs[i] * mean_var[i][0] + freq * new_mean_via_link) / total_freq

            m2_old = mean_var[i][1] + mean_var[i][0]**2
            m2_new = new_var_via_link + new_mean_via_link**2

            updated_m2 = (freqs[i] * m2_old + freq * m2_new) / total_freq
            updated_var = updated_m2 - updated_mean**2
            updated_var = max(updated_var, 0.0)

            updated_r = stats.norm.cdf(T - updated_mean, scale=math.sqrt(max(updated_var, 1e-8)))

        if updated_r > current_r + 1e-6 or (abs(updated_r - current_r) <= EPSILON and updated_mean < curr_mean):
            mean_var[i] = (updated_mean, updated_var)
            freqs[i] += freq
            attractive_set.append(link)

            if VERBOSE:
                print(f"Updated node {i}: R = {updated_r:.4f}, mean = {updated_mean:.2f}, std = {math.sqrt(updated_var):.2f}")

            if i in incoming_links:
                for prev_link in incoming_links[i]:
                    prev_freq = INFINITE_FREQUENCY if prev_link.headway <= 0 else 1.0 / prev_link.headway

                    prev_mean_wait = 1 / prev_freq if prev_freq < INFINITE_FREQUENCY else 0.0
                    prev_tent_mean = prev_mean_wait + prev_link.travel_cost  + updated_mean
                    
                    prev_var_wait = prev_mean_wait  # (1.0 / prev_freq)**2 / 12.0
                    prev_tent_var = prev_var_wait  + updated_var

                    prev_tent_var = max(prev_tent_var, 1e-8)
                    prev_tent_r = stats.norm.cdf(T - prev_tent_mean, scale=math.sqrt(prev_tent_var))

                    pq.update(prev_link, -prev_tent_r, prev_tent_mean)

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