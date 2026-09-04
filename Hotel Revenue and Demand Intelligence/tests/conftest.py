import pytest

from src.data_loader import (
    DB_PATH,
    database_ready,
    load_bookings,
    load_daily_metrics,
    load_guests,
    load_room_nights,
    load_rooms,
)


def pytest_collection_modifyitems(config, items):
    if database_ready():
        return
    skip = pytest.mark.skip(
        reason=f"dataset not found at {DB_PATH}; run 'python data/make_dataset.py' first"
    )
    for item in items:
        if item.nodeid.endswith("test_database_file_exists"):
            continue
        item.add_marker(skip)


@pytest.fixture(scope="session")
def bookings():
    return load_bookings()


@pytest.fixture(scope="session")
def rooms():
    return load_rooms()


@pytest.fixture(scope="session")
def guests():
    return load_guests()


@pytest.fixture(scope="session")
def daily_metrics():
    return load_daily_metrics()


@pytest.fixture(scope="session")
def room_nights():
    return load_room_nights()


@pytest.fixture(scope="session")
def hotel_capacity(rooms):
    return int(rooms["rooms_available"].sum())
