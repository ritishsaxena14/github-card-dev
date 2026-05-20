import os
import httpx
import json
from mcp.server.fastmcp import FastMCP
from google import genai
from typing import List, Dict
from dotenv import load_dotenv

# Load environment variables
if os.path.exists("vibe.env"):
    load_dotenv("vibe.env")
elif os.path.exists("../vibe.env"):
    load_dotenv("../vibe.env")
else:
    load_dotenv()

# Initialize FastMCP server
mcp = FastMCP("GitHubDevCard")

# Initialize Gemini Client
client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))

@mcp.tool()
async def scrape_github(username: str) -> dict:
    """Fetch user profile data and top repos from GitHub."""
    headers = {
        "User-Agent": "GitHub-Card-Generator"
    }
    token = os.getenv("GITHUB_TOKEN")
    if token and "your_github_token" not in token:
        headers["Authorization"] = f"token {token}"
        
    async with httpx.AsyncClient(headers=headers) as http_client:
        try:
            # User info
            user_resp = await http_client.get(f"https://api.github.com/users/{username}")
            if user_resp.status_code == 404:
                return {"error": f"User '{username}' not found on GitHub."}
            elif user_resp.status_code == 403:
                return {"error": "GitHub API rate limit exceeded. Please check your GITHUB_TOKEN."}
            
            user_data = user_resp.json()
            
            # Repos info
            repos_resp = await http_client.get(f"https://api.github.com/users/{username}/repos?sort=updated&per_page=30")
            repos = repos_resp.json() if repos_resp.status_code == 200 else []
            
            # Filter and sort top 6 repos by stars
            top_repos = sorted(repos, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:6]
            
            # Aggregate languages
            languages = {}
            for repo in repos:
                lang = repo.get("language")
                if lang:
                    languages[lang] = languages.get(lang, 0) + 1
            
            return {
                "name": user_data.get("name") or username,
                "bio": user_data.get("bio"),
                "location": user_data.get("location"),
                "avatar_url": user_data.get("avatar_url"),
                "public_repos": user_data.get("public_repos"),
                "followers": user_data.get("followers"),
                "top_repos": [
                    {
                        "name": r["name"],
                        "stars": r["stargazers_count"],
                        "language": r["language"],
                        "description": r["description"]
                    } for r in top_repos
                ],
                "languages": sorted(languages, key=languages.get, reverse=True)[:5]
            }
        except Exception as e:
            return {"error": str(e)}

@mcp.tool()
async def analyze_profile(github_data: dict) -> dict:
    """Use Gemini 2.5 Flash to analyze the profile with a robust fallback."""
    if "error" in github_data:
        return {"error": github_data["error"]}

    prompt = f"""
    Analyze this GitHub profile data and return a JSON object.
    Data: {json.dumps(github_data)}
    Return JSON format:
    {{
        "developer_vibe": "one sentence personality description",
        "top_skills": ["skill1", "skill2", "skill3"],
        "fun_fact": "a clever observation based on their repos",
        "card_theme": "hacker" | "builder" | "researcher" | "designer" | "open-source-hero"
    }}
    """
    
    try:
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key or "your_gemini" in api_key:
            raise ValueError("No valid API key")

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config={"response_mime_type": "application/json"}
        )
        return json.loads(response.text)
    except Exception:
        followers = github_data.get("followers", 0)
        repos = github_data.get("public_repos", 0)
        langs = github_data.get("languages", ["Code"])
        
        if followers > 5000:
            vibe = "A legendary force in the open-source ecosystem."
            theme = "open-source-hero"
        elif repos > 50:
            vibe = "A prolific builder who never stops shipping code."
            theme = "builder"
        elif "Python" in langs or "C++" in langs:
            vibe = "A deep-tech specialist solving complex problems."
            theme = "researcher"
        else:
            vibe = "A dedicated developer crafting digital futures."
            theme = "hacker"

        return {
            "developer_vibe": vibe,
            "top_skills": langs[:3] if langs else ["GitHub", "Git", "DevOps"],
            "fun_fact": f"Has shipped {repos} projects to the world!",
            "card_theme": theme
        }

@mcp.tool()
def generate_card_html(username: str, github_data: dict, analysis: dict) -> str:
    """Generates an authentic FIFA-style animated HTML card."""
    if "error" in github_data:
        return f"<div style='color: #f85149; background: #161b22; padding: 20px; border-radius: 8px; border: 1px solid #30363d; font-family: sans-serif;'><strong>Error:</strong> {github_data['error']}</div>"

    followers = github_data.get("followers", 0)

    # ── Tier Logic & Visuals ──────────────────────────────────────────────────
    if followers < 1000:
        tier       = "74"
        tier_label = "BRONZE"
        colors = {
            "bg"          : "linear-gradient(160deg, #6b3a1f 0%, #a0522d 40%, #cd7f32 70%, #8b4513 100%)",
            "border"      : "#cd7f32",
            "text"        : "#1a0a00",
            "glow"        : "rgba(205,127,50,0.55)",
            "overlay_bg"  : "rgba(101,55,20,0.55)",
            "badge_bg"    : "rgba(139,69,19,0.45)",
            "badge_border": "rgba(205,127,50,0.6)",
            "stat_sep"    : "rgba(139,69,19,0.5)",
            "shimmer"     : "rgba(205,127,50,0.15)",
            "label_color" : "#3d1a00",
        }
    elif followers < 30000:
        tier       = "84"
        tier_label = "SILVER"
        colors = {
            "bg"          : "linear-gradient(160deg, #4a4a4a 0%, #888 40%, #c8c8c8 65%, #e8e8e8 80%, #a0a0a0 100%)",
            "border"      : "#c0c0c0",
            "text"        : "#0d0d0d",
            "glow"        : "rgba(192,192,192,0.55)",
            "overlay_bg"  : "rgba(80,80,80,0.55)",
            "badge_bg"    : "rgba(120,120,120,0.4)",
            "badge_border": "rgba(200,200,200,0.6)",
            "stat_sep"    : "rgba(100,100,100,0.4)",
            "shimmer"     : "rgba(220,220,220,0.15)",
            "label_color" : "#222",
        }
    elif followers < 90000:
        tier       = "92"
        tier_label = "GOLD"
        colors = {
            "bg"          : "linear-gradient(160deg, #7a4f00 0%, #c8860a 35%, #f5c518 60%, #ffe066 80%, #c8860a 100%)",
            "border"      : "#ffd700",
            "text"        : "#2d1a00",
            "glow"        : "rgba(255,215,0,0.65)",
            "overlay_bg"  : "rgba(100,65,0,0.55)",
            "badge_bg"    : "rgba(180,120,0,0.45)",
            "badge_border": "rgba(255,215,0,0.7)",
            "stat_sep"    : "rgba(140,90,0,0.4)",
            "shimmer"     : "rgba(255,230,50,0.18)",
            "label_color" : "#3d2000",
        }
    else:
        tier       = "99"
        tier_label = "PLATINUM"
        colors = {
            "bg"          : "linear-gradient(160deg, #1a0033 0%, #3d0070 30%, #7b00d4 55%, #b44bff 75%, #4b0096 100%)",
            "border"      : "#c8a0ff",
            "text"        : "#f0e6ff",
            "glow"        : "rgba(180,100,255,0.75)",
            "overlay_bg"  : "rgba(40,0,80,0.6)",
            "badge_bg"    : "rgba(100,0,200,0.45)",
            "badge_border": "rgba(200,160,255,0.65)",
            "stat_sep"    : "rgba(140,60,220,0.45)",
            "shimmer"     : "rgba(200,160,255,0.15)",
            "label_color" : "#e0c8ff",
        }

    skills_html = "".join(
        [f'<span class="skill-badge">{s}</span>' for s in analysis.get("top_skills", [])[:3]]
    )

    vibe     = analysis.get("developer_vibe", "")
    fun_fact = analysis.get("fun_fact", "")

    html = f"""
    <div id="card-to-download"
         style="background:#0d1117; padding:40px 30px; display:inline-block;
                border-radius:24px; font-family:'Inter',sans-serif;">

      <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700;900&display=swap');

        /* ── Violent intro: shake + flash ── */
        @keyframes violent-shake {{
          0%,100% {{ transform: translateX(0) translateY(0) rotate(0deg); }}
          5%       {{ transform: translateX(-8px) translateY(-6px) rotate(-2deg); }}
          10%      {{ transform: translateX( 9px) translateY( 7px) rotate( 2deg); }}
          15%      {{ transform: translateX(-10px) translateY(-8px) rotate(-3deg); }}
          20%      {{ transform: translateX( 11px) translateY( 6px) rotate( 2deg); }}
          25%      {{ transform: translateX(-9px) translateY(-9px) rotate(-2deg); }}
          30%      {{ transform: translateX( 8px) translateY( 8px) rotate( 1deg); }}
          35%      {{ transform: translateX(-7px) translateY(-5px) rotate(-1deg); }}
          40%      {{ transform: translateX( 6px) translateY( 6px) rotate( 1deg); }}
          50%      {{ transform: translateX(-3px) translateY(-3px) rotate(0deg); }}
          60%      {{ transform: translateX( 2px) translateY( 2px) rotate(0deg); }}
          75%      {{ transform: translateX(-1px) translateY(-1px) rotate(0deg); }}
        }}

        /* Blinding white-out then fade */
        @keyframes thunder-blind {{
          0%       {{ filter: brightness(1)  blur(0px); opacity:0; }}
          5%       {{ filter: brightness(12) blur(4px); opacity:1; }}
          12%      {{ filter: brightness(20) blur(8px) contrast(2); }}
          20%      {{ filter: brightness(15) blur(6px); }}
          30%      {{ filter: brightness(8)  blur(3px); }}
          45%      {{ filter: brightness(4)  blur(1px); }}
          60%      {{ filter: brightness(2)  blur(0px); }}
          80%      {{ filter: brightness(1.2) blur(0); }}
          100%     {{ filter: brightness(1)  blur(0); opacity:1; }}
        }}

        /* Outer glow pulses during shake */
        @keyframes glow-pulse {{
          0%,100% {{ box-shadow: 0 0 40px {colors["glow"]}; }}
          10%     {{ box-shadow: 0 0 120px {colors["glow"]}, 0 0 200px white; }}
          20%     {{ box-shadow: 0 0 180px {colors["glow"]}, 0 0 260px white; }}
          35%     {{ box-shadow: 0 0 100px {colors["glow"]}; }}
          55%     {{ box-shadow: 0 0 70px  {colors["glow"]}; }}
        }}

        /* Shimmer sweep after reveal */
        @keyframes shimmer {{
          0%   {{ left: -120%; }}
          100% {{ left: 140%; }}
        }}

        .fifa-card {{
          width: 340px;
          height: 520px;
          background: {colors["bg"]};
          border: 3px solid {colors["border"]};
          clip-path: polygon(0% 12%, 50% 0%, 100% 12%, 100% 82%, 50% 100%, 0% 82%);
          color: {colors["text"]};
          position: relative;
          overflow: hidden;
          animation:
            violent-shake  1.6s ease-out             forwards,
            thunder-blind  1.6s ease-out             forwards,
            glow-pulse     1.6s ease-out             forwards;
        }}

        /* Shimmer stripe — runs once after reveal */
        .fifa-card::after {{
          content: '';
          position: absolute;
          top: 0; left: -120%;
          width: 60%; height: 100%;
          background: linear-gradient(
            105deg,
            transparent 30%,
            {colors["shimmer"]} 50%,
            transparent 70%
          );
          animation: shimmer 0.9s ease-in-out 1.7s forwards;
          pointer-events: none;
          z-index: 20;
        }}

        /* ── Top-left overlay (rating + DEV + tier) ── */
        .card-overlay-details {{
          position: absolute;
          top: 52px;
          left: 24px;
          display: flex;
          flex-direction: column;
          align-items: center;
          z-index: 10;
        }}

        .rating {{
          font-size: 52px;
          font-weight: 900;
          line-height: 1;
          color: {colors["text"]};
          text-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }}

        .position {{
          font-size: 15px;
          font-weight: 800;
          text-transform: uppercase;
          margin-top: -2px;
          color: {colors["text"]};
          letter-spacing: 1px;
        }}

        .tier-label {{
          font-size: 9px;
          font-weight: 900;
          letter-spacing: 2px;
          background: {colors["overlay_bg"]};
          border: 1px solid {colors["border"]};
          color: {colors["label_color"]};
          padding: 2px 7px;
          border-radius: 4px;
          margin-top: 4px;
          text-transform: uppercase;
        }}

        /* ── Profile photo ── sits right-side, clear of top label area ── */
        .player-image-wrap {{
          position: absolute;
          top: 48px;         /* below the clip-path top vertex */
          right: 0px;
          width: 200px;
          height: 200px;
          z-index: 5;
          /* Fade out toward left edge so it blends */
          -webkit-mask-image: linear-gradient(to left, black 55%, transparent 100%);
          mask-image:         linear-gradient(to left, black 55%, transparent 100%);
        }}

        .player-image {{
          width: 100%;
          height: 100%;
          object-fit: cover;
          object-position: top center;
          border-radius: 8px;
        }}

        /* ── Bottom info block ── */
        .bottom-info {{
          position: absolute;
          bottom: 118px;
          width: 100%;
          display: flex;
          flex-direction: column;
          align-items: center;
          z-index: 10;
          padding: 0 20px;
          gap: 6px;
        }}

        .player-name {{
          font-size: 24px;
          font-weight: 900;
          text-transform: uppercase;
          margin: 0;
          letter-spacing: -0.5px;
          text-align: center;
          color: {colors["text"]};
          text-shadow: 0 1px 6px rgba(0,0,0,0.25);
          width: 90%;
          border-bottom: 1.5px solid {colors["stat_sep"]};
          padding-bottom: 6px;
        }}

        .stats-row {{
          display: flex;
          gap: 0;
          width: 85%;
          justify-content: space-around;
        }}

        .stat {{
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: 4px 8px;
        }}

        .stat + .stat {{
          border-left: 1px solid {colors["stat_sep"]};
        }}

        .stat-val {{
          font-size: 18px;
          font-weight: 900;
          color: {colors["text"]};
        }}

        .stat-lbl {{
          font-size: 8px;
          font-weight: 700;
          opacity: 0.75;
          text-transform: uppercase;
          letter-spacing: 0.5px;
          color: {colors["text"]};
        }}

        .skills-wrap {{
          display: flex;
          flex-wrap: wrap;
          justify-content: center;
          gap: 4px;
          max-width: 260px;
        }}

        .skill-badge {{
          background: {colors["badge_bg"]};
          border: 1px solid {colors["badge_border"]};
          color: {colors["text"]};
          padding: 3px 9px;
          border-radius: 10px;
          font-size: 9px;
          font-weight: 700;
          letter-spacing: 0.3px;
        }}

        /* ── Vibe + fun-fact ── larger, fully visible ── */
        .vibe-block {{
          position: absolute;
          bottom: 52px;
          width: 100%;
          text-align: center;
          padding: 0 38px;
          z-index: 10;
          display: flex;
          flex-direction: column;
          gap: 2px;
        }}

        .vibe-text {{
          font-size: 9px;
          font-weight: 700;
          color: {colors["text"]};
          opacity: 0.9;
          line-height: 1.35;
          font-style: italic;
        }}

        .fun-text {{
          font-size: 8px;
          font-weight: 600;
          color: {colors["text"]};
          opacity: 0.7;
          line-height: 1.3;
        }}
      </style>

      <div class="fifa-card">

        <!-- Top-left: rating / DEV / tier -->
        <div class="card-overlay-details">
          <div class="rating">{tier}</div>
          <div class="position">DEV</div>
          <div class="tier-label">{tier_label}</div>
        </div>

        <!-- Profile photo — right side, starts below tier label row -->
        <div class="player-image-wrap">
          <img src="{github_data.get('avatar_url')}" class="player-image" crossorigin="anonymous">
        </div>

        <!-- Name + stats + skills -->
        <div class="bottom-info">
          <h2 class="player-name">{github_data.get('name', username).split()[0]}</h2>

          <div class="stats-row">
            <div class="stat">
              <span class="stat-val">{github_data.get('public_repos', 0)}</span>
              <span class="stat-lbl">REPOS</span>
            </div>
            <div class="stat">
              <span class="stat-val">{followers if followers < 1000 else str(round(followers/1000, 1))+'K'}</span>
              <span class="stat-lbl">FOLLOWERS</span>
            </div>
            <div class="stat">
              <span class="stat-val">{len(github_data.get('languages', []))}</span>
              <span class="stat-lbl">LANGS</span>
            </div>
          </div>

          <div class="skills-wrap">
            {skills_html}
          </div>
        </div>

        <!-- Vibe + fun fact — fully visible at bottom -->
        <div class="vibe-block">
          <div class="vibe-text">"{vibe}"</div>
          <div class="fun-text">{fun_fact}</div>
        </div>

      </div>
    </div>
    """
    return html

@mcp.tool()
def save_card(username: str, html: str) -> str:
    """Saves the HTML card to a static file and returns the path."""
    os.makedirs("static/cards", exist_ok=True)
    file_path = f"static/cards/{username}.html"
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(html)
    return f"/static/cards/{username}.html"

if __name__ == "__main__":
    mcp.run()
