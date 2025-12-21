# traffic_flows

## Запуск юнит-тестов

Для запуска всех юнит-тестов выполните:

```bash
python -m pytest unit_tests/ -v
```

Для запуска тестов только для определенного модуля:

```bash
python -m pytest unit_tests/test_florian.py -v
```

```bash
python -m pytest unit_tests/test_visualization.py -v
```

## Запуск
```bash
pip install -r requirements.txt
pip install -e .
python3 ./comparisons/compare_volumes.py
```
## Результат
![Сравнение](visual/network_volumes_highlightev2d.png )
**Примечание: модифицированный алгоритм выбирает Res3 --> DownTown, так как это увеличивает вероятность прийти вовремя с 0.34 до 0.41**


### Математичеcкое описание методов в description.ipynb