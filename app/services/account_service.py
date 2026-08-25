from app.integrations.db.postgres import fetch_one


class AccountService:
    def get_account(self, account_id: str) -> dict | None:
        return fetch_one(
            "SELECT * FROM accounts WHERE account_id = %s",
            (account_id,),
        )
