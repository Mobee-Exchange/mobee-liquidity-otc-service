from sqlalchemy import orm, text


class PriceRepository:
    def __init__(self, session: orm.Session):
        self.session = session

    def fetch_current_prices(self, currencies: list[str]) -> dict[str, float]:
        """
        Returns {currency: usd_price} from datawarehouse.last_hour_price_diff.
        Only returns rows where USD_Current is non-null and positive.
        """
        if not currencies:
            return {}
        placeholders = ", ".join(f":c{i}" for i in range(len(currencies)))
        params = {f"c{i}": c for i, c in enumerate(currencies)}
        query = text(
            f"""
            SELECT
                Currency,
                USD_Current
            FROM
                datawarehouse.last_hour_price_diff
            WHERE
                Currency IN ({placeholders})
                AND USD_Current IS NOT NULL
                AND USD_Current > 0
            """
        )
        result = self.session.execute(query, params).mappings().all()
        return {row["Currency"]: float(row["USD_Current"]) for row in result}
