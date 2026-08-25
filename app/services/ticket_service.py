from app.integrations.db.postgres import fetch_one


class TicketService:
    def get_ticket(self, ticket_id: str) -> dict | None:
        return fetch_one(
            "SELECT * FROM tickets WHERE ticket_id = %s",
            (ticket_id,),
        )
