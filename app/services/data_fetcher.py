import logging

import yfinance as yf
import pandas as pd

logger = logging.getLogger(__name__)


class DataFetcher:
    @staticmethod
    def get_stock_data(ticker):
        """Historical OHLCV data from yfinance."""
        try:
            stock = yf.Ticker(ticker)
            df = stock.history(period="1y", timeout=15)

            if df is None or df.empty or len(df) < 50:
                print(f"⚠️ No sufficient data for {ticker}")
                return None

            df.columns = [col.lower() for col in df.columns]
            return df
        except Exception as e:
            print(f"❌ Error fetching price data for {ticker}: {e}")
            return None

    @staticmethod
    def get_fundamentals(ticker):
        """Fundamentals from yfinance info — replaces Finnhub metrics."""
        try:
            info = yf.Ticker(ticker).info
            return {
                "pe_ratio":           info.get("trailingPE") or info.get("forwardPE", "N/A"),
                "ps_ratio":           info.get("priceToSalesTrailing12Months", "N/A"),
                "revenue_growth_yoy": info.get("revenueGrowth", "N/A"),
                "debt_to_equity":     info.get("debtToEquity", "N/A"),
                "net_margin":         info.get("profitMargins", "N/A"),
                "52_week_high":       info.get("fiftyTwoWeekHigh", "N/A"),
            }
        except Exception as e:
            logger.debug("get_fundamentals failed for %s: %s", ticker, e)
            return {}

    @staticmethod
    def get_news(ticker):
        """Latest news headlines from yfinance — replaces Finnhub news."""
        try:
            news = yf.Ticker(ticker).news or []
            return [
                item.get("content", {}).get("title", "")
                for item in news[:5]
                if item.get("content", {}).get("title")
            ]
        except Exception as e:
            logger.debug("get_news failed for %s: %s", ticker, e)
            return []

    @staticmethod
    def get_company_profile(ticker):
        """Company profile from yfinance — replaces Finnhub profile2."""
        try:
            info = yf.Ticker(ticker).info
            return {
                "name":       info.get("longName") or info.get("shortName", ticker),
                "industry":   info.get("industry", "N/A"),
                "market_cap": info.get("marketCap", "N/A"),
            }
        except Exception:
            return {"name": ticker, "industry": "N/A"}

    @staticmethod
    def get_institutional_data(ticker):
        """Institutional holders, major holders, insider transactions from yfinance."""
        try:
            stock = yf.Ticker(ticker)
            inst   = stock.institutional_holders
            major  = stock.major_holders
            insider = stock.insider_transactions
            return {
                "institutional_holders": inst.to_dict()    if inst    is not None and not inst.empty    else {},
                "major_holders":         major.to_dict()   if major   is not None and not major.empty   else {},
                "insider_transactions":  insider.to_dict() if insider is not None and not insider.empty else {},
            }
        except Exception as e:
            logger.debug("get_institutional_data failed for %s: %s", ticker, e)
            return {}

    @staticmethod
    def get_smart_money_signal(ticker: str) -> str:
        """Insider/institutional sentiment via Perplexity — replaces Finnhub insider_sentiment."""
        try:
            from app.services.perplexity_service import PerplexityService
            svc = PerplexityService()
            if svc.is_available():
                return svc.search(
                    f"Recent insider buying or selling for {ticker} stock. "
                    f"Any institutional accumulation or 13F filings showing large positions? "
                    f"2 sentences only.",
                    max_chars=200,
                )
        except Exception:
            pass
        return ""