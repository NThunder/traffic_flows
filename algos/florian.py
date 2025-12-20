from utils import *
import math

# Оригинальный Spiess-Florian (минимизация ожидаемого времени)

def find_optimal_strategy(all_links, all_stops, destination):
    if VERBOSE:
        print("1.1 Initialization")
    u = {stop: 0.0 if stop == destination else MATH_INF for stop in all_stops}
    f = {stop: 0.0 for stop in all_stops}

    overline_a = []

    # Precompute links by ToNode
    links_by_to_node = {}
    for link in all_links:
        # Проверяем, что обе остановки существуют в all_stops
        if link.to_node in all_stops and link.from_node in all_stops:
            if link.to_node not in links_by_to_node:
                links_by_to_node[link.to_node] = []
            links_by_to_node[link.to_node].append(link)

    # Priority queue
    pq = PriorityQueue()
    for link in all_links:
        # Проверяем, что узел существует в all_stops
        if link.to_node in all_stops:
            pq.push(link, u[link.to_node] + link.travel_cost)

    while True:
        link, priority = pq.pop()
        if link is None or math.isinf(priority) or priority >= MATH_INF:
            break

        a = link
        i = a.from_node
        j = a.to_node
        
        # Проверяем, что обе остановки существуют в all_stops
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
            print(f"  u_j + c_a = {u[j] + a.travel_cost}")
            print(f"  u_i = {u[i]}")

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

        # Update PQ for links pointing to i (actually, links from nodes pointing to i? Wait, links that end at i are incoming, but update outgoing from predecessors)
        # In Go, it's linksByToNode[i] which are links ending at i, but then update entry for link.FromNode which is predecessor
        # Wait, in Go: linksToUpdate = linksByToNode[i]  # links ending at i
        # then for link in linksToUpdate:  # link is incoming to i
        # then iEntries = entries[link.FromNode]  # entries for from_node of incoming, i.e. predecessor
        # then for entry in iEntries:
        # if entry.link.ToNode == i and entry.link.FromNode == link.FromNode:  # entry for the incoming link
        # pq.update(entry, u[i] + link.TravelCost)  # update priority for the incoming link to u[i] + cost? No
        # Wait, link is incoming: from pred to i, cost is link.TravelCost for pred -> i
        # But priority for entry is u[ToNode] + TravelCost, ToNode is i, so u[i] + TravelCost? No
        # Wait, priority = u[j] + c_a where j = ToNode, a = (i,j)? No
        # In init: priority = u[link.ToNode] + link.TravelCost, for link (from, to), priority = u[to] + cost(from->to)
        # But in update, when u[i] updated, which links to update? Links that depend on u[i], i.e. links where ToNode == i? No
        # Wait, when u[i] changes, the priorities that use u[i] are for links where ToNode == i, priority = u[i] + c_a for a ending at i? No
        # Let's see: priority for a link a = (k, i), priority = u[i] + c_a where c_a is cost from k to i
        # Yes, so when u[i] changes, update priorities for links ending at i, i.e. incoming to i.
        # Yes, linksToUpdate = linksByToNode[i]  # ToNode == i, incoming
        # then for link in linksToUpdate: link = (pred, i)
        # then entry for that link, update to new u[i] + link.TravelCost
        # Yes.

        if i in links_by_to_node:
            for update_link in links_by_to_node[i]:  # update_link = (pred, i)
                # Проверяем существование узлов
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
    stop_times, active_trips, all_stops = parse_gtfs_limited(directory, limit)
    all_links = calculate_links(stop_times, active_trips, all_stops)
    all_links = calculate_headways(stop_times, active_trips, all_links)
    

    return all_links, all_stops

if __name__ == "__main__":
    directory = "improved-gtfs-moscow-official"
    all_links, all_stops = parse_gtfs(directory, 100000)

    print("🔍 Ищем пару связанных остановок...")
    origin, destination = find_connected_od_pair_with_min_hops(all_links)

    if origin is None or destination is None:
        raise ValueError("Не удалось найти ни одной пары остановок с путём между ними!")

    print(f"✅ Найдена пара: origin={origin}, destination={destination}")

    origins_reaching_dest = get_all_origins_reaching_destination(all_links, destination)

    print(f"🎯 Найдено {len(origins_reaching_dest)} остановок, из которых можно доехать до {destination}")

    od_matrix = {}
    for origin in origins_reaching_dest:
        if origin != destination:
            demand = random.uniform(50.0, 500.0)
            od_matrix[origin] = {destination: demand}

    print(f"📊 OD-матрица создана: {len(od_matrix)} origin → {destination} (случайный спрос)")
    result = compute_sf(all_links, all_stops, destination, od_matrix)