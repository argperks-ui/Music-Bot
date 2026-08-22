import os
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, RedirectResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Git Music Dashboard")

CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
CALLBACK_URL = os.getenv("CALLBACK_URL", "http://localhost:3000/auth/callback")

@app.get("/")
async def serve_index():
    return FileResponse("index.html")

@app.get("/login")
async def serve_login():
    return FileResponse("login.html")

@app.get("/dashboard")
async def serve_dashboard():
    return FileResponse("Dashboard/dashboard.html")

@app.get("/api/discord/login")
async def discord_login():
    discord_auth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={CALLBACK_URL}"
        f"&response_type=code"
        f"&scope=identify%20guilds"
    )
    return RedirectResponse(discord_auth_url)

@app.get("/auth/callback")
async def discord_callback(code: str):
    data = {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": CALLBACK_URL,
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}

    async with httpx.AsyncClient() as client:
        # Request access token from Discord
        token_response = await client.post("https://discord.com/api/oauth2/token", data=data, headers=headers)
        if token_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to retrieve token from Discord")

        token_data = token_response.json()
        access_token = token_data.get("access_token")

        # Fetch user profile to verify identity
        user_response = await client.get(
            "https://discord.com/api/users/@me",
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if user_response.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to fetch Discord user data")

    return RedirectResponse(url="/dashboard")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 3000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)