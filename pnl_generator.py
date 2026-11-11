from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
from io import BytesIO
import requests
import os
from typing import Optional, Tuple
import hashlib

class PNLCardGenerator:
    def __init__(self):
        self.width, self.height = 1200, 675
        self.cache_dir = "/tmp/pnl_cache"
        self.font_dir = "/tmp/pnl_fonts"
        os.makedirs(self.cache_dir, exist_ok=True)
        os.makedirs(self.font_dir, exist_ok=True)
        
        self.colors = {
            'bg_dark': (10, 10, 15, 255),
            'red_glow': (255, 40, 40),
            'orange': (255, 165, 0),
            'white': (255, 255, 255),
            'gray': (180, 180, 180),
            'dark_overlay': (0, 0, 0, 180)
        }
        
        # Download exact fonts needed
        self.font_bold = self._get_font_path("Montserrat-Bold.ttf", "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Bold.ttf")
        self.font_extra_bold = self._get_font_path("Montserrat-ExtraBold.ttf", "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-ExtraBold.ttf")
        self.font_regular = self._get_font_path("Montserrat-Regular.ttf", "https://github.com/JulietaUla/Montserrat/raw/master/fonts/ttf/Montserrat-Regular.ttf")

    def _get_font_path(self, filename: str, url: str) -> str:
        path = os.path.join(self.font_dir, filename)
        if not os.path.exists(path):
            try:
                r = requests.get(url, timeout=10)
                r.raise_for_status()
                with open(path, 'wb') as f:
                    f.write(r.content)
            except Exception as e:
                print(f"Failed to download font {filename}: {e}")
                return None
        return path

    def get_font(self, size: int, bold: bool = True, extra_bold: bool = False) -> ImageFont.FreeTypeFont:
        if extra_bold and self.font_extra_bold:
            return ImageFont.truetype(self.font_extra_bold, size)
        elif bold and self.font_bold:
            return ImageFont.truetype(self.font_bold, size)
        elif self.font_regular:
            return ImageFont.truetype(self.font_regular, size)
        return ImageFont.load_default()

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
        except Exception as e:
            print(f"Failed to download {url}: {e}")
            return None

    def create_background(self, bg_image_url: Optional[str], dark_transparent: bool) -> Image.Image:
        if bg_image_url:
            bg = self.download_image(bg_image_url)
            if bg:
                # Resize and crop to fill
                bg = ImageOps.fit(bg, (self.width, self.height), Image.Resampling.LANCZOS)
                if dark_transparent:
                    overlay = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 180))
                    bg = Image.alpha_composite(bg, overlay)
                return bg
        
        # Fallback dark background
        img = Image.new('RGBA', (self.width, self.height), self.colors['bg_dark'])
        return img

    def crop_to_circle(self, img: Image.Image, size: int) -> Image.Image:
        img = img.resize((size, size), Image.Resampling.LANCZOS)
        mask = Image.new('L', (size, size), 0)
        ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
        output = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        output.paste(img, (0, 0), mask)
        return output

    def draw_text_with_shadow(self, img: Image.Image, pos: Tuple[int, int], text: str, 
                              font: ImageFont.FreeTypeFont, fill_color: Tuple, 
                              shadow_color: Tuple = (0, 0, 0), shadow_offset: Tuple[int, int] = (4, 4),
                              shadow_blur: int = 5):
        """Draws text with a soft drop shadow using Gaussian Blur (looks much better)"""
        # Create shadow layer
        shadow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        shadow_draw = ImageDraw.Draw(shadow_layer)
        shadow_draw.text((pos[0] + shadow_offset[0], pos[1] + shadow_offset[1]), text, font=font, fill=shadow_color)
        shadow_layer = shadow_layer.filter(ImageFilter.GaussianBlur(shadow_blur))
        
        # Composite shadow and text
        img.alpha_composite(shadow_layer)
        draw = ImageDraw.Draw(img)
        draw.text(pos, text, font=font, fill=fill_color)
        return img

    def draw_glow_text(self, img: Image.Image, pos: Tuple[int, int], text: str, 
                       font: ImageFont.FreeTypeFont, text_color: Tuple, glow_color: Tuple):
        """Creates a heavy neon glow behind the text"""
        # 1. Create glow layer
        glow_layer = Image.new('RGBA', img.size, (0, 0, 0, 0))
        glow_draw = ImageDraw.Draw(glow_layer)
        glow_draw.text(pos, text, font=font, fill=glow_color)
        
        # 2. Blur it heavily
        glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(15))
        
        # 3. Paste glow twice for intensity
        img.alpha_composite(glow_layer)
        img.alpha_composite(glow_layer)
        
        # 4. Draw the solid text on top
        draw = ImageDraw.Draw(img)
        draw.text(pos, text, font=font, fill=text_color)
        return img

    def generate_card(self,
                     name: str, multiplier: str, initial_market_cap: str, 
                     time_str: str, author_username: str,
                     blockchain_logo_url: Optional[str] = None, 
                     custom_logo_url: Optional[str] = None, 
                     background_image_url: Optional[str] = None,
                     dark_transparent: bool = True) -> BytesIO:
        
        # 1. Base Background
        img = self.create_background(background_image_url, dark_transparent)
        
        # Add faint red glow to the left side
        glow = Image.new('RGBA', img.size, (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([-200, 100, 500, 800], fill=(255, 0, 0, 60))
        glow = glow.filter(ImageFilter.GaussianBlur(100))
        img.alpha_composite(glow)
        
        draw = ImageDraw.Draw(img)

        # Layout constants
        right_margin = 80
        left_margin = 80
        center_y = self.height // 2

        # 2. Custom Logo (Left Side)
        if custom_logo_url:
            logo = self.download_image(custom_logo_url)
            if logo:
                logo_size = 220
                logo = self.crop_to_circle(logo, logo_size)
                logo_x, logo_y = 100, center_y - (logo_size // 2)
                
                # Red Glow behind logo
                glow_layer = Image.new('RGBA', img.size, (0,0,0,0))
                ImageDraw.Draw(glow_layer).ellipse([logo_x-20, logo_y-20, logo_x+logo_size+20, logo_y+logo_size+20], fill=(255, 30, 30, 180))
                glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(30))
                img.alpha_composite(glow_layer)
                
                # Paste Logo
                img.alpha_composite(logo, (logo_x, logo_y))

        # 3. Blockchain Logo (Top Center)
        if blockchain_logo_url:
            chain_logo = self.download_image(blockchain_logo_url)
            if chain_logo:
                chain_size = 50
                chain_logo = self.crop_to_circle(chain_logo, chain_size)
                chain_x = (self.width - chain_size) // 2
                img.alpha_composite(chain_logo, (chain_x, 40))

        # 4. Text Fonts
        font_name = self.get_font(85, extra_bold=True)
        font_mult = self.get_font(160, extra_bold=True)
        font_info = self.get_font(36, bold=True)
        font_author = self.get_font(48, extra_bold=True)

        # 5. Token Name (FLOAT) - Top Right
        name_text = name.upper()
        name_bbox = draw.textbbox((0, 0), name_text, font=font_name)
        name_x = self.width - right_margin - (name_bbox[2] - name_bbox[0])
        img = self.draw_text_with_shadow(img, (name_x, 80), name_text, font_name, self.colors['white'], shadow_blur=8)

        # 6. Multiplier (104x) - Center Right
        mult_text = multiplier
        mult_bbox = draw.textbbox((0, 0), mult_text, font=font_mult)
        mult_x = self.width - right_margin - (mult_bbox[2] - mult_bbox[0])
        mult_y = 210
        # Orange text with intense red/orange glow
        img = self.draw_glow_text(img, (mult_x, mult_y), mult_text, font_mult, (255, 170, 60), (255, 40, 0, 200))
        # Add a dark shadow under it for depth
        img = self.draw_text_with_shadow(img, (mult_x, mult_y), mult_text, font_mult, (255, 170, 60), (0,0,0,255), (6, 8), 4)

        # 7. Info (Called at...) - Below Multiplier
        info_text = f"Called at {initial_market_cap} | {time_str}"
        info_bbox = draw.textbbox((0, 0), info_text, font=font_info)
        info_x = self.width - right_margin - (info_bbox[2] - info_bbox[0])
        info_y = 410
        img = self.draw_text_with_shadow(img, (info_x, info_y), info_text, font_info, self.colors['white'], shadow_blur=5)

        # 8. Author Username - Bottom Right
        author_text = author_username.upper()
        author_bbox = draw.textbbox((0, 0), author_text, font=font_author)
        author_x = self.width - right_margin - (author_bbox[2] - author_bbox[0])
        author_y = 540
        
        # Small circle next to author
        circle_size = 24
        circle_x = author_x - 45
        circle_y = author_y + 12
        draw.ellipse([circle_x, circle_y, circle_x+circle_size, circle_y+circle_size], outline=self.colors['white'], width=3)
        
        img = self.draw_text_with_shadow(img, (author_x, author_y), author_text, font_author, self.colors['white'], shadow_blur=6)

        # 9. Rounded Corners Border
        mask = Image.new('L', (self.width, self.height), 0)
        ImageDraw.Draw(mask).rounded_rectangle((0, 0, self.width, self.height), radius=30, fill=255)
        final_img = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        final_img.paste(img, (0, 0), mask)

        # Save
        img_io = BytesIO()
        final_img.convert('RGB').save(img_io, 'PNG', quality=95, optimize=True)
        img_io.seek(0)
        return img_io

# Singleton
generator = PNLCardGenerator()