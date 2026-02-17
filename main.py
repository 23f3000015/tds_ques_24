from fastapi import FastAPI
import requests
import sqlite3
from datetime import datetime
import os

app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------
# Initialize Database
# ---------------------------
def init_db():
    conn = sqlite3.connect("pipeline.db")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            original TEXT,
            analysis TEXT,
            sentiment TEXT,
            source TEXT,
            timestamp TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ---------------------------
# AI PIPE ANALYSIS FUNCTION
# ---------------------------
def analyze_text(text):
    try:
        url = "https://aipipe.org/openai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {os.getenv('AI_PIPE_TOKEN')}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {
                    "role": "user",
                    "content": f"Analyze this in 2 sentences and classify sentiment as optimistic, pessimistic, or balanced: {text}"
                }
            ]
        }

        response = requests.post(url, headers=headers, json=payload, timeout=10)

        if response.status_code != 200:
            return f"AI API Error: {response.text}", "unknown"

        result = response.json()
        content = result["choices"][0]["message"]["content"]

        sentiment = "balanced"
        if "optimistic" in content.lower():
            sentiment = "optimistic"
        elif "pessimistic" in content.lower():
            sentiment = "pessimistic"

        return content, sentiment

    except Exception as e:
        return f"AI Error: {str(e)}", "unknown"

# ---------------------------
# PIPELINE ENDPOINT
# ---------------------------
@app.post("/pipeline")
def run_pipeline(data: dict):

    email = data.get("email")
    source = data.get("source")

    results = []
    errors = []

    for i in range(3):

        # ---------------------------
        # 1. FETCH UUID
        # ---------------------------
        try:
            response = requests.get("https://httpbin.org/uuid", timeout=5)
            uuid = response.json()["uuid"]
        except Exception as e:
            errors.append(f"API error: {str(e)}")
            continue

        # ---------------------------
        # 2. AI ANALYSIS
        # ---------------------------
        analysis, sentiment = analyze_text(uuid)

        if sentiment == "unknown":
            errors.append("AI processing failed")

        # ---------------------------
        # 3. STORE IN DATABASE
        # ---------------------------
        try:
            conn = sqlite3.connect("pipeline.db")
            cursor = conn.cursor()
            timestamp = datetime.utcnow().isoformat()

            cursor.execute("""
                INSERT INTO results (original, analysis, sentiment, source, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (uuid, analysis, sentiment, source, timestamp))

            conn.commit()
            conn.close()
            stored = True

        except Exception as e:
            errors.append(f"DB error: {str(e)}")
            stored = False

        results.append({
            "original": uuid,
            "analysis": analysis,
            "sentiment": sentiment,
            "stored": stored,
            "timestamp": timestamp
        })

    # ---------------------------
    # 4. MOCK NOTIFICATION
    # ---------------------------
    print("Notification sent to: 23f3000015@ds.study.iitm.ac.in")

    return {
        "items": results,
        "notificationSent": True,
        "processedAt": datetime.utcnow().isoformat(),
        "errors": errors
    }
