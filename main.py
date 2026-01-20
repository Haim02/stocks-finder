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

from fastapi import FastAPI, BackgroundTasks, Header, HTTPException
import os
from run_daily_scan import run_scan

app = FastAPI()
# WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")

# @app.get("/trigger")
# async def trigger_scan(background_tasks: BackgroundTasks, x_secret: str = Header(None)):
#     # בדיקת אבטחה
#     if x_secret != WEBHOOK_SECRET:
#         raise HTTPException(status_code=401, detail="Unauthorized")

#     # הפעלה ברקע (מונע Timeout)
#     background_tasks.add_task(run_scan)

#     return {"status": "started", "message": "The scan is running in the background. You will get an email soon."}

@app.get("/trigger")
async def trigger(background_tasks: BackgroundTasks):
    # ביטלנו זמנית את בדיקת ה-Header כדי לוודא שהכל עובד
    print("Trigger received! Starting background scan...")
    background_tasks.add_task(run_scan)
    return {"status": "success", "message": "Scan started successfully!"}


# async def trigger(background_tasks: BackgroundTasks, x_secret: str = Header(None, alias="X-Secret")):
#     # הדפסה ללוגים כדי שנדע מה הגיע
#     print(f"Received secret: {x_secret}")

#     if x_secret != os.getenv("WEBHOOK_SECRET"):
#         raise HTTPException(status_code=401, detail="Invalid Secret")

#     background_tasks.add_task(run_scan)
#     return {"status": "success"}