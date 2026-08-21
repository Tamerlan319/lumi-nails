from __future__ import annotations

# Здесь можно менять услуги, длительность и стоимость без правки логики бота.
SERVICES = [
    {"id": 1, "name": "Маникюр", "duration": 90, "price": 1800},
    {"id": 2, "name": "Педикюр", "duration": 120, "price": 2400},
    {"id": 3, "name": "Стрижка", "duration": 60, "price": 1500},
    {"id": 4, "name": "Окрашивание", "duration": 180, "price": 4500},
]

# service_ids — список услуг, которые выполняет мастер.
MASTERS = [
    {"id": 1, "name": "Анна", "service_ids": [1, 2]},
    {"id": 2, "name": "Мария", "service_ids": [1, 2, 3]},
    {"id": 3, "name": "Елена", "service_ids": [3, 4]},
]


def service_by_id(service_id: int) -> dict | None:
    return next((item for item in SERVICES if item["id"] == service_id), None)


def master_by_id(master_id: int) -> dict | None:
    return next((item for item in MASTERS if item["id"] == master_id), None)


def masters_for_service(service_id: int) -> list[dict]:
    return [m for m in MASTERS if service_id in m["service_ids"]]
