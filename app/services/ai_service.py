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




import openai
from app.core.config import settings

class AIService:
    @staticmethod
    def analyze_stock(ticker, price, score, reasons, fundamentals, news, company_info):
        client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)

        # שליפת נתונים מהפרופיל שהבאנו מ-Finnhub
        company_name = company_info.get('name', ticker)
        industry = company_info.get('industry', 'N/A')

        news_str = "\n".join(news) if news else "אין חדשות משמעותיות לאחרונה."

        prompt = f"""
        Analyze the stock {ticker} ({company_name}) which operates in the {industry} industry.
        Current Price: ${price}.
        Technical Score: {score}/5.
        Technical Reasons: {', '.join(reasons)}.
        Fundamentals: {fundamentals}
        Recent News: {news_str}

        Write a professional stock analysis in HEBREW.
        Structure:
        1. 'על החברה' - 2 sentences in Hebrew explaining what this company does and its main products.
        2. 'למה עכשיו?' - Relationship between technical setup and recent events/fundamentals.
        3. 'ניתוח פונדמנטלי' - Does the data support the business?
        4. 'שורה תחתונה' - Swing potential.

        Use emojis, professional tone, and clear formatting.
        """

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a senior Wall Street analyst expert in Hebrew."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7
            )
            return response.choices[0].message.content
        except Exception as e:
            return f"ניתוח AI לא זמין כרגע: {e}"

        