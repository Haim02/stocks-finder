"""
scanner.py — Main Entry Point
"""
import logging
from app.options_engine.iv import get_iv, SYMBOLS
from app.options_engine.strategies import select_strategies, build_setup
from app.options_engine.alerts import check_and_alert

logger = logging.getLogger(__name__)


def run_options_engine(symbols: list[str] = None) -> list[dict]:
    symbols = symbols or SYMBOLS
    logger.info("=== Options Engine — %d symbols ===", len(symbols))
    all_setups = []

    for symbol in symbols:
        iv_result = get_iv(symbol)
        if not iv_result:
            logger.warning("Skip %s — no IV data", symbol)
            continue

        strategies = select_strategies(iv_result.iv_rank)
        logger.info("%s IV Rank=%.2f → %s", symbol, iv_result.iv_rank, strategies[0])

        for strategy in strategies[:1]:
            setup = build_setup(symbol, iv_result.price, iv_result.iv_current,
                               iv_result.iv_rank, strategy)
            if setup:
                all_setups.append(setup)
                break

    if all_setups:
        check_and_alert(all_setups)

    return [
        {"symbol": s.symbol, "price": s.price, "iv": s.iv, "iv_rank": s.iv_rank,
         "strategy": s.strategy, "expiration": s.expiration, "dte": s.dte,
         "strikes": s.strikes, "greeks": s.greeks, "credit": s.credit,
         "max_loss": s.max_loss, "probability_profit": s.probability_profit,
         "return_on_risk": s.return_on_risk}
        for s in all_setups
    ]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    results = run_options_engine()
    for r in results:
        print(r)
