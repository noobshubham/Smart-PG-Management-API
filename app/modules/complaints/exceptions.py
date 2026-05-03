class ComplaintError(Exception):
    """Base complaints-domain error."""


class ComplaintNotFoundError(ComplaintError):
    def __init__(self, complaint_id: int) -> None:
        super().__init__(f"Complaint {complaint_id} not found")
        self.complaint_id = complaint_id
