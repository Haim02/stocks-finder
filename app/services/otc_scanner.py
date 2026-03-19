import yfinance as yf
import pandas as pd

class OTCScanner:
    @staticmethod
    def evaluate_hard_rules(ticker):
        """
        בודק אם מניית OTC עומדת בחוקי הברזל:
        1. מחיר בין 0.01$ ל-5.00$
        2. מחזור יחסי (RVOL) גדול מ-2
        """
        try:
            # תיקון נפוץ ל-Yahoo Finance עבור OTC
            yf_ticker = ticker
            if not ticker.endswith(('OB', 'PK', 'US')):
                # לעיתים יאהו דורש סיומת למניות מעבר לדלפק, מנסים קודם את הטיקר הנקי
                pass

            stock = yf.Ticker(yf_ticker)
            # מושכים נתוני חודש אחורה כדי לחשב ממוצע מחזורים (30 ימי מסחר)
            hist = stock.history(period="1mo")

            if hist.empty or len(hist) < 20:
                return None # אין מספיק היסטוריה

            current_price = hist['Close'].iloc[-1]
            current_vol = hist['Volume'].iloc[-1]

            # חישוב ממוצע מחזורים של כל הימים הקודמים (ללא היום הנוכחי כדי לא לעוות)
            avg_vol_30d = hist['Volume'].iloc[:-1].mean()

            if avg_vol_30d == 0:
                return None

            rvol = current_vol / avg_vol_30d

            # חוקי הברזל (Hard Rules)
            if 0.01 <= current_price <= 5.00 and rvol > 2.0:
                prev_close = hist['Close'].iloc[-2]
                pct_change = ((current_price - prev_close) / prev_close) * 100

                return {
                    "price": current_price,
                    "volume": current_vol,
                    "avg_vol_30d": avg_vol_30d,
                    "rvol": round(rvol, 2),
                    "pct_change": round(pct_change, 2)
                }

            return None

        except Exception as e:
            # מתעלמים בשקט ממניות שלא קיימות ב-Yahoo
            return None