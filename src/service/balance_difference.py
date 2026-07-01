import logging
from src.db.clickhouse import session_scope
from src.repository.balance_diff import BalanceDifferenceRepository

log = logging.getLogger(__name__)


class BalanceDifferenceService:
    def __init__(self):
        pass
    def run(self):
        with session_scope() as session:
            repo = BalanceDifferenceRepository(session)
            rows = repo.get_latest_diff()
        log.info(f"{rows} inserted to balance_diff table")
        return int(rows)

