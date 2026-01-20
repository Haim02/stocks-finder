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
import sys

# נסיון ייבוא עם הדפסת שגיאה אם נכשל
try:
    from run_daily_scan import run_scan
except Exception as e:
    print(f"IMPORT ERROR: Could not find run_daily_scan. Error: {e}")
    run_scan = None

app = FastAPI()

@app.get("/trigger")
async def trigger(background_tasks: BackgroundTasks):
    print("--- Trigger Received ---")

    if run_scan is None:
        return {"status": "error", "message": "run_scan function not found in imports"}

    # הפעלה בטוחה עם לוגים
    def wrapper():
        try:
            print("Background task is actually starting now...")
            run_scan()
            print("Background task finished successfully!")
        except Exception as e:
            print(f"CRITICAL ERROR DURING SCAN: {e}")

    background_tasks.add_task(wrapper)
    return {"status": "success", "message": "Task added to background"}