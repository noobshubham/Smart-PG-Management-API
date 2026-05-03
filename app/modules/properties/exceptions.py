class PropertyError(Exception):
    """Base properties-domain error."""


class RoomNotFoundError(PropertyError):
    def __init__(self, room_id: int) -> None:
        super().__init__(f"Room {room_id} not found")
        self.room_id = room_id


class DuplicateRoomNumberError(PropertyError):
    def __init__(self, room_number: str) -> None:
        super().__init__(f"Room number '{room_number}' already exists in this PG")
        self.room_number = room_number


class CapacityBelowOccupancyError(PropertyError):
    def __init__(self, requested: int, occupied: int) -> None:
        super().__init__(
            f"Cannot set capacity to {requested}: {occupied} residents are active"
        )
        self.requested = requested
        self.occupied = occupied


class RoomOccupiedError(PropertyError):
    def __init__(self, room_id: int) -> None:
        super().__init__(f"Cannot delete room {room_id} while residents are active")
        self.room_id = room_id
