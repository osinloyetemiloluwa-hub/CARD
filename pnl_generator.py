from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import BytesIO
import requests
import os
from typing import Optional, Tuple
import hashlib
import math
import urllib.request

class PNLCardGenerator:
    def __init__(self):
        self.width, self.height = 1200, 675
        self.cache_dir = "/tmp/pnl_cache"
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Colors
        self.colors = {
            'bg_dark': (10, 10, 15, 255),
            'red_glow': (255, 40, 40),
            'orange': (255, 140, 50),
            'orange_dark': (200, 90, 20),
            'white': (255, 255, 255),
            'gray': (150, 150, 150),
            'dark_overlay': (0, 0, 0, 180),
            'frame_green': (30, 90, 50, 255) # Border color from reference
        }

        # Download Fonts on startup
        self.font_regular = self.get_font(32, "Montserrat-Medium.ttf")
        self.font_bold = self.get_font(36, "Montserrat-ExtraBold.ttf")
        self.font_title = self.get_font(85, "Montserrat-ExtraBold.ttf")
        self.font_mult = self.get_font(140, "Montserrat-Black.ttf")
        self.font_small = self.get_font(20, "Montserrat-Medium.ttf")

    def get_font(self, size: int, font_name: str) -> ImageFont.FreeTypeFont:
        """Downloads and loads the specific font from Google Fonts GitHub"""
        font_path = os.path.join(self.cache_dir, font_name)
        if not os.path.exists(font_path):
            try:
                url = f"https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/{font_name}"
                urllib.request.urlretrieve(url, font_path)
            except Exception as e:
                print(f"Failed to download font {font_name}: {e}")
                # Fallback to default if download fails
                return ImageFont.load_default()
        return ImageFont.truetype(font_path, size)

    def download_image(self, url: str, cache_key: str = None) -> Optional[Image.Image]:
        if not url: return None
        if not cache_key: cache_key = hashlib.md5(url.encode()).hexdigest()
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.png")
        
        if os.path.exists(cache_path):
            try: return Image.open(cache_path).convert('RGBA')
            except: pass
        
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            img = Image.open(BytesIO(response.content)).convert('RGBA')
            img.save(cache_path)
            return img
        except:
            return None

    def create_background(self, bg_image_url: Optional[str], dark_transparent: bool) -> Image.Image:
        if bg_image_url:
            bg = self.download_image(bg_image_url)
            if bg:
                bg_ratio = bg.width / bg.height
                target_ratio = self.width / self.height
                if bg_ratio > target_ratio:
                    new_width = int(bg.height * target_ratio)
                    offset = (bg.width - new_width) // 2
                    bg = bg.crop((offset, 0, offset + new_width, bg.height))
                else:
                    new_height = int(bg.width / target_ratio)
                    offset = (bg.height - new_height) // 2
                    bg = bg.crop((0, offset, bg.width, offset + new_height))
                bg = bg.resize((self.width, self.height), Image.Resampling.LANCZOS)
                
                if dark_transparent:
                    # Darken heavily to match reference
                    overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 200))
                    bg = Image.alpha_composite(bg, overlay)
                return bg
        
        # Fallback dark background
        img = Image.new('RGBA', (self.width, self.height), (5, 5, 5, 255))
        draw = ImageDraw.Draw(img)
        # Subtle red glow in background
        for i in range(80):
            alpha = int(40 * (1 - i/80))
            radius = 600 - i*8
            draw.ellipse([300-radius, 337-radius, 300+radius, 337+radius], fill=(255, 0, 0, alpha))
        return img

    def crop_to_circle(self, img: Image.Image, size: int) -> Image.Image:
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        mask = Image.new('L', (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.ellipse((0, 0, size, size), fill=255)
        output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        output.paste(img, (0, 0), mask)
        return output

    def crop_to_rounded_square(self, img: Image.Image, size: int, radius: int) -> Image.Image:
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        mask = Image.new('L', (size, size), 0)
        mask_draw = ImageDraw.Draw(mask)
        mask_draw.rounded_rectangle((0, 0, size, size), radius=radius, fill=255)
        output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        output.paste(img, (0, 0), mask)
        return output

    def generate_card(self,
                     name: str,
                     multiplier: str,
                     initial_market_cap: str,
                     time_str: str,
                     author_username: str,
                     blockchain_logo_url: Optional[str] = None,
                     custom_logo_url: Optional[str] = None,
                     background_image_url: Optional[str] = None,
                     dark_transparent: bool = True) -> BytesIO:
        
        img = self.create_background(background_image_url, dark_transparent)
        
        # === 1. CUSTOM LOGO (Left) ===
        if custom_logo_url:
            logo = self.download_image(custom_logo_url)
            if logo:
                logo_size = 220
                logo_img = self.crop_to_circle(logo, logo_size)
                logo_x, logo_y = 80, (self.height - logo_size) // 2
                
                # Red ring around logo
                draw = ImageDraw.Draw(img)
                draw.ellipse([logo_x-4, logo_y-4, logo_x+logo_size+4, logo_y+logo_size+4], outline=(200, 0, 0, 255), width=4)
                img.paste(logo_img, (logo_x, logo_y), logo_img)

        # === 2. BLOCKCHAIN LOGO (Top Middle) ===
        draw = ImageDraw.Draw(img)
        if blockchain_logo_url:
            chain_logo = self.download_image(blockchain_logo_url)
            if chain_logo:
                chain_size = 50
                chain_img = self.crop_to_rounded_square(chain_logo, chain_size, radius=12)
                chain_x = (self.width - chain_size) // 2
                chain_y = 25
                # Draw blue border behind it
                draw.rounded_rectangle([chain_x-4, chain_y-4, chain_x+chain_size+4, chain_y+chain_size+4], radius=16, fill=(30, 60, 150, 255))
                img.paste(chain_img, (chain_x, chain_y), chain_img)

        # === 3. UI ELEMENTS (Top Right Menu) ===
        menu_x, menu_y = self.width - 60, 40
        for i in range(3):
            draw.rectangle([menu_x, menu_y + (i*8), menu_x + 20, menu_y + (i*8) + 2], fill=self.colors['white'])

        # === 4. NAME/TITLE (Top Right) ===
        title_text = name.upper()
        title_bbox = draw.textbbox((0, 0), title_text, font=self.font_title)
        title_x = self.width - 80 - (title_bbox[2] - title_bbox[0])
        draw.text((title_x, 90), title_text, font=self.font_title, fill=self.colors['white'])

        # === 5. MULTIPLIER (Center Right, 3D Effect) ===
        mult_text = multiplier
        mult_bbox = draw.textbbox((0, 0), mult_text, font=self.font_mult)
        mult_w = mult_bbox[2] - mult_bbox[0]
        mult_h = mult_bbox[3] - mult_bbox[1]
        
        # Create a separate layer for 3D text so we can rotate it
        txt_layer = Image.new('RGBA', (mult_w + 100, mult_h + 100), (0,0,0,0))
        txt_draw = ImageDraw.Draw(txt_layer)
        
        # 3D Extrusion (draw shadow multiple times)
        for i in range(12, 0, -1):
            txt_draw.text((50 + i, 50 + i), mult_text, font=self.font_mult, fill=self.colors['orange_dark'])
            
        # Main Orange Text
        txt_draw.text((50, 50), mult_text, font=self.font_mult, fill=self.colors['orange'])
        
        # Rotate slightly (like reference)
        txt_layer = txt_layer.rotate(5, expand=False, resample=Image.Resampling.BICUBIC)
        
        # Create Red Glow Shadow
        glow_layer = Image.new('RGBA', txt_layer.size, (0,0,0,0))
        glow_layer.paste(txt_layer, (0,0), txt_layer)
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(15))
        
        # Colorize glow to red
        red_glow = Image.new('RGBA', glow_layer.size, (255, 0, 0, 150))
        red_glow.putalpha(glow_layer.getchannel('A'))
        
        # Paste Glow and Text
        mult_x = self.width - 80 - (mult_w + 50)
        mult_y = 220
        img.paste(red_glow, (mult_x - 20, mult_y - 20), red_glow)
        img.paste(txt_layer, (mult_x - 50, mult_y - 50), txt_layer)

        # === 6. SUBTITLE (Called at...) ===
        draw = ImageDraw.Draw(img)
        info_text = f"Called at {initial_market_cap} | {time_str}"
        info_bbox = draw.textbbox((0, 0), info_text, font=self.font_regular)
        info_x = self.width - 80 - (info_bbox[2] - info_bbox[0])
        draw.text((info_x, 460), info_text, font=self.font_regular, fill=self.colors['white'])

        # === 7. AUTHOR (Bottom Right) ===
        author_text = author_username.upper()
        author_bbox = draw.textbbox((0, 0), author_text, font=self.font_bold)
        author_x = self.width - 80 - (author_bbox[2] - author_bbox[0])
        draw.text((author_x, 550), author_text, font=self.font_bold, fill=self.colors['white'])
        
        # Author Avatar Circle (Empty outline like reference)
        circle_size = 24
        draw.ellipse([author_x - 45, 555, author_x - 45 + circle_size, 555 + circle_size], outline=self.colors['white'], width=3)

        # === 8. WATERMARKS (Bottom Center) ===
        wm_text_1 = "@phanes_bot"
        wm_text_2 = "@phanesbot"
        
        # Calculate positions for center alignment
        wm1_bbox = draw.textbbox((0,0), wm_text_1, font=self.font_small)
        wm2_bbox = draw.textbbox((0,0), wm_text_2, font=self.font_small)
        total_w = (wm1_bbox[2]-wm1_bbox[0]) + (wm2_bbox[2]-wm2_bbox[0]) + 80 # 80px gap
        
        start_x = (self.width - total_w) // 2
        y_pos = 630
        
        # Discord Icon (Fake circle)
        draw.ellipse([start_x, y_pos+2, start_x+16, y_pos+18], outline=self.colors['white'], width=2)
        draw.text((start_x + 25, y_pos), wm_text_1, font=self.font_small, fill=self.colors['white'])
        
        # Twitter Icon (Fake circle)
        x2 = start_x + (wm1_bbox[2]-wm1_bbox[0]) + 60
        draw.ellipse([x2, y_pos+2, x2+16, y_pos+18], outline=self.colors['white'], width=2)
        draw.text((x2 + 25, y_pos), wm_text_2, font=self.font_small, fill=self.colors['white'])

        # === 9. UI FRAME (Outer Border) ===
        # Draw a subtle rounded border around the whole card
        draw.rounded_rectangle([15, 15, self.width-15, self.height-15], radius=20, outline=self.colors['frame_green'], width=2)

        # Convert to RGB
        final_img = img.convert('RGB')
        img_io = BytesIO()
        final_img.save(img_io, 'PNG', quality=100)
        img_io.seek(0)
        return img_io

# Singleton
generator = PNLCardGenerator()