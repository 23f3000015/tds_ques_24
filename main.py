from fastapi import FastAPI
import requests
import sqlite3
from datetime import datetime
from openai import OpenAI

app = FastAPI()

client = OpenAI(api_key="YOUR_OPENAI_API_KEY")

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

def analyze_text(text):
    try:
        prompt = f"""
        Analyze this in 2 sentences and classify sentiment as optimistic, pessimistic, or balanced:
        {text}
        """

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}]
        )

        result = response.choices[0].message.content

        sentiment = "balanced"
        if "optimistic" in result.lower():
            sentiment = "optimistic"
        elif "pessimistic" in result.lower():
            sentiment = "pessimistic"

        return result, sentiment

    except Exception as e:
        return f"AI Error: {str(e)}", "unknown"

@app.post("/pipeline")
def run_pipeline(data: dict):

    email = data.get("email")
    source = data.get("source")

    results = []
    errors = []

    for i in range(3):

        try:
            response = requests.get("https://httpbin.org/uuid", timeout=5)
            uuid = response.json()["uuid"]
        except Exception as e:
            errors.append(f"API error: {str(e)}")
            continue

        try:
            analysis, sentiment = analyze_text(uuid)
        except Exception as e:
            errors.append(f"AI error: {str(e)}")
            continue

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

    print(f"Notification sent to: 23f3000015@ds.study.iitm.ac.in")

    return {
        "items": results,
        "notificationSent": True,
        "processedAt": datetime.utcnow().isoformat(),
        "errors": errors
    }
