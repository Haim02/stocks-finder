# import openai
# from app.core.config import settings

# class AIService:
#     @staticmethod
#     def analyze_stock(ticker, price, score, reasons, fundamentals, news):
#         client = openai.OpenAI(api_key=settings.OPENAI_API_KEY) # וודא שזה השם ב-settings

#         news_str = "\n".join(news) if news else "אין חדשות משמעותיות לאחרונה."

#         prompt = f"""
#         Analyze the stock {ticker} currently trading at ${price}.
#         Technical Score: {score}/5.
#         Technical Reasons: {', '.join(reasons)}.
#         Fundamentals: {fundamentals}
#         Recent News: {news_str}

#         Write a professional, deep stock analysis in HEBREW for a premium trading newsletter.
#         Include sections:
#         1. 'למה עכשיו?' - הסבר על השילוב בין הטכני לחדשות.
#         2. 'ניתוח פונדמנטלי' - האם המספרים תומכים בעסק?
#         3. 'שורה תחתונה' - סיכום פוטנציאל הסווינג.
#         Use emojis, professional tone, and clear formatting.
#         """

#         try:
#             response = client.chat.completions.create(
#                 model="gpt-4o-mini",
#                 messages=[
#                     {"role": "system", "content": "You are a senior Wall Street analyst expert in Hebrew."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 temperature=0.7
#             )
#             return response.choices[0].message.content
#         except Exception as e:
#             return f"ניתוח AI לא זמין כרגע: {e}"




# import openai
# from app.core.config import settings

# class AIService:
#     @staticmethod
#     def analyze_stock(ticker, price, score, reasons, fundamentals, news, company_info):
#         client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

#         # שליפת נתונים מהפרופיל שהבאנו מ-Finnhub
#         company_name = company_info.get('name', ticker)
#         industry = company_info.get('industry', 'N/A')

#         news_str = "\n".join(news) if news else "אין חדשות משמעותיות לאחרונה."

#         prompt = f"""
#         Analyze the stock {ticker} ({company_name}) which operates in the {industry} industry.
#         Current Price: ${price}.
#         Technical Score: {score}/5.
#         Technical Reasons: {', '.join(reasons)}.
#         Fundamentals: {fundamentals}
#         Recent News: {news_str}

#         Write a professional stock analysis in HEBREW.
#         Structure:
#         1. 'על החברה' - 2 sentences in Hebrew explaining what this company does and its main products.
#         2. 'למה עכשיו?' - Relationship between technical setup and recent events/fundamentals.
#         3. 'ניתוח פונדמנטלי' - Does the data support the business?
#         4. 'שורה תחתונה' - Swing potential.

#         Use emojis, professional tone, and clear formatting.
#         """

#         try:
#             response = client.chat.completions.create(
#                 model="gpt-4o-mini",
#                 messages=[
#                     {"role": "system", "content": "You are a senior Wall Street analyst expert in Hebrew."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 temperature=0.7
#             )
#             return response.choices[0].message.content
#         except Exception as e:
#             return f"ניתוח AI לא זמין כרגע: {e}"



# import openai
# from app.core.config import settings

# class AIService:
#     @staticmethod
#     def analyze_stock(ticker, price, score, reasons, fundamentals, news, company_info):
#         client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

#         company_name = company_info.get('name', ticker)
#         industry = company_info.get('industry', 'N/A')
#         news_str = "\n".join(news) if news else "אין חדשות משמעותיות לאחרונה."

#         # הפרומפט המעודכן שדורש את הטבלאות והורדת המגמה החודשית
#         prompt = f"""
#         Analyze the stock {ticker} ({company_name}) in the {industry} industry.
#         Current Price: ${price}.
#         Technical Score: {score}/5.
#         Technical Reasons: {', '.join(reasons)}.
#         Fundamentals: {fundamentals}
#         Recent News: {news_str}

#         You MUST return the response in HTML format.

#         Structure:
#         1. 'על החברה' - 2 sentences in Hebrew.
#         2. 'Checklist Table' - Include ONLY: נר אחרון, מגמה שבועית, ווליום, MA20, מצב כללי.
#            (CRITICAL: Do NOT include "מגמה חודשית"). Use ✅/❌ or technical terms.
#         3. 'Trade Plan Table' - Include: Entry Area, Stop Loss, Target 1 (RR 2.0), Target 2 (RR 3.5).
#         4. 'ניתוח פונדמנטלי' - 2 sentences in Hebrew.
#         5. 'שורה תחתונה' - Swing potential in Hebrew.

#         Use professional Hebrew, emojis, and RTL direction for text.
#         Format tables with: width:100%; border-collapse:collapse; margin-top:10px;
#         """

#         try:
#             response = client.chat.completions.create(
#                 model="gpt-4o", # השתמשתי ב-4o לדיוק מקסימלי בבניית הטבלאות
#                 messages=[
#                     {"role": "system", "content": "You are a senior Wall Street analyst expert in Hebrew and HTML formatting."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 temperature=0.7
#             )
#             return response.choices[0].message.content
#         except Exception as e:
#             return f"ניתוח AI לא זמין כרגע: {e}"


# import openai
# from app.core.config import settings

# class AIService:
#     @staticmethod
#     def analyze_stock(ticker, price, score, reasons, fundamentals, news, company_info):
#         client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

#         company_name = company_info.get('name', ticker)
#         industry = company_info.get('industry', 'N/A')
#         news_str = "\n".join(news) if news else "אין חדשות משמעותיות לאחרונה."

#         prompt = f"""
#         Analyze the stock {ticker} ({company_name}).
#         Current Price: ${price}.
#         Technical Score: {score}/5.
#         Technical Reasons: {', '.join(reasons)}.

#         Task: Create a professional HTML report in HEBREW.

#         Sections to include:
#         1. 'על החברה' - Short summary.
#         2. 'Checklist Table' - Rows: נר אחרון, מגמה שבועית, ווליום, MA20, מצב כללי.
#            (DO NOT include "מגמה חודשית"). Use ✅/❌.
#         3. 'Trade Plan' - Based on the price ${price}, suggest a logical entry and confirm if the technicals support a 1:2.5 risk/reward.
#         4. 'שורה תחתונה' - Summary of the opportunity.

#         Style: RTL, professional, clean HTML tables.
#         """

#         try:
#             response = client.chat.completions.create(
#                 model="gpt-4o",
#                 messages=[
#                     {"role": "system", "content": "You are a senior analyst. Return only the internal HTML content."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 temperature=0.7
#             )
#             return response.choices[0].message.content
#         except Exception as e:
#             return f"ניתוח AI לא זמין: {e}"


# import openai
# from app.core.config import settings

# class AIService:
#     @staticmethod
#     def analyze_stock(ticker, price, score, reasons, fundamentals, news, company_info):
#         client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

#         company_name = company_info.get('name', ticker)
#         industry = company_info.get('industry', 'N/A')
#         news_str = "\n".join(news) if news else "אין חדשות משמעותיות לאחרונה."

#         # זיהוי אם זה Squeeze כדי לכוון את ה-AI
#         context = "Potential Early Breakout / Squeeze Setup" if "Squeeze" in str(reasons) else "Technical Setup"

#         prompt = f"""
#         Analyze the stock {ticker} ({company_name}) - {industry}.
#         Context: {context}.
#         Current Price: ${price}.
#         Score: {score}/5.
#         Technical Reasons: {', '.join(reasons)}.
#         Fundamentals Data: {fundamentals}
#         Recent News: {news_str}

#         Task: Write a professional HTML report in HEBREW.

#         Sections REQUIRED:
#         1. 'על החברה' - Brief business description.
#         2. 'Checklist Table' - HTML Table with rows: נר אחרון, ווליום, RSI, MA20, מצב כללי.
#            (CRITICAL: Do NOT include "מגמה חודשית"). Use ✅/❌.
#         3. 'ניתוח פונדמנטלי' - 2-3 sentences analyzing the financial health/news.
#         4. 'Trade Plan' - Entry/Exit logic based on the chart.
#         5. 'שורה תחתונה' - Conclusion.

#         Style: RTL (Right-to-Left), clean design, professional financial Hebrew.
#         Return ONLY the HTML code (no markdown code blocks).
#         """

#         try:
#             response = client.chat.completions.create(
#                 model="gpt-4o",
#                 messages=[
#                     {"role": "system", "content": "You are a senior technical analyst expert in Hebrew."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 temperature=0.7
#             )
#             # ניקוי אם ה-AI בטעות מחזיר Markdown
#             content = response.choices[0].message.content
#             content = content.replace("```html", "").replace("```", "")
#             return content

#         except Exception as e:
#             return f"<p>ניתוח AI לא זמין: {e}</p>"



# from openai import OpenAI
# from app.core.config import settings

# class AIService:
#     def __init__(self):
#         self.client = None
#         if settings.OPENAI_API_KEY:
#             self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
#         else:
#             print("⚠️ Warning: OPENAI_API_KEY missing.")

#     def analyze_stock(self, ticker, headline, financials):
#         """
#         שולח ל-OpenAI את כל הנתונים ומבקש ניתוח אנליסט בעברית.
#         """
#         if not self.client:
#             return "שירות ה-AI לא זמין (חסר מפתח)."

#         # הכנת הנתונים לפרומפט
#         eff = financials.get('efficiency')
#         eff_str = "לא זמין"
#         if eff:
#             trend = "שיפור" if eff['is_improving'] else "הרעה"
#             eff_str = f"יחס הוצאות נוכחי {eff['curr_ratio']}% (מגמת {trend} לעומת רבעון קודם)"

#         prompt = f"""
#         Act as a senior Wall Street analyst speaking Hebrew.
#         Analyze the stock {ticker} based on the following data:

#         1. **News Event**: "{headline}"
#         2. **Financials**:
#            - Revenue Growth (QoQ): {financials.get('revenue_growth_qoq')}%
#            - Efficiency (Op. Expenses / Revenue): {eff_str}
#            - Sector: {financials.get('sector')}

#         **Your Task:**
#         Write a concise summary (3-4 sentences) in Hebrew.
#         - Explain why this news is important.
#         - Mention if the financials (growth/efficiency) support a price increase.
#         - Bottom line: Is this a strong setup?

#         Tone: Professional, direct, insightful.
#         """

#         try:
#             response = self.client.chat.completions.create(
#                 model="gpt-4o-mini", # מהיר וזול, מצוין לסיכומים
#                 messages=[
#                     {"role": "system", "content": "You are a helpful financial analyst."},
#                     {"role": "user", "content": prompt}
#                 ],
#                 max_tokens=200,
#                 temperature=0.7
#             )
#             return response.choices[0].message.content.strip()
#         except Exception as e:
#             print(f"❌ OpenAI Error: {e}")
#             return "שגיאה ביצירת סיכום AI."


# from openai import OpenAI
# from app.core.config import settings

# class AIService:
#     def __init__(self):
#         self.client = None
#         if settings.OPENAI_API_KEY:
#             self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

#     def analyze_stock(self, ticker, headline, financials):
#         """
#         מחזיר מילון עם שני מפתחות:
#         1. 'hebrew_desc': תיאור החברה בעברית.
#         2. 'analysis': ניתוח המצב.
#         """
#         if not self.client:
#             return {"hebrew_desc": "שירות AI לא זמין", "analysis": "חסר מפתח"}

#         # הכנת נתונים
#         desc_en = financials.get('description', '')
#         eff = financials.get('efficiency')
#         eff_str = "לא זמין"
#         if eff:
#             trend = "שיפור" if eff['is_improving'] else "הרעה"
#             eff_str = f"{eff['curr_ratio']}% (מגמת {trend})"

#         prompt = f"""
#         You are a financial analyst assisting a Hebrew speaker.

#         Input Data for {ticker}:
#         1. Company Description (English): "{desc_en}"
#         2. News Headline: "{headline}"
#         3. Financials: Revenue Growth {financials.get('revenue_growth_qoq')}%, Efficiency {eff_str}.

#         **Task:**
#         Output exactly two parts separated by "|||".

#         Part 1: Translate the company description to Hebrew (concise, max 2 sentences).
#         Part 2: Analyze the news and financials in Hebrew (3 sentences). Is it a buy signal?

#         Format:
#         <Hebrew Description>|||<Hebrew Analysis>
#         """

#         try:
#             response = self.client.chat.completions.create(
#                 model="gpt-4o-mini",
#                 messages=[{"role": "user", "content": prompt}],
#                 max_tokens=300,
#                 temperature=0.7
#             )
#             content = response.choices[0].message.content.strip()

#             # פיצול התשובה לשני חלקים
#             parts = content.split("|||")
#             if len(parts) == 2:
#                 return {
#                     "hebrew_desc": parts[0].strip(),
#                     "analysis": parts[1].strip()
#                 }
#             else:
#                 return {
#                     "hebrew_desc": "תרגום לא זמין",
#                     "analysis": content
#                 }

#         except Exception as e:
#             print(f"❌ OpenAI Error: {e}")
#             return {"hebrew_desc": "שגיאה", "analysis": "שגיאה"}



from openai import OpenAI
from app.core.config import settings

class AIService:
    def __init__(self):
        self.client = None
        if settings.OPENAI_API_KEY:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

    def analyze_stock(self, ticker, headline, financials):
        if not self.client:
            return {"hebrew_desc": "חסר מפתח AI", "analysis": "לא ניתן לנתח"}

        rev = financials['revenue']
        ni = financials['net_income']
        eff = financials['efficiency']

        # בניית טקסט להתייעלות
        eff_str = "N/A"
        if eff['curr'] and eff['prev']:
            eff_str = f"Current: {eff['curr']}%, Previous: {eff['prev']}%"

        prompt = f"""
        Act as a senior financial analyst writing in Hebrew.

        Stock: {ticker}
        News: "{headline}"
        Company Description: "{financials.get('description', '')}"

        Financial Highlights (Quarterly Comparison):
        - Revenue: {rev['curr']} (Change: {rev['change']}%)
        - Net Income: {ni['curr']} (Change: {ni['change']}%)
        - Operating Efficiency Ratio (Expenses/Revenue - Lower is better): {eff_str}

        **Task:**
        Output exactly two parts separated by "|||".

        Part 1: Translate the company description to Hebrew (max 2 sentences).
        Part 2: Create "Report Highlights" (עיקרי הדוח) in Hebrew.
                - Summarize financial performance.
                - Did the efficiency improve? (Lower ratio = Improvement).
                - Explain the news significance.
                - Bottom line for a trader.

        Format:
        <Hebrew Description>|||<Hebrew Highlights>
        """

        try:
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=350,
                temperature=0.7
            )
            content = response.choices[0].message.content.strip()
            parts = content.split("|||")
            if len(parts) == 2:
                return {"hebrew_desc": parts[0].strip(), "analysis": parts[1].strip()}
            else:
                return {"hebrew_desc": "תרגום לא זמין", "analysis": content}

        except Exception as e:
            return {"hebrew_desc": "שגיאה", "analysis": "שגיאה בניתוח"}