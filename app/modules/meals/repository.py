from datetime import date

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.modules.meals.models import MealLog


class MealLogRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def list_for_date(self, pg_id: int, on_date: date) -> list[MealLog]:
        stmt = (
            select(MealLog)
            .where(MealLog.pg_id == pg_id, MealLog.date == on_date)
            .order_by(MealLog.resident_id)
        )
        return list(self.db.execute(stmt).scalars().all())

    def find_open_for_resident(self, resident_id: int, on_date: date) -> MealLog | None:
        """An "open" poll = prompted_at set, response not yet recorded.

        Used by the inbound dispatcher. NOT tenant-scoped because the resident
        already comes from a phone-lookup; the resident's pg_id implicitly
        scopes the query.
        """
        stmt = (
            select(MealLog)
            .where(
                MealLog.resident_id == resident_id,
                MealLog.date == on_date,
                MealLog.prompted_at.is_not(None),
                MealLog.responded_at.is_(None),
            )
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def get_or_create(self, pg_id: int, resident_id: int, on_date: date) -> MealLog:
        stmt = select(MealLog).where(
            MealLog.pg_id == pg_id,
            MealLog.resident_id == resident_id,
            MealLog.date == on_date,
        )
        existing = self.db.execute(stmt).scalar_one_or_none()
        if existing is not None:
            return existing
        log = MealLog(pg_id=pg_id, resident_id=resident_id, date=on_date)
        self.db.add(log)
        self.db.commit()
        self.db.refresh(log)
        return log

    def save(self, log: MealLog) -> MealLog:
        self.db.commit()
        self.db.refresh(log)
        return log

    def headcount_for_date(self, pg_id: int, on_date: date) -> dict[str, int]:
        stmt = (
            select(MealLog.will_eat_dinner, func.count(MealLog.id))
            .where(MealLog.pg_id == pg_id, MealLog.date == on_date)
            .group_by(MealLog.will_eat_dinner)
        )
        eating = skipping = not_responded = 0
        for value, count in self.db.execute(stmt).all():
            count_i = int(count)
            if value is True:
                eating = count_i
            elif value is False:
                skipping = count_i
            else:
                not_responded = count_i
        return {
            "eating": eating,
            "skipping": skipping,
            "not_responded": not_responded,
            "total_polled": eating + skipping + not_responded,
        }
