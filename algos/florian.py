from utils import *
import math

# Оригинальный Spiess-Florian (минимизация ожидаемого времени)

def find_optimal_strategy(all_links, all_stops, destination):
    if VERBOSE:
        print("Initialization")
    u = {stop: 0.0 if stop == destination else MATH_INF for stop in all_stops}
    f = {stop: 0.0 for stop in all_stops}

    overline_a = []

    links_by_to_node = {}
    for link in all_links:
        if link.to_node in all_stops and link.from_node in all_stops:
            if link.to_node not in links_by_to_node:
                links_by_to_node[link.to_node] = []
            links_by_to_node[link.to_node].append(link)

    pq = PriorityQueue()
    for link in all_links:
        if link.to_node in all_stops:
            pq.push(link, u[link.to_node] + link.travel_cost)

    while True:
        link, priority = pq.pop()
        if link is None or math.isinf(priority) or priority >= MATH_INF:
            break

        a = link
        i = a.from_node
        j = a.to_node
        
        if i not in all_stops or j not in all_stops:
            continue
            
        sum_uc = u[j] + a.travel_cost

        if u[i] < sum_uc:
            continue

        if VERBOSE:
            print(f"Process: a = ({i}, {j})")
            print(f"  u_i < u_j + c_a : {u[i]} < {u[j]} + {a.travel_cost} - FALSE")

        freq = INFINITE_FREQUENCY if a.headway <= 0 else 1 / a.headway

        if VERBOSE:
            print(f"  f_a = {freq}")

        numerator_part = f[i] * u[i]
        if math.isnan(numerator_part):
            numerator_part = ALPHA
        numerator_part2 = freq * (u[j] + a.travel_cost)
        if math.isnan(numerator_part2):
            numerator_part2 = ALPHA
        numerator = numerator_part + numerator_part2
        denominator = f[i] + freq
        u[i] = numerator / denominator if denominator != 0 else ALPHA
        f[i] = denominator

        if VERBOSE:
            print(f"  u_i = {u[i]}")
            print(f"  f_i = {f[i]}")
            print(f"  overlineA += ({i}, {j})")

        overline_a.append(a)

        if i in links_by_to_node:
            for update_link in links_by_to_node[i]:
                if update_link.to_node in all_stops and update_link.from_node in all_stops:
                    pq.update(update_link, u[i] + update_link.travel_cost)

        if VERBOSE:
            print("Node labels:")
            for s in all_stops:
                print(f"{s} -> (u_i, f_i) = ({u[s]}, {f[s]})")

    return Strategy(u, f, overline_a)

def assign_demand(all_links, all_stops, optimal_strategy, od_matrix, destination):
    # Sort a_set by descending (labels[to] + travel_cost)
    optimal_strategy.a_set = sorted(optimal_strategy.a_set, key=lambda a: -(optimal_strategy.labels[a.to_node] + a.travel_cost))

    return calculate_flow_volumes(all_links, all_stops, optimal_strategy, od_matrix, destination)


def compute_sf(all_links, all_stops, destination, od_matrix):
    ops = find_optimal_strategy(all_links, all_stops, destination)
    volumes = assign_demand(all_links, all_stops, ops, od_matrix, destination)
    return SFResult(ops, volumes)

def parse_gtfs(directory, limit=10000):
    stop_times, active_trips, all_stops, stop_names, route_names = parse_gtfs_limited(directory, limit)
    all_links = calculate_links(stop_times, active_trips, all_stops)
    all_links = calculate_headways(stop_times, active_trips, all_links)
    

    return all_links, all_stops

if __name__ == "__main__":
    directory = "improved-gtfs-moscow-official"
    all_links, all_stops = parse_gtfs(directory, 100000)

    print("Ищем пару связанных остановок...")
    origin, destination = find_connected_od_pair_with_min_hops(all_links)

    if origin is None or destination is None:
        raise ValueError("Не удалось найти ни одной пары остановок с путём между ними!")

    print(f"Найдена пара: origin={origin}, destination={destination}")

    origins_reaching_dest = get_all_origins_reaching_destination(all_links, destination)

    print(f"Найдено {len(origins_reaching_dest)} остановок, из которых можно доехать до {destination}")

    od_matrix = {}
    for origin in origins_reaching_dest:
        if origin != destination:
            demand = random.uniform(50.0, 500.0)
            od_matrix[origin] = {destination: demand}

    print(f"OD-матрица создана: {len(od_matrix)} origin → {destination} (случайный спрос)")
    result = compute_sf(all_links, all_stops, destination, od_matrix)