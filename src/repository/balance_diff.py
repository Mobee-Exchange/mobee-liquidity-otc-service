from sqlalchemy import text, orm


class BalanceDifferenceRepository:
    def __init__(self, session: orm.Session):
        self.session = session

    def get_latest_diff(self):
        result = (
            self.session.execute(
                text("""
                select timestamp, 
                        platform,
                        source_name,
                        currency,
                        network,
                        amount as balance,
                        prev_balance,
                        amount-prev_balance as diff 
                     from (   
                        SELECT
                            timestamp, platform, source_name, currency, network, amount,
                            lagInFrame(amount, 1) OVER w AS prev_balance,
                            count()               OVER w AS n,
                            row_number() OVER (PARTITION BY platform, source_name, currency, network
                                            ORDER BY timestamp DESC) AS rn
                        FROM mobee_liquidity_otc.balance_ingest
                        WINDOW w AS (PARTITION BY platform, source_name, currency, network
                                    ORDER BY timestamp)
                    )
                    WHERE rn = 1                 -- only the newest snapshot per source
                    AND n  > 1                 -- has a prior observation (skip first-ever)
                    AND amount != prev_balance;  -- changed only
                    """)
            )
            .mappings()
            .all()
        )
        result = [dict(row) for row in result]
        if not result:
            return 0
        self.session.execute(
            text("""INSERT INTO mobee_liquidity_otc.balance_diff
                                 (timestamp, platform, source_name, currency, network, prev_balance,balance,diff)
                                 VALUES (:timestamp, :platform, :source_name, :currency, :network, :prev_balance, :balance, :diff)"""),
            result,
        )
        return len(result)
