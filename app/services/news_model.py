# import os
# import joblib
# import pandas as pd
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.ensemble import RandomForestClassifier
# from app.data.mongo_client import MongoDB

# class NewsModel:
#     def __init__(self):
#         self.model_path = "models/news_classifier.pkl"
#         self.vec_path = "models/tfidf.pkl"
#         self.is_trained = os.path.exists(self.model_path)

#         if self.is_trained:
#             self.model = joblib.load(self.model_path)
#             self.vectorizer = joblib.load(self.vec_path)

#         # מילות מפתח לגיבוי (Cold Start) - עד שיהיה מודל מאומן
#         self.keywords = {
#             'fda': 90, 'approval': 90, 'granted': 85,
#             'contract': 80, 'awarded': 80, 'partnership': 75,
#             'acquisition': 85, 'merger': 85, 'beat': 70,
#             'raised': 75, 'guidance': 70, 'upgrade': 65
#         }

#     def predict_impact(self, headline):
#         """
#         מחזיר ציון (0-100) לכותרת.
#         משתמש ב-ML אם קיים, אחרת משתמש במילות מפתח.
#         """
#         score = 0

#         # מסלול 1: מודל AI
#         if self.is_trained:
#             vec = self.vectorizer.transform([headline])
#             # מחזיר את ההסתברות שהחדשה היא Class 1 (חיובית)
#             prob = self.model.predict_proba(vec)[0][1]
#             score = int(prob * 100)

#         # מסלול 2: מילות מפתח (גיבוי או חיזוק)
#         keyword_score = 0
#         headline_lower = headline.lower()
#         for word, val in self.keywords.items():
#             if word in headline_lower:
#                 keyword_score = max(keyword_score, val)

#         # שקלול: אם המודל בטוח, נלך איתו. אם לא, מילות מפתח
#         return max(score, keyword_score)

#     def train(self, df):
#         """מאמן את המודל מחדש ושומר קבצים"""
#         print("🧠 Training News Model...")
#         vectorizer = TfidfVectorizer(stop_words='english', max_features=1000)
#         X = vectorizer.fit_transform(df['headline'])
#         y = df['is_winner'] # 1 = עלה, 0 = לא עלה

#         clf = RandomForestClassifier(n_estimators=100, random_state=42)
#         clf.fit(X, y)

#         os.makedirs("models", exist_ok=True)
#         joblib.dump(clf, self.model_path)
#         joblib.dump(vectorizer, self.vec_path)
#         print("✅ Model trained and saved successfully!")


import joblib
import os
import sys

class NewsModel:
    def __init__(self):
        # --- תיקון נתיבים קריטי ---
        # חישוב הנתיב באופן דינמי כדי למנוע שגיאות File Not Found
        # זה מוצא איפה הקובץ הזה נמצא, ועולה תיקייה אחת למעלה ל-app/models
        current_dir = os.path.dirname(os.path.abspath(__file__))
        base_path = os.path.join(current_dir, '..', 'models')

        self.model_path = os.path.join(base_path, "news_classifier.pkl")
        self.vectorizer_path = os.path.join(base_path, "tfidf_vectorizer.pkl")

        self.model = None
        self.vectorizer = None

        # טעינת המודל בעת יצירת המחלקה
        self._load_model()

    def _load_model(self):
        """מנסה לטעון את המודל המאומן מהדיסק"""
        try:
            if os.path.exists(self.model_path) and os.path.exists(self.vectorizer_path):
                self.model = joblib.load(self.model_path)
                self.vectorizer = joblib.load(self.vectorizer_path)
                print(f"🧠 NewsModel: Loaded TRAINED model successfully!")
                print(f"   (Source: {self.model_path})")
            else:
                print("⚠️ NewsModel: Trained model not found.")
                print(f"   Looking in: {self.model_path}")
                print("   -> Switching to Heuristic Mode (Backup).")
        except Exception as e:
            print(f"⚠️ Error loading model: {e}")
            self.model = None

    def predict_impact(self, headline):
        """
        מחזיר ציון (0-100) לכותרת.
        אם יש מודל מאומן - משתמש בו.
        אם אין - משתמש בלוגיקה של מילות מפתח.
        """

        # --- אפשרות 1: שימוש במוח המאומן (AI) ---
        if self.model and self.vectorizer:
            try:
                # המרת הכותרת למספרים שהמודל מבין
                vec = self.vectorizer.transform([headline])

                # המודל מחזיר הסתברות (למשל: 0.82 סיכוי לעלייה)
                # [0] = סיכוי לירידה, [1] = סיכוי לעלייה
                prob = self.model.predict_proba(vec)[0][1]

                # המרה לאחוזים (82)
                return int(prob * 100)
            except Exception as e:
                print(f"⚠️ AI Prediction failed: {e}")
                # במקרה של תקלה, ממשיכים לאפשרות 2

        # --- אפשרות 2: גיבוי ידני (Heuristics) ---
        # משתמשים בזה רק אם אין מודל או שהוא נכשל
        return self._calculate_heuristic_score(headline)

    def _calculate_heuristic_score(self, headline):
        """חישוב ציון לפי מילות מפתח (כשיש תקלה ב-AI או אין מודל)"""
        score = 50 # ציון התחלתי ניטרלי
        headline_lower = headline.lower()

        # מילים חזקות מאוד (מקפיצות ציון)
        strong_positive = [
            'fda approval', 'fda approved', 'phase 3', 'phase iii',
            'acquired', 'merger', 'record revenue', 'beat estimates',
            'contract awarded', 'breakthrough', 'guidance raised'
        ]

        # מילים חיוביות רגילות
        positive = [
            'partnership', 'collaboration', 'launch', 'expansion',
            'growth', 'positive results', 'buy rating', 'upgrade'
        ]

        # מילים שליליות (מורידות ציון)
        negative = [
            'public offering', 'direct offering', 'dilution',
            'investigation', 'lawsuit', 'suspended', 'rejected',
            'missed estimates', 'downgrade', 'sell rating'
        ]

        # חישוב הניקוד
        for word in strong_positive:
            if word in headline_lower: score += 30

        for word in positive:
            if word in headline_lower: score += 15

        for word in negative:
            if word in headline_lower: score -= 20

        # וידוא שהציון נשאר בין 0 ל-100
        return max(0, min(100, score))

    # הערה: הסרתי מפה את פונקציית train()
    # הסיבה: האימון מתבצע עכשיו בקובץ הנפרד והחכם train_model.py
    # שדואג לאיסוף נתונים מה-DB, סינון כפילויות ובדיקת היסטוריה.