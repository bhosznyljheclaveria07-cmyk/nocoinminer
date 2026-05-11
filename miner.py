import requests
import time
import hashlib
import base64
import json
import os
from groq import Groq

API_URL = "https://bqrapnlqqtjedjyhlfci.supabase.co/functions/v1/submit-solution"

API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImJxcmFwbmxxcXRqZWRqeWhsZmNpIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NzgyNzUyNjQsImV4cCI6MjA5Mzg1MTI2NH0.mf0fz6kAnK0yeAXrb-XT6yikbdRmeAq5jsikVPPhaFE"

WALLET = "0xe8b85a40c81545fdc607f3ee5efe53fd0ab3dc34"
AGENT = "variz"

# =========================
# GROQ AI
# =========================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

groq_client = None

if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)

# =========================
# HEADERS
# =========================

headers = {
    "apikey": API_KEY,
    "Content-Type": "application/json"
}

# =========================
# CACHE
# =========================

CACHE_FILE = "answers.json"

try:
    with open(CACHE_FILE, "r") as f:
        cache = json.load(f)
except:
    cache = {}

def save_cache():
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

# =========================
# GET PUZZLE
# =========================

def get_puzzle():
    url = f"{API_URL}?eth={WALLET}"

    response = requests.get(
        url,
        headers=headers,
        timeout=60
    )

    return response.json()

# =========================
# LOCAL SOLVERS
# =========================

def solve_sha256_empty():
    result = hashlib.sha256(b"").hexdigest()
    return result[:6]

def solve_base64(prompt):
    try:
        text = prompt.split("'")[1]
        decoded = base64.b64decode(text).decode()
        return decoded.lower().strip()
    except:
        return None

def solve_reverse(prompt):
    try:
        text = prompt.split("'")[1]
        return text[::-1].lower().strip()
    except:
        return None

def solve_math(prompt):
    try:
        expression = (
            prompt.lower()
            .replace("calculate", "")
            .replace("what is", "")
            .replace("=", "")
            .strip()
        )

        result = eval(expression)

        return str(result)
    except:
        return None

# =========================
# GROQ AI
# =========================

def ask_groq(prompt):
    if not groq_client:
        return None

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "system",
                    "content": "You solve cryptographic and logic puzzles. Return ONLY the final answer."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0
        )

        answer = response.choices[0].message.content

        return answer.lower().strip()

    except Exception as e:
        print("[GROQ ERROR]", e)
        return None

# =========================
# MAIN SOLVER
# =========================

def solve_puzzle(puzzle):
    prompt = puzzle["prompt"]
    prompt_lower = prompt.lower()

    print("[PUZZLE]", prompt)

    if prompt in cache:
        print("[CACHE] Using cached answer")
        return cache[prompt]

    answer = None

    # SHA256
    if "sha-256 hash of the empty string" in prompt_lower:
        answer = solve_sha256_empty()

    # BASE64
    elif "base64" in prompt_lower:
        answer = solve_base64(prompt)

    # REVERSE
    elif "reverse" in prompt_lower:
        answer = solve_reverse(prompt)

    # MATH
    elif "calculate" in prompt_lower or "what is" in prompt_lower:
        answer = solve_math(prompt)

    # GROQ AI FALLBACK
    if not answer:
        print("[AI] Using Groq AI...")
        answer = ask_groq(prompt)

    if answer:
        answer = str(answer).lower().strip()

        cache[prompt] = answer
        save_cache()

    return answer

# =========================
# SUBMIT
# =========================

def submit_answer(puzzle_id, answer):
    payload = {
        "eth_address": WALLET,
        "agent_name": AGENT,
        "puzzle_id": puzzle_id,
        "answer": answer
    }

    response = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        timeout=60
    )

    return response.json()

# =========================
# START
# =========================

print("[MINER] Started successfully")

while True:
    try:
        data = get_puzzle()

        puzzle = data.get("puzzle")

        if not puzzle:
            print("[INFO] No puzzle available")
            time.sleep(30)
            continue

        answer = solve_puzzle(puzzle)

        if not answer:
            print("[INFO] Could not solve puzzle")
            time.sleep(10)
            continue

        print("[ANSWER]", answer)

        result = submit_answer(
            puzzle["id"],
            answer
        )

        print("[RESULT]", result)

        if result.get("correct"):
            print("[SUCCESS] +500 NTC")
        else:
            print("[FAILED] Wrong answer")

        time.sleep(5)

    except Exception as e:
        print("[ERROR]", e)
        time.sleep(15)
