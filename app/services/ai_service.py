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


import openai
from app.core.config import settings

class AIService:
    @staticmethod
    def analyze_stock(ticker, price, score, reasons, fundamentals, news, company_info):
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        company_name = company_info.get('name', ticker)
        industry = company_info.get('industry', 'N/A')
        news_str = "\n".join(news) if news else "אין חדשות משמעותיות לאחרונה."

        # זיהוי אם זה Squeeze כדי לכוון את ה-AI
        context = "Potential Early Breakout / Squeeze Setup" if "Squeeze" in str(reasons) else "Technical Setup"

        prompt = f"""
        Analyze the stock {ticker} ({company_name}) - {industry}.
        Context: {context}.
        Current Price: ${price}.
        Score: {score}/5.
        Technical Reasons: {', '.join(reasons)}.
        Fundamentals Data: {fundamentals}
        Recent News: {news_str}

        Task: Write a professional HTML report in HEBREW.

        Sections REQUIRED:
        1. 'על החברה' - Brief business description.
        2. 'Checklist Table' - HTML Table with rows: נר אחרון, ווליום, RSI, MA20, מצב כללי.
           (CRITICAL: Do NOT include "מגמה חודשית"). Use ✅/❌.
        3. 'ניתוח פונדמנטלי' - 2-3 sentences analyzing the financial health/news.
        4. 'Trade Plan' - Entry/Exit logic based on the chart.
        5. 'שורה תחתונה' - Conclusion.

        Style: RTL (Right-to-Left), clean design, professional financial Hebrew.
        Return ONLY the HTML code (no markdown code blocks).
        """

        try:
            response = client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are a senior technical analyst expert in Hebrew."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            # ניקוי אם ה-AI בטעות מחזיר Markdown
            content = response.choices[0].message.content
            content = content.replace("```html", "").replace("```", "")
            return content

        except Exception as e:
            return f"<p>ניתוח AI לא זמין: {e}</p>"