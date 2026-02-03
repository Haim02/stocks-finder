# from pymongo import MongoClient, UpdateOne
# from app.core.config import settings
# from datetime import datetime

# class MongoDB:
#     _client = None

#     @classmethod
#     def get_db(cls):
#         if cls._client is None:
#             cls._client = MongoClient(settings.MONGO_URI)
#         return cls._client[settings.DB_NAME]

#     @classmethod
#     def save_news_event(cls, ticker, news_item):
#         """שומר חדשה בודדת אם היא לא קיימת כבר"""
#         db = cls.get_db()
#         collection = db.news_events

#         # אנחנו משתמשים ב-URL כמפתח ייחודי למניעת כפילויות
#         collection.update_one(
#             {'url': news_item['url']},
#             {
#                 '$setOnInsert': {
#                     'ticker': ticker,
#                     'headline': news_item['headline'],
#                     'news_date': datetime.now(), # תאריך הסריקה
#                     'processed_for_training': False # דגל לאימון עתידי
#                 }
#             },
#             upsert=True
#         )

#     @classmethod
#     def get_unlabeled_data(cls):
#         """שליפת חדשות שעדיין לא אומנו"""
#         db = cls.get_db()
#         return list(db.news_events.find({'processed_for_training': False}))



# from pymongo import MongoClient, UpdateOne
# from app.core.config import settings
# from datetime import datetime
# import certifi  # <-- הוספנו את זה

# class MongoDB:
#     _client = None

#     @classmethod
#     def get_db(cls):
#         if cls._client is None:
#             # שימוש ב-certifi כדי לאמת את החיבור המאובטח (SSL/TLS)
#             # זה פותר את שגיאת ה-Handshake
#             cls._client = MongoClient(
#                 settings.MONGO_URI,
#                 tlsCAFile=certifi.where()
#             )
#         return cls._client[settings.DB_NAME]

#     @classmethod
#     def save_news_event(cls, ticker, news_item):
#         """שומר חדשה בודדת אם היא לא קיימת כבר"""
#         db = cls.get_db()
#         collection = db.news_events

#         # שימוש ב-URL כמפתח ייחודי למניעת כפילויות
#         collection.update_one(
#             {'url': news_item['url']},
#             {
#                 '$setOnInsert': {
#                     'ticker': ticker,
#                     'headline': news_item['headline'],
#                     'news_date': datetime.now(),
#                     'processed_for_training': False
#                 }
#             },
#             upsert=True
#         )

#     @classmethod
#     def get_unlabeled_data(cls):
#         """שליפת חדשות שעדיין לא אומנו"""
#         db = cls.get_db()
#         return list(db.news_events.find({'processed_for_training': False}))


#     @classmethod
#     def mark_as_processed(cls, doc_id):
#         """מסמן שהחדשה עברה תהליך אימון ולא צריך לשלוף אותה שוב"""
#         db = cls.get_db()
#         db.news_events.update_one(
#             {'_id': doc_id},
#             {'$set': {'processed_for_training': True}}
#         )


from pymongo import MongoClient, UpdateOne
from app.core.config import settings
from datetime import datetime, timedelta
import certifi
import pytz

class MongoDB:
    _client = None

    @classmethod
    def get_db(cls):
        if cls._client is None:
            # חיבור מאובטח עם certifi
            cls._client = MongoClient(
                settings.MONGO_URI,
                tlsCAFile=certifi.where()
            )
        return cls._client[settings.DB_NAME]

    @classmethod
    def save_news_event(cls, ticker, news_item):
        """שומר חדשה בודדת אם היא לא קיימת כבר"""
        db = cls.get_db()
        collection = db.news_events

        # המרת תאריך לפורמט תקין
        raw_date = news_item.get('published_at') or news_item.get('raw_date')
        if isinstance(raw_date, str):
            try:
                dt_object = datetime.fromisoformat(raw_date)
            except:
                dt_object = datetime.now(pytz.utc)
        else:
            dt_object = raw_date

        collection.update_one(
            {'url': news_item['url']},
            {
                '$setOnInsert': {
                    'ticker': ticker,
                    'headline': news_item['headline'],
                    'news_date': dt_object,
                    'processed_for_training': False,
                    'created_at': datetime.now(pytz.utc)
                }
            },
            upsert=True
        )

    @classmethod
    def get_unlabeled_data(cls):
        """שליפת חדשות שעדיין לא אומנו"""
        db = cls.get_db()
        return list(db.news_events.find({'processed_for_training': False}))

    @classmethod
    def mark_as_processed(cls, doc_id):
        """מסמן שהחדשה עברה תהליך אימון"""
        db = cls.get_db()
        db.news_events.update_one(
            {'_id': doc_id},
            {'$set': {'processed_for_training': True}}
        )

    # --- תוספת חדשה: מנגנון הצינון (Spam Filter) ---

    @classmethod
    def log_sent_alert(cls, ticker, reason):
        """מתעד שמניה נשלחה במייל"""
        db = cls.get_db()
        db.sent_alerts.insert_one({
            "ticker": ticker,
            "reason": reason, # 'News' or 'Technical'
            "sent_at": datetime.now(pytz.utc)
        })

    @classmethod
    def was_sent_recently(cls, ticker, days=3):
        """בודק אם המניה נשלחה במייל ב-X הימים האחרונים"""
        db = cls.get_db()
        cutoff_date = datetime.now(pytz.utc) - timedelta(days=days)

        count = db.sent_alerts.count_documents({
            "ticker": ticker,
            "sent_at": {"$gte": cutoff_date}
        })

        return count > 0