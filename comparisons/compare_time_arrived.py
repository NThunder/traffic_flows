from typing import Dict, List, Set, Tuple
import matplotlib.pyplot as plt
import networkx as nx
from algos.florian import compute_sf as florian_compute_sf
from algos.time_arrived_florian import compute_sf as time_arrived_compute_sf
from utils import Link
import numpy as np


def create_transportation_network():
    """
    Создает транспортную сеть с 10 вершинами, демонстрирующую различия между алгоритмами:
    - Быстрый, но ненадежный маршрут (например, автобус с большими задержками)
    - Медленный, но надежный маршрут (например, метро с регулярным движением)
    """
    links: List[Link] = [
        # Быстрый, но ненадежный маршрут (автобус) - A -> B -> F -> J
        Link(from_node="A", to_node="B", route_id="BUS1", travel_cost=8, headway=30, 
             mean_travel_time=8, std_travel_time=5, delay_mu=0, delay_sigma=3),
        Link(from_node="B", to_node="F", route_id="BUS1", travel_cost=15, headway=30, 
             mean_travel_time=15, std_travel_time=8, delay_mu=0, delay_sigma=4),
        Link(from_node="F", to_node="J", route_id="BUS1", travel_cost=12, headway=30, 
             mean_travel_time=12, std_travel_time=6, delay_mu=0, delay_sigma=3),
        
        # Медленный, но надежный маршрут (метро) - A -> C -> G -> J
        Link(from_node="A", to_node="C", route_id="METRO1", travel_cost=12, headway=5, 
             mean_travel_time=12, std_travel_time=1, delay_mu=0, delay_sigma=0.5),
        Link(from_node="C", to_node="G", route_id="METRO1", travel_cost=18, headway=5, 
             mean_travel_time=18, std_travel_time=2, delay_mu=0, delay_sigma=0.8),
        Link(from_node="G", to_node="J", route_id="METRO1", travel_cost=10, headway=5, 
             mean_travel_time=10, std_travel_time=1, delay_mu=0, delay_sigma=0.6),
        
        # Альтернативный маршрут через D и H
        Link(from_node="A", to_node="D", route_id="TRAIN1", travel_cost=10, headway=20, 
             mean_travel_time=10, std_travel_time=3, delay_mu=0, delay_sigma=1.5),
        Link(from_node="D", to_node="H", route_id="TRAIN1", travel_cost=14, headway=20, 
             mean_travel_time=14, std_travel_time=4, delay_mu=0, delay_sigma=2),
        Link(from_node="H", to_node="J", route_id="TRAIN1", travel_cost=11, headway=20, 
             mean_travel_time=11, std_travel_time=3, delay_mu=0, delay_sigma=1.5),
        
        # Соединения между маршрутами
        Link(from_node="B", to_node="C", route_id="FEEDER1", travel_cost=3, headway=15, 
             mean_travel_time=3, std_travel_time=1, delay_mu=0, delay_sigma=0.7),
        Link(from_node="C", to_node="D", route_id="FEEDER2", travel_cost=2, headway=10, 
             mean_travel_time=2, std_travel_time=0.5, delay_mu=0, delay_sigma=0.4),
        Link(from_node="F", to_node="G", route_id="FEEDER3", travel_cost=4, headway=25, 
             mean_travel_time=4, std_travel_time=2, delay_mu=0, delay_sigma=1.2),
        Link(from_node="G", to_node="H", route_id="FEEDER4", travel_cost=3, headway=12, 
             mean_travel_time=3, std_travel_time=1, delay_mu=0, delay_sigma=0.6),
        
        # Дополнительные соединения для создания более сложной сети
        Link(from_node="B", to_node="E", route_id="BUS2", travel_cost=6, headway=25, 
             mean_travel_time=6, std_travel_time=4, delay_mu=0, delay_sigma=2.2),
        Link(from_node="E", to_node="I", route_id="BUS2", travel_cost=9, headway=25, 
             mean_travel_time=9, std_travel_time=5, delay_mu=0, delay_sigma=2.5),
        Link(from_node="I", to_node="J", route_id="BUS2", travel_cost=7, headway=25, 
             mean_travel_time=7, std_travel_time=4, delay_mu=0, delay_sigma=2.0),
        Link(from_node="E", to_node="F", route_id="FEEDER5", travel_cost=2, headway=18, 
             mean_travel_time=2, std_travel_time=1, delay_mu=0, delay_sigma=0.8),
        Link(from_node="I", to_node="G", route_id="FEEDER6", travel_cost=3, headway=16, 
             mean_travel_time=3, std_travel_time=1.5, delay_mu=0, delay_sigma=0.9),
    ]
    
    stops: Set[str] = {"A", "B", "C", "D", "E", "F", "G", "H", "I", "J"}
    od_matrix: Dict[str, Dict[str, float]] = {"A": {"J": 1000}}  # 1000 пассажиров из A в J
    destination: str = "J"
    
    return links, stops, od_matrix, destination


def visualize_network(links: List[Link], stops: Set[str], destination: str, title: str, filename: str):
    """Визуализирует транспортную сеть"""
    G = nx.DiGraph()
    
    for stop in stops:
        G.add_node(stop)
    
    for link in links:
        G.add_edge(link.from_node, link.to_node, weight=link.travel_cost, route=link.route_id,
                  headway=link.headway, mean_tt=link.mean_travel_time, std_tt=link.std_travel_time)
    
    plt.figure(figsize=(16, 12))
    
    # Используем spring_layout для лучшего распределения узлов
    pos = nx.spring_layout(G, scale=3, seed=42)  # Увеличиваем масштаб для большего расстояния между узлами
    
    # Рисуем узлы с увеличенными отступами
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=2500, alpha=0.9)
    nx.draw_networkx_nodes(G, pos, nodelist=[destination], node_color='red', node_size=2500, alpha=0.9)
    
    # Рисуем ребра
    nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20, alpha=0.6)
    
    # Рисуем метки узлов
    nx.draw_networkx_labels(G, pos, font_size=14, font_weight='bold')
    
    # Подготовим метки ребер
    edge_labels = {}
    for link in links:
        edge_labels[(link.from_node, link.to_node)] = f"{link.route_id}\n{link.travel_cost}min\nH:{link.headway}m"
    
    # Рисуем метки ребер с вертикальным сдвигом для избежания перекрытий
    for (edge, label) in edge_labels.items():
        # Получаем координаты начала и конца ребра
        start_pos = pos[edge[0]]
        end_pos = pos[edge[1]]
        
        # Вычисляем смещение для размещения метки
        mid_x = (start_pos[0] + end_pos[0]) / 2
        mid_y = (start_pos[1] + end_pos[1]) / 2
        
        # Смещаем метку немного вверх от середины ребра
        offset_x = 0.2 * (end_pos[1] - start_pos[1])  # увеличиваем смещение пропорционально наклону
        offset_y = -0.2 * (end_pos[0] - start_pos[0])  # увеличиваем перпендикулярное смещение
        
        plt.text(mid_x + offset_x, mid_y + offset_y, label, fontsize=8,
                horizontalalignment='center', verticalalignment='center',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='white', alpha=0.8))
    
    plt.title(title, size=16)
    plt.axis('off')
    plt.tight_layout()
    
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.show()


def visualize_algorithm_result(links: List[Link], stops: Set[str], destination: str, 
                              result, algorithm_name: str, filename: str, od_matrix: Dict[str, Dict[str, float]]):
    """Визуализирует результат работы алгоритма"""
    G = nx.DiGraph()
    
    for stop in stops:
        G.add_node(stop)
    
    for link in links:
        G.add_edge(link.from_node, link.to_node, weight=link.travel_cost, route=link.route_id)
    
    plt.figure(figsize=(16, 12))
    
    # Используем spring_layout для лучшего распределения узлов
    pos = nx.spring_layout(G, scale=3, seed=42) # Увеличиваем масштаб для большего расстояния между узлами
    
    # Рисуем все ребра серым цветом
    nx.draw_networkx_edges(G, pos, edge_color='lightgray', arrows=True, arrowsize=15, alpha=0.5)
    
    # Рисуем узлы
    nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=300, alpha=0.9)
    nx.draw_networkx_nodes(G, pos, nodelist=[destination], node_color='red', node_size=3000, alpha=0.9)
    
    # Рисуем метки узлов
    nx.draw_networkx_labels(G, pos, font_size=14, font_weight='bold')
    
    # Выделяем ребра, используемые в оптимальной стратегии
    if hasattr(result.strategy, 'a_set'):
        strategy_edges = [(link.from_node, link.to_node) for link in result.strategy.a_set]
        nx.draw_networkx_edges(G, pos, edgelist=strategy_edges, edge_color='green',
                              arrows=True, arrowsize=25, width=3, alpha=0.8)
    
    # Подготовим метки ребер с объемами
    edge_labels = {}
    for link in links:
        volume = result.volumes.links.get(link.from_node, {}).get(link.to_node, 0)
        edge_labels[(link.from_node, link.to_node)] = f"{link.route_id}\n{link.travel_cost}min\nV:{volume:.1f}"
    
    # Рисуем метки ребер
    for (edge, label) in edge_labels.items():
        # Получаем координаты начала и конца ребра
        start_pos = pos[edge[0]]
        end_pos = pos[edge[1]]
        
        # Вычисляем смещение для размещения метки
        mid_x = (start_pos[0] + end_pos[0]) / 2
        mid_y = (start_pos[1] + end_pos[1]) / 2
        
        # Смещаем метку немного вверх от середины ребра
        offset_x = 0.2 * (end_pos[1] - start_pos[1]) # увеличиваем смещение пропорционально наклону
        offset_y = -0.2 * (end_pos[0] - start_pos[0])  # увеличиваем перпендикулярное смещение
        
        plt.text(mid_x + offset_x, mid_y + offset_y, label, fontsize=8,
                horizontalalignment='center', verticalalignment='center',
                bbox=dict(boxstyle='round,pad=0.2', facecolor='yellow', alpha=0.7))
    
    plt.title(f"{algorithm_name} - Оптимальная стратегия (зеленые ребра)\nОбъемы пассажиропотока", size=16)
    plt.axis('off')
    plt.tight_layout()
    
    plt.savefig(filename, dpi=300, bbox_inches='tight')
    plt.show()


def main():
    # Создаем транспортную сеть
    links, stops, od_matrix, destination = create_transportation_network()
    
    print("Транспортная сеть создана:")
    print(f"- Число вершин: {len(stops)}")
    print(f"- Число связей: {len(links)}")
    print(f"- OD-матрица: {od_matrix}")
    print(f"- Цель: {destination}")
    
    # Визуализируем сеть
    visualize_network(links, stops, destination, 
                     "Транспортная сеть: быстрый ненадежный маршрут (автобус) vs медленный надежный маршрут (метро)", 
                     "transportation_network.png")
    
    # Запускаем алгоритм Флориана (минимизация ожидаемого времени)
    print("\nЗапускаем алгоритм Флориана...")
    florian_result = florian_compute_sf(links, stops, destination, od_matrix)
    print("Алгоритм Флориана завершен")
    
    # Визуализируем результат алгоритма Флориана
    visualize_algorithm_result(links, stops, destination, florian_result, 
                             "Алгоритм Флориана", "florian_result.png", od_matrix)
    
    # Запускаем алгоритм с учетом времени прибытия (максимизация надежности)
    print("\nЗапускаем алгоритм с учетом времени прибытия...")
    time_arrived_result = time_arrived_compute_sf(links, stops, destination, od_matrix, T=50)
    print("Алгоритм с учетом времени прибытия завершен")
    
    # Визуализируем результат алгоритма с учетом времени прибытия
    visualize_algorithm_result(links, stops, destination, time_arrived_result, 
                             "Алгоритм с учетом времени прибытия", "time_arrived_result.png", od_matrix)
    
    # Сравниваем результаты
    print("\nСравнение результатов:")
    print(f"Алгоритм Флориана выбрал {len(florian_result.strategy.a_set)} ребер")
    print(f"Алгоритм с учетом времени прибытия выбрал {len(time_arrived_result.strategy.a_set)} ребер")
    
    florian_routes = set()
    for link in florian_result.strategy.a_set:
        florian_routes.add(link.route_id)
    
    time_arrived_routes = set()
    for link in time_arrived_result.strategy.a_set:
        time_arrived_routes.add(link.route_id)
    
    print(f"Маршруты по Флориану: {florian_routes}")
    print(f"Маршруты по времени прибытия: {time_arrived_routes}")
    
    # Анализ различий
    print(f"\nРазличия в маршрутах:")
    unique_florian = florian_routes - time_arrived_routes
    unique_time_arrived = time_arrived_routes - florian_routes
    
    if unique_florian:
        print(f"Уникальные для Флориана: {unique_florian}")
    if unique_time_arrived:
        print(f"Уникальные для времени прибытия: {unique_time_arrived}")
    
    if not unique_florian and not unique_time_arrived:
        print("Алгоритмы выбрали одинаковые маршруты")


if __name__ == "__main__":
    main()