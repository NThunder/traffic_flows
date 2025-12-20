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


```bash
pip install -e .
python3 -m comparisons.compare_volumes
```