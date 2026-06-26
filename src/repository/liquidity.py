from sqlalchemy import orm, text


class LiquidityRepository:
    def __init__(self, session: orm.Session):
        self.session = session

    def fetch_quote_dict(self) -> dict[str, str]:
        query = text(
            """
            SELECT
                token,
                symbol
            FROM 
                liquidity.quote_dict
            """
        )
        result = self.session.execute(query).mappings().all()
        return {row["token"]: row["symbol"] for row in result}

    def fetch_fireblocks_supported_assets(self) -> dict[str, str]:
        query = text(
            """
            SELECT
                asset_id,
                native_asset,
                currency_code
            FROM
                _fireblocks.list_supported_assets
            WHERE
                currency_code IS NOT NULL
            """
        )
        result = self.session.execute(query).mappings().all()
        return {
            row["asset_id"]: {
                "native_asset": row["native_asset"],
                "currency_code": row["currency_code"],
            }
            for row in result
        }

    def fetch_fireblocks_assets_with_currency(self) -> list[dict]:
        """
        Returns all assets that have a currency_code set, used by the
        min_threshold refresh service to look up USD prices.

        Returns list of {asset_id, currency_code}.
        """
        query = text(
            """
            SELECT
                asset_id,
                currency_code
            FROM
                _fireblocks.list_supported_assets
            WHERE
                currency_code IS NOT NULL
            """
        )
        result = self.session.execute(query).mappings().all()
        return [{"asset_id": row["asset_id"], "currency_code": row["currency_code"]} for row in result]
