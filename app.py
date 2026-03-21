import io
import os
import asyncio
import httpx
from contextlib import asynccontextmanager
from fastapi import FastAPI, Response, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, ImageDraw, ImageFont
from concurrent.futures import ThreadPoolExecutor

# ==================== ALL CONTROLS HERE ====================
# Banner Settings
TARGET_HEIGHT = 400

# Text Colors
STROKE_COLOR = "black"
TEXT_COLOR = "white"

# Font Sizes
FONT_LARGE_SIZE = 125
FONT_SMALL_SIZE = 95
FONT_LEVEL_SIZE = 50

# Text Positions - ADJUSTABLE NAMES
NAME_X_OFFSET = 25
NAME_Y = 35  # Name position (move up/down by changing this)
GUILD_X_OFFSET = 25
GUILD_Y = 240  # Guild position (move up/down by changing this)

# Stroke Sizes
NAME_STROKE_SIZE = 2
GUILD_STROKE_SIZE = 2
LEVEL_STROKE_SIZE = 3

# Pin Settings
PIN_SIZE = 130
PIN_X = 0
PIN_Y_OFFSET = TARGET_HEIGHT - PIN_SIZE  # Bottom left

# Level Text Settings (No Background)
LEVEL_X_PADDING = 25
LEVEL_Y_PADDING = 16
LEVEL_Y_OFFSET = -6

# Banner Crop Settings
BANNER_ROTATION = 3
CROP_TOP = 0.23
CROP_BOTTOM = 0.32
CROP_SIDES = 0.17
BANNER_WIDTH_MULTIPLIER = 2.0

# Font Files
FONT_FILE = "arial_unicode_bold.otf"
FONT_CHEROKEE = "NotoSansCherokee.ttf"

# API Settings
INFO_API_URL = "https://flash-player-info.vercel.app/info"

# API Keys - SEPARATE KEYS
INFO_API_KEY = "Flash"  # Key for info API
BANNER_API_KEY = "Flash2hour"  # Key for banner API (you can change this)

# ========== DEFAULT IMAGES ==========
DEFAULT_AVATAR_URL = "https://i.postimg.cc/8ccqg7dq/IMG-20260320-124950.jpg"
DEFAULT_BANNER_URL = "https://i.postimg.cc/cv5BRLKr/IMG-20260320-124918.jpg"
# =====================================
# ============================================================

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
        return ImageFont.load_default()
    except:
        return ImageFont.load_default()

async def fetch_image_bytes(item_id):
    if not item_id or str(item_id) == "0" or item_id is None:
        return None

    item_id = str(item_id)
    
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
                resp = await client.head(url)
                if resp.status_code == 200:
                    img_resp = await client.get(url)
                    return img_resp.content
            except:
                continue
    return None

async def fetch_default_image(url):
    """Fetch default image from URL"""
    try:
        resp = await client.get(url)
        if resp.status_code == 200:
            return resp.content
    except:
        pass
    return None

def bytes_to_image(img_bytes, is_default=False):
    if not img_bytes:
        return Image.new('RGBA', (100, 100), (0, 0, 0, 0))
    
    img = Image.open(io.BytesIO(img_bytes)).convert("RGBA")
    
    # Agar default image hai to text wala part crop kar do
    if is_default:
        width, height = img.size
        # Sirf neeche ke text wale part ko crop karo (30% height)
        crop_height = int(height * 0.7)  # 70% rakho, 30% text wala hatado
        img = img.crop((0, 0, width, crop_height))
    
    return img

def draw_text_with_stroke(draw, x, y, text, font, stroke_size, stroke_color, text_color):
    """Draw text with stroke effect - सबके लिए common function"""
    if stroke_size > 0:
        # Pehle stroke draw karo (black)
        for dx in range(-stroke_size, stroke_size + 1):
            for dy in range(-stroke_size, stroke_size + 1):
                if dx != 0 or dy != 0:  # Center ko skip karo
                    draw.text((x + dx, y + dy), text, font=font, fill=stroke_color)
    
    # Phir original text draw karo (white)
    draw.text((x, y), text, font=font, fill=text_color)

def process_banner_image(data, avatar_bytes, banner_bytes, pin_bytes, is_default_avatar=False, is_default_banner=False):
    avatar_img = bytes_to_image(avatar_bytes, is_default_avatar)
    banner_img = bytes_to_image(banner_bytes, is_default_banner)
    pin_img = bytes_to_image(pin_bytes, False)

    level = str(data.get("AccountLevel", "0"))
    name = data.get("AccountName", "Unknown")
    guild = data.get("GuildName", "")

    # Avatar
    avatar_img = avatar_img.resize((TARGET_HEIGHT, TARGET_HEIGHT), Image.LANCZOS)
    
    # Banner processing
    b_w, b_h = banner_img.size
    if b_w > 50 and b_h > 50:
        banner_img = banner_img.rotate(BANNER_ROTATION, resample=Image.BICUBIC, expand=True)
        b_w, b_h = banner_img.size
        
        left, top = b_w * CROP_SIDES, b_h * CROP_TOP
        right, bottom = b_w * (1 - CROP_SIDES), b_h * (1 - CROP_BOTTOM)
        banner_img = banner_img.crop((left, top, right, bottom))

    b_w, b_h = banner_img.size
    if b_h > 0:
        new_banner_w = int(TARGET_HEIGHT * (b_w / b_h) * BANNER_WIDTH_MULTIPLIER)
        banner_img = banner_img.resize((new_banner_w, TARGET_HEIGHT), Image.LANCZOS)
    else:
        banner_img = Image.new("RGBA", (800, 400), (50, 50, 50))

    # Combine images
    final_w = TARGET_HEIGHT + new_banner_w
    final_h = TARGET_HEIGHT
    combined = Image.new("RGBA", (final_w, final_h), (0, 0, 0, 0))
    combined.paste(avatar_img, (0, 0))
    combined.paste(banner_img, (TARGET_HEIGHT, 0))
    
    draw = ImageDraw.Draw(combined)
    
    # Load fonts
    font_large = load_unicode_font(FONT_LARGE_SIZE) 
    font_large_cherokee = load_unicode_font(FONT_LARGE_SIZE, FONT_CHEROKEE)
    font_small = load_unicode_font(FONT_SMALL_SIZE) 
    font_small_cherokee = load_unicode_font(FONT_SMALL_SIZE, FONT_CHEROKEE)
    font_level = load_unicode_font(FONT_LEVEL_SIZE)

    text_x = TARGET_HEIGHT + 40 
    
    def is_cherokee(char):
        code = ord(char)
        return (0x13A0 <= code <= 0x13FF) or (0xAB70 <= code <= 0xABBF)

    # Draw name WITH stroke (हल्का स्ट्रोक)
    current_x = text_x + NAME_X_OFFSET
    for char in name:
        font = font_large_cherokee if is_cherokee(char) else font_large
        draw_text_with_stroke(draw, current_x, NAME_Y, char, font, NAME_STROKE_SIZE, STROKE_COLOR, TEXT_COLOR)
        current_x += font.getlength(char)

    # Draw guild WITH stroke (हल्का स्ट्रोक)
    current_x = text_x + GUILD_X_OFFSET
    for char in guild:
        font = font_small_cherokee if is_cherokee(char) else font_small
        draw_text_with_stroke(draw, current_x, GUILD_Y, char, font, GUILD_STROKE_SIZE, STROKE_COLOR, TEXT_COLOR)
        current_x += font.getlength(char)

    # Add pin if exists
    if pin_img and pin_img.size != (100, 100):
        pin_img = pin_img.resize((PIN_SIZE, PIN_SIZE), Image.LANCZOS)
        combined.paste(pin_img, (PIN_X, PIN_Y_OFFSET), pin_img)

    # Draw level text WITH stroke (थोड़ा ज्यादा स्ट्रोक)
    level_txt = f"Lvl.{level}"
    text_width = draw.textlength(level_txt, font=font_level)
    text_height = FONT_LEVEL_SIZE
    
    # Position at bottom right
    level_x = final_w - text_width - LEVEL_X_PADDING
    level_y = final_h - text_height - LEVEL_Y_PADDING + LEVEL_Y_OFFSET
    
    # Draw level with stroke
    draw_text_with_stroke(draw, level_x, level_y, level_txt, font_level, LEVEL_STROKE_SIZE, STROKE_COLOR, TEXT_COLOR)

    img_io = io.BytesIO()
    combined.save(img_io, 'PNG')
    img_io.seek(0)
    return img_io

@app.get("/")
async def home():
    return {
        "message": "⚡ Ultra Fast Banner API Running",
        "Fix By": "FL4SH_FF",
        "Telegram": "@flash_ff_70",
        "Your Info Api": INFO_API_URL,
        "Api Endpoint": "/banner?uid={uid}&key={banner_key}",
        "Note": "Join To @flash_ff_70 For More 💝",
        "API Keys": {
            "info_api_key": INFO_API_KEY,
            "banner_api_key": BANNER_API_KEY
        }
    }

@app.get("/banner")
async def get_banner(uid: str, key: str):
    # Check banner API key first
    if not uid or not key:
        raise HTTPException(status_code=400, detail="UID and Banner API Key required")
    
    if key != BANNER_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid Banner API Key")

    try:
        # Call info API with its own key
        resp = await client.get(f"{INFO_API_URL}?uid={uid}&key={INFO_API_KEY}")
        
        if resp.status_code != 200:
            raise HTTPException(status_code=502, detail="Info API Error")
            
        data = resp.json()
        
        basic_info = data.get("basicInfo", {})
        clan_basic_info = data.get("clanBasicInfo", {})
        
        if not basic_info: 
            raise HTTPException(status_code=404, detail="Not Found")
        
        # headPic se avatar lenge
        avatar_task = fetch_image_bytes(basic_info.get("headPic"))
        banner_task = fetch_image_bytes(basic_info.get("bannerId"))
        pin_task = fetch_image_bytes(basic_info.get("pinId"))

        results = await asyncio.gather(avatar_task, banner_task, pin_task)
        avatar_bytes, banner_bytes, pin_bytes = results[0], results[1], results[2]
        
        # Flags for default images
        is_default_avatar = False
        is_default_banner = False
        
        # Agar avatar nahi mila to default avatar fetch karo
        if avatar_bytes is None:
            default_avatar = await fetch_default_image(DEFAULT_AVATAR_URL)
            if default_avatar:
                avatar_bytes = default_avatar
                is_default_avatar = True
        
        # Agar banner nahi mila to default banner fetch karo
        if banner_bytes is None:
            default_banner = await fetch_default_image(DEFAULT_BANNER_URL)
            if default_banner:
                banner_bytes = default_banner
                is_default_banner = True
        
        if pin_bytes is None: 
            pin_bytes = b''

        loop = asyncio.get_event_loop()
        banner_data = {
            "AccountLevel": basic_info.get("level", "0"),
            "AccountName": basic_info.get("nickname", "Unknown"),
            "GuildName": clan_basic_info.get("clanName", "")
        }
        
        img_io = await loop.run_in_executor(
            process_pool, 
            process_banner_image, 
            banner_data, avatar_bytes, banner_bytes, pin_bytes, is_default_avatar, is_default_banner
        )
        
        return Response(content=img_io.getvalue(), media_type="image/png", headers={"Cache-Control": "public, max-age=300"})

    except Exception as e:
        print(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=5000)