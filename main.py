from fastapi import FastAPI, BackgroundTasks
import uvicorn
from run_daily_scan import run_scan # ייבוא הפונקציה שלך

app = FastAPI()

@app.get("/")
def home():
    return {"status": "The scanner is online and waiting for a signal"}

@app.get("/trigger")
def trigger(background_tasks: BackgroundTasks):
    # הפעלת הסריקה הקיימת שלך ברקע
    background_tasks.add_task(run_scan)
    return {"message": "Scan started! You will get an email when it's done."}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)