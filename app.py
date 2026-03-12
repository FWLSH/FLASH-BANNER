import io
import os
import asyncio
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await client.aclose()
    process_pool.shutdown()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

INFO_API_URL = "https://flash-player-info.vercel.app/info?uid={uid}&key=Flash"
FONT_FILE = "arial_unicode_bold.otf"
FONT_CHEROKEE = "NotoSansCherokee.ttf"

# ========== YAHAN VALUES CHANGE KARO ==========
class BannerConfig:
    # Avatar Control
    AVATAR_SIZE = 600  # Avatar ka size
    
    # Banner Control
    BANNER_WIDTH_MULTIPLIER = 2.2
    BANNER_ROTATION = 3
    BANNER_CROP_TOP = 0.20
    BANNER_CROP_BOTTOM = 0.30
    BANNER_CROP_SIDES = 0.17
    
    # NAME CONTROL
    NAME_POS_X = 40      # Left-Right
    NAME_POS_Y = 40      # Up-Down
    FONT_SIZE_NAME = 170 # Name ka font size
    
    # GUILD CONTROL
    GUILD_POS_Y_OFFSET = 300  # Name se kitna niche
    FONT_SIZE_GUILD = 150     # Guild ka font size
    
    # LEVEL CONTROL - SIRF TEXT, BOX NAHI
    FONT_SIZE_LEVEL = 70      # Level ka font size
    LEVEL_POS_X = 40          # Right side se distance
    LEVEL_POS_Y = 60          # ⬆️ YAHAN CHANGE KARO - jitna niche chahiye utna bada
    
    # PIN CONTROL
    PIN_SIZE = 150
    PIN_POS_X = 20                 # Left-Right
    PIN_POS_Y_FROM_BOTTOM = 100    # Bottom se distance
# ==============================================

client = httpx.AsyncClient(
    headers={"User-Agent": "Mozilla/5.0"},
    timeout=10.0,
    follow_redirects=True
)

process_pool = ThreadPoolExecutor(max_workers=4)

def load_unicode_font(size, font_file=FONT_FILE):
    try:
        font_path = os.path.join(os.path.dirname(__file__), font_file)
        if os.path.exists(font_path):
            return ImageFont.truetype(font_path, size)
        return ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", size) if os.path.exists("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf") else ImageFont.load_default()
    except:
        return ImageFont.load_default()

async def fetch_image_bytes(item_id):
    if not item_id or str(item_id) == "0" or item_id is None:
        return None

    item_id = str(item_id)
    print(f"Fetching image for ID: {item_id}")
    
    direct_urls = [
        f"https://raw.githubusercontent.com/KISHAN-FF-MAHTO/free-fire/main/items/{item_id}.png",
        f"https://raw.githubusercontent.com/djdndbdjdi/ff-assets/main/icons/{item_id}.png",
        f"https://raw.githubusercontent.com/akshitmittal1/free-fire-assets/main/images/{item_id}.png",
        f"https://raw.githubusercontent.com/TheVivekGoyal/FreeFire-Assets/main/Images/{item_id}.png"
    ]
    
    for url in direct_urls:
        try:
            resp = await client.get(url, timeout=5.0)
            if resp.status_code == 200 and resp.content:
                print(f"✅ Found image at: {url}")
                return resp.content
        except:
            continue
    
    for repo_num in range(1, 7):
        if repo_num == 1: 
            batch_start, batch_end = 1, 7
        else:
            batch_start = (repo_num - 1) * 6 + 1
            batch_end = batch_start + 6
            
        for batch_num in range(batch_start, batch_end):
            batch_str = f"{batch_num:02d}"
            url = f"https://raw.githubusercontent.com/djdndbdjfi/free-fire-items-{repo_num}/main/items/batch-{batch_str}/{item_id}.png"
            
            try:
                resp = await client.get(url, timeout=3.0)
                if resp.status_code == 200 and resp.content:
                    print(f"✅ Found in repo {repo_num}, batch {batch_str}")
                    return resp.content
            except:
                continue
    
    print(f"❌ No image found for ID: {item_id}")
    return None

def bytes_to_image(img_bytes):
    if img_bytes:
        try:
            return Image.open(io.BytesIO(img_bytes)).convert("RGBA")
        except:
            return None
    return None

def process_banner_image(data, avatar_bytes, banner_bytes, pin_bytes):
    try:
        print("Processing banner image...")
        
        TARGET_HEIGHT = BannerConfig.AVATAR_SIZE
        
        # Avatar - AGAR IMAGE NAHI MILI TO SIRF TRANSPARENT
        if avatar_bytes:
            try:
                avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
                avatar_img = avatar_img.resize((TARGET_HEIGHT, TARGET_HEIGHT), Image.LANCZOS)
            except:
                avatar_img = Image.new('RGBA', (TARGET_HEIGHT, TARGET_HEIGHT), (0, 0, 0, 0))
        else:
            avatar_img = Image.new('RGBA', (TARGET_HEIGHT, TARGET_HEIGHT), (0, 0, 0, 0))
        
        # Banner - AGAR IMAGE NAHI MILI TO SIRF TRANSPARENT
        if banner_bytes:
            try:
                banner_img = Image.open(io.BytesIO(banner_bytes)).convert("RGBA")
                banner_img = banner_img.rotate(BannerConfig.BANNER_ROTATION, resample=Image.BICUBIC, expand=True)
                b_w, b_h = banner_img.size
                
                left, top = b_w * BannerConfig.BANNER_CROP_SIDES, b_h * BannerConfig.BANNER_CROP_TOP
                right, bottom = b_w * (1 - BannerConfig.BANNER_CROP_SIDES), b_h * (1 - BannerConfig.BANNER_CROP_BOTTOM)
                banner_img = banner_img.crop((left, top, right, bottom))
                
                b_w, b_h = banner_img.size
                new_banner_w = int(TARGET_HEIGHT * (b_w / b_h) * BannerConfig.BANNER_WIDTH_MULTIPLIER)
                banner_img = banner_img.resize((new_banner_w, TARGET_HEIGHT), Image.LANCZOS)
            except:
                new_banner_w = int(TARGET_HEIGHT * BannerConfig.BANNER_WIDTH_MULTIPLIER)
                banner_img = Image.new('RGBA', (new_banner_w, TARGET_HEIGHT), (0, 0, 0, 0))
        else:
            new_banner_w = int(TARGET_HEIGHT * BannerConfig.BANNER_WIDTH_MULTIPLIER)
            banner_img = Image.new('RGBA', (new_banner_w, TARGET_HEIGHT), (0, 0, 0, 0))

        # Final image - COMPLETELY TRANSPARENT
        final_w = TARGET_HEIGHT + new_banner_w
        final_h = TARGET_HEIGHT
        combined = Image.new("RGBA", (final_w, final_h), (0, 0, 0, 0))
        
        # Paste images
        combined.paste(avatar_img, (0, 0), avatar_img)
        combined.paste(banner_img, (TARGET_HEIGHT, 0), banner_img)
        
        # Draw text
        draw = ImageDraw.Draw(combined)
        
        try:
            font_large = load_unicode_font(BannerConfig.FONT_SIZE_NAME)
            font_small = load_unicode_font(BannerConfig.FONT_SIZE_GUILD)
            font_level = load_unicode_font(BannerConfig.FONT_SIZE_LEVEL)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
            font_level = ImageFont.load_default()

        level = str(data.get("AccountLevel", "0"))
        name = data.get("AccountName", "Unknown")
        guild = data.get("GuildName", "")
        
        text_x = TARGET_HEIGHT + BannerConfig.NAME_POS_X
        text_y = BannerConfig.NAME_POS_Y
        
        # Name with stroke only
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx*dx + dy*dy <= 9:
                    draw.text((text_x + dx, text_y + dy), name, font=font_large, fill="black")
        draw.text((text_x, text_y), name, font=font_large, fill="white")
        
        # Guild with stroke only
        if guild and guild.strip():
            for dx in range(-2, 3):
                for dy in range(-2, 3):
                    if dx*dx + dy*dy <= 4:
                        draw.text((text_x + dx, text_y + BannerConfig.GUILD_POS_Y_OFFSET + dy), guild, font=font_small, fill="black")
            draw.text((text_x, text_y + BannerConfig.GUILD_POS_Y_OFFSET), guild, font=font_small, fill="white")
        
        # Pin
        if pin_bytes:
            try:
                pin_img = Image.open(io.BytesIO(pin_bytes)).convert("RGBA")
                pin_size = BannerConfig.PIN_SIZE
                pin_img = pin_img.resize((pin_size, pin_size), Image.LANCZOS)
                combined.paste(pin_img, (BannerConfig.PIN_POS_X, TARGET_HEIGHT - pin_size - BannerConfig.PIN_POS_Y_FROM_BOTTOM), pin_img)
            except:
                pass
        
        # ===== LEVEL - SIRF TEXT, KOI BOX NAHI =====
        level_txt = f"LVL {level}"
        
        # Level text position - bottom right corner
        bbox = draw.textbbox((0, 0), level_txt, font=font_level)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]
        
        text_x_pos = final_w - text_w - BannerConfig.LEVEL_POS_X
        text_y_pos = final_h - text_h - BannerConfig.LEVEL_POS_Y
        
        # Text stroke
        for dx in range(-2, 3):
            for dy in range(-2, 3):
                if dx*dx + dy*dy <= 4:
                    draw.text((text_x_pos + dx, text_y_pos + dy), level_txt, font=font_level, fill="black")
        
        # White text
        draw.text((text_x_pos, text_y_pos), level_txt, font=font_level, fill="white")
        # ===========================================

        img_io = io.BytesIO()
        combined.save(img_io, 'PNG', optimize=True, quality=100)
        img_io.seek(0)
        print("✅ HD Banner generated successfully!")
        return img_io
        
    except Exception as e:
        print(f"Process error: {e}")
        blank = Image.new('RGBA', (1400, 600), (0, 0, 0, 0))
        draw = ImageDraw.Draw(blank)
        draw.text((500, 250), "Banner Error", fill="white")
        draw.text((500, 300), str(e)[:50], fill="red")
        img_io = io.BytesIO()
        blank.save(img_io, 'PNG')
        img_io.seek(0)
        return img_io

@app.get("/")
async def home():
    return {
        "message": "✅ Free Fire HD Banner API",
        "endpoint": "/banner?uid={uid}",
        "example": "/banner?uid=3419823759",
        "quality": "HD 600px",
        "background": "Transparent"
    }

@app.get("/profile")
@app.get("/banner")
async def get_banner(uid: str):
    if not uid:
        raise HTTPException(status_code=400, detail="UID required")

    try:
        resp = await client.get(f"https://flash-player-info.vercel.app/info?uid={uid}&key=Flash")
        
        resp.raise_for_status()
        data = resp.json()

        basic_info = data.get("basicInfo", {})
        profile_info = data.get("profileInfo", {})
        clan_info = data.get("clanBasicInfo", {})

        avatar_id = profile_info.get("headPic") or basic_info.get("headPic")
        banner_id = basic_info.get("bannerId")
        pin_id = basic_info.get("pinId") or basic_info.get("titl")

        avatar_task = fetch_image_bytes(avatar_id)
        banner_task = fetch_image_bytes(banner_id)
        pin_task = fetch_image_bytes(pin_id) if (pin_id and str(pin_id) != "0") else asyncio.sleep(0)

        results = await asyncio.gather(avatar_task, banner_task, pin_task)
        avatar_bytes, banner_bytes, pin_bytes = results[0], results[1], results[2]
        if pin_bytes is None: pin_bytes = b''

        loop = asyncio.get_event_loop()
        banner_data = {
            "AccountLevel": basic_info.get("level") or 0,
            "AccountName": basic_info.get("nickname") or "Unknown",
            "GuildName": clan_info.get("clanName") or ""
        }

        img_io = await loop.run_in_executor(
            process_pool,
            process_banner_image,
            banner_data, avatar_bytes, banner_bytes, pin_bytes
        )

        return Response(
            content=img_io.getvalue(),
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=300"}
        )

    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Info API request failed: {e}")
    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    print("="*50)
    print("🚀 Free Fire HD Banner API")
    print("="*50)
    print("📍 http://127.0.0.1:5000")
    print("📝 http://127.0.0.1:5000/banner?uid=3419823759")
    print("="*50)
    uvicorn.run(app, host="127.0.0.1", port=5000)