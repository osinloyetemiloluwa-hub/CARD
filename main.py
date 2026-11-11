from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
from urllib.parse import urlencode
import uvicorn
from pnl_generator import generator  # CRITICAL FIX: Import the generator

app = FastAPI(
    title="PNL Image Generator API",
    description="Generate PNL cards for Discord",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/generate")
def generate_pnl_image(  # NOTE: Removed 'async' so it runs in a threadpool and doesn't block the server
    # Required parameters
    name: str = Query(..., max_length=30, description="Token/Project name (e.g., FLOAT)"),
    multiplier: str = Query(..., max_length=15, description="Multiplier (e.g., 104x)"),
    initial_market_cap: str = Query(..., max_length=15, description="Initial MC (e.g., 72.3K)"),
    author_username: str = Query(..., max_length=30, description="Username (e.g., VEXMORR)"),
    
    # Optional parameters
    time_str: str = Query("9d, 21h", max_length=20, description="Time since call"),
    blockchain_logo: Optional[str] = Query(None, description="URL to blockchain logo (top middle)"),
    custom_logo: Optional[str] = Query(None, description="URL to custom logo (left side)"),
    background_image: Optional[str] = Query(None, description="URL to background image"),
    dark_transparent: bool = Query(True, description="Apply dark transparent overlay")
):
    """
    Generate PNL card image with custom parameters.
    """
    try:
        image_stream = generator.generate_card(
            name=name,
            multiplier=multiplier,
            initial_market_cap=initial_market_cap,
            time_str=time_str,
            author_username=author_username,
            blockchain_logo_url=blockchain_logo,
            custom_logo_url=custom_logo,
            background_image_url=background_image,
            dark_transparent=dark_transparent
        )
        
        filename = f"pnl_{name}_{multiplier}.png"
        
        return StreamingResponse(
            image_stream,
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename={filename}",
                "Cache-Control": "public, max-age=3600"
            }
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")

@app.get("/api/generate/batch")
async def generate_batch_urls(
    name: str,
    multiplier: str,
    initial_market_cap: str,
    author_username: str,
    time_str: str = "9d, 21h",
    blockchain_logo: Optional[str] = None,
    custom_logo: Optional[str] = None,
    background_image: Optional[str] = None,
    dark_transparent: bool = True,
    base_url: str = Query(..., description="Your Render API base URL (e.g., https://your-app.onrender.com)")
):
    """Returns pre-built URLs that can be used directly in Discord embeds"""
    
    # FIX: Properly URL-encode parameters to prevent broken links if names have spaces
    params = {
        "name": name,
        "multiplier": multiplier,
        "initial_market_cap": initial_market_cap,
        "author_username": author_username,
        "time_str": time_str,
        "dark_transparent": str(dark_transparent).lower()
    }
    
    if blockchain_logo:
        params["blockchain_logo"] = blockchain_logo
    if custom_logo:
        params["custom_logo"] = custom_logo
    if background_image:
        params["background_image"] = background_image
    
    image_url = f"{base_url}/api/generate?{urlencode(params)}"
    
    return JSONResponse({
        "image_url": image_url,
        "discord_embed": {
            "title": f"{name} - {multiplier}",
            "color": 0xff3838,
            "image": {"url": image_url},
            "footer": {"text": f"Called by {author_username}"}
        }
    })

@app.get("/health")
async def health():
    return {"status": "ok", "generator": "ready"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)