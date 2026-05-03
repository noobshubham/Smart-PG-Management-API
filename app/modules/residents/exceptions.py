class ResidentError(Exception):
    """Base residents-domain error."""


class ResidentNotFoundError(ResidentError):
    def __init__(self, resident_id: int) -> None:
        super().__init__(f"Resident {resident_id} not found")
        self.resident_id = resident_id


class RoomFullError(ResidentError):
    def __init__(self, room_id: int) -> None:
        super().__init__(f"Room {room_id} has no available capacity")
        self.room_id = room_id


class InvalidRoomError(ResidentError):
    def __init__(self, room_id: int) -> None:
        super().__init__(f"Room {room_id} does not exist in this PG")
        self.room_id = room_id


class InvalidMoveOutDateError(ResidentError):
    def __init__(self) -> None:
        super().__init__("move_out_date cannot be before joined_date")


class ResidentAlreadyInactiveError(ResidentError):
    def __init__(self, resident_id: int) -> None:
        super().__init__(f"Resident {resident_id} is already inactive")
        self.resident_id = resident_id
