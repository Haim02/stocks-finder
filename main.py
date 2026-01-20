# from fastapi import FastAPI, BackgroundTasks
# import uvicorn
# from run_daily_scan import run_scan # ייבוא הפונקציה שלך

# app = FastAPI()

# @app.get("/")
# def home():
#     return {"status": "The scanner is online and waiting for a signal"}

# @app.get("/trigger")
# def trigger(background_tasks: BackgroundTasks):
#     # הפעלת הסריקה הקיימת שלך ברקע
#     background_tasks.add_task(run_scan)
#     return {"message": "Scan started! You will get an email when it's done."}

# if __name__ == "__main__":
#     uvicorn.run(app, host="0.0.0.0", port=8000)

# from fastapi import FastAPI, BackgroundTasks, Header, HTTPException
# import os
# from run_daily_scan import run_scan

# app = FastAPI()
# WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# @app.get("/trigger")
# async def trigger(background_tasks: BackgroundTasks, x_secret: str = Header(None, alias="X-Secret")):
#     # הדפסה ללוגים כדי שנדע מה הגיע
#     print(f"Received secret: {x_secret}")

#     if x_secret != os.getenv("WEBHOOK_SECRET"):
#         raise HTTPException(status_code=401, detail="Invalid Secret")

#     background_tasks.add_task(run_scan)
#     return {"status": "success"}


from fastapi import FastAPI, BackgroundTasks
import os
import traceback
from run_daily_scan import run_scan

app = FastAPI()

@app.get("/trigger")
async def trigger(background_tasks: BackgroundTasks):
    print("--- ה-Trigger התקבל בהצלחה ---")

    def wrapper():
        try:
            print("מנסה להריץ את הסריקה ברקע...")
            run_scan()
            print("הסריקה הסתיימה בהצלחה!")
        except Exception as e:
            print("!!! שגיאה קריטית בזמן הסריקה !!!")
            print(traceback.format_exc()) # זה ידפיס ל-Render את השגיאה המדויקת

    background_tasks.add_task(wrapper)
    return {"status": "started"}