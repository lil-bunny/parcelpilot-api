from app.integrations.db.postgres import fetch_one


class OrderService:
    def get_order(self, order_id: str) -> dict | None:
        return fetch_one(
            "SELECT * FROM orders WHERE order_id = %s",
            (order_id,),
        )
