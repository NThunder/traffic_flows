
from algos.florian import find_optimal_strategy, assign_demand as assign_demand_florain, parse_gtfs
from algos.time_arrived_florian import find_optimal_strategy as  find_optimal_strategy_modified, assign_demand as assign_demand_time_arrived
from algos.lateness_prob_florian import  parse_sample_data

def compare_approaches(od_matrix, destination, T=60):
    all_links, all_stops = parse_sample_data()
    # Оригинальный
    strategy_orig = find_optimal_strategy(all_links, all_stops, destination)
    volumes_orig = assign_demand_florain(all_links, all_stops, strategy_orig, od_matrix, destination, is_original=True)
    # Модифицированный
    strategy_mod = find_optimal_strategy_modified(all_links, all_stops, destination, T)
    volumes_mod = assign_demand_time_arrived(all_links, all_stops, strategy_mod, od_matrix, destination, is_original=False)
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
compare_approaches({'A': {'C': 100}, 'A': {'E': 50}}, 'E', 10)