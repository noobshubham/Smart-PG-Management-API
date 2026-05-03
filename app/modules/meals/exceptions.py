class MealError(Exception):
    """Base meals-domain error."""


class MealLogNotFoundError(MealError):
    def __init__(self, log_id: int) -> None:
        super().__init__(f"Meal log {log_id} not found")
        self.log_id = log_id
