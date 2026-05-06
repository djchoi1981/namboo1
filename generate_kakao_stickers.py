#!/usr/bin/env python3
"""
카카오톡 스타일 이모티콘 스티커 시트 생성기
사용법: python generate_kakao_stickers.py --photo 사진경로.jpg --api-key YOUR_OPENAI_KEY
"""

import os
import sys
import time
import base64
import json
import argparse
from io import BytesIO
from pathlib import Path

# PIL은 필수
try:
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageOps
except ImportError:
    print("❌ Pillow가 필요합니다: pip install Pillow")
    sys.exit(1)

# openai는 선택적 (없으면 데모 모드)
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# ====================================================================
# 이모티콘 16개 정의
# ====================================================================

EMOTICONS = [
    {
        "id": 0,
        "text": "안녕하세요!",
        "pose": "waving right hand up high cheerfully, big warm bright smile",
        "prop": "wave",
        "mini_emojis": ["✨", "👋"],
        "accent_color": (255, 180, 190),
    },
    {
        "id": 1,
        "text": "식사 챙기셨어요?",
        "pose": "holding a cute coffee tumbler with both hands, warm gentle caring smile",
        "prop": "coffee tumbler",
        "mini_emojis": ["☕", "♥"],
        "accent_color": (255, 213, 170),
    },
    {
        "id": 2,
        "text": "확인해볼게요",
        "pose": "holding a magnifying glass up to eye, examining documents with focused expression",
        "prop": "magnifying glass and papers",
        "mini_emojis": ["🔍", "📄"],
        "accent_color": (200, 220, 255),
    },
    {
        "id": 3,
        "text": "제가 챙길게요",
        "pose": "holding a checklist clipboard, raising one finger confidently with assured smile",
        "prop": "checklist clipboard",
        "mini_emojis": ["✅", "☝️"],
        "accent_color": (180, 240, 200),
    },
    {
        "id": 4,
        "text": "잠깐 시간 괜찮으세요?",
        "pose": "holding a small cute alarm clock, polite slightly apologetic expression",
        "prop": "alarm clock",
        "mini_emojis": ["⏰", "🙏"],
        "accent_color": (255, 240, 180),
    },
    {
        "id": 5,
        "text": "곧 연락드릴게요",
        "pose": "holding smartphone to ear as if calling, friendly speaking expression",
        "prop": "smartphone",
        "mini_emojis": ["📱", "💬"],
        "accent_color": (220, 200, 255),
    },
    {
        "id": 6,
        "text": "서류만 준비해주세요",
        "pose": "holding a neat stack of documents, guiding helpful instructive expression",
        "prop": "document stack",
        "mini_emojis": ["📋", "✨"],
        "accent_color": (255, 230, 200),
    },
    {
        "id": 7,
        "text": "접수 완료!",
        "pose": "thumbs up with other hand holding stamped document, big triumphant smile",
        "prop": "stamped document and thumbs up",
        "mini_emojis": ["👍", "🎉"],
        "accent_color": (255, 200, 220),
    },
    {
        "id": 8,
        "text": "처리 중이에요",
        "pose": "looking focused at tablet device with serious concentrated expression",
        "prop": "tablet",
        "mini_emojis": ["⚙️", "💻"],
        "accent_color": (200, 230, 255),
    },
    {
        "id": 9,
        "text": "좋은 소식이에요!",
        "pose": "both fists lightly raised in joy, excited beaming happy expression",
        "prop": "joy gesture",
        "mini_emojis": ["🌟", "💛"],
        "accent_color": (255, 245, 170),
    },
    {
        "id": 10,
        "text": "감사드립니다",
        "pose": "both hands pressed together in grateful bow, humble grateful expression",
        "prop": "prayer hands gesture",
        "mini_emojis": ["🙏", "💙"],
        "accent_color": (200, 240, 230),
    },
    {
        "id": 11,
        "text": "생일 축하드려요!",
        "pose": "holding a cute birthday cake with candles, celebratory joyful smile",
        "prop": "birthday cake",
        "mini_emojis": ["🎂", "🎊"],
        "accent_color": (255, 210, 230),
    },
    {
        "id": 12,
        "text": "오늘도 힘내세요",
        "pose": "fist lightly raised in cheer, energetic encouraging warm expression",
        "prop": "cheer fist",
        "mini_emojis": ["💪", "⭐"],
        "accent_color": (255, 220, 180),
    },
    {
        "id": 13,
        "text": "빠른 회복 바랍니다",
        "pose": "holding heart shape and small flower bouquet, warm comforting soft smile",
        "prop": "heart and flowers",
        "mini_emojis": ["💗", "🌸"],
        "accent_color": (255, 220, 230),
    },
    {
        "id": 14,
        "text": "편안한 주말 되세요",
        "pose": "holding a cozy mug with both hands, relaxed contented peaceful smile",
        "prop": "cozy mug",
        "mini_emojis": ["☕", "🌙"],
        "accent_color": (220, 210, 250),
    },
    {
        "id": 15,
        "text": "축하드립니다!",
        "pose": "clapping hands enthusiastically, radiant overjoyed celebratory expression",
        "prop": "clapping gesture",
        "mini_emojis": ["👏", "🎊"],
        "accent_color": (255, 215, 170),
    },
]

# ====================================================================
# 스타일 상수
# ====================================================================

SHEET_SIZE = 2400                # 전체 시트 크기 (정사각형)
GRID_COLS = 4
GRID_ROWS = 4
PADDING = 30                     # 시트 바깥 여백
CELL_GAP = 20                    # 칸 간격
CELL_SIZE = (SHEET_SIZE - PADDING * 2 - CELL_GAP * (GRID_COLS - 1)) // GRID_COLS

SHEET_BG = (252, 248, 242)       # 연한 크림색 배경
STICKER_BORDER_COLOR = (255, 255, 255)
STICKER_BORDER_WIDTH = 12
STICKER_SHADOW_COLOR = (220, 210, 200, 80)

# 텍스트 스타일
TEXT_FILL = (255, 252, 245)      # 밝은 내부색
TEXT_STROKE = (60, 35, 20)       # 짙은 갈색 테두리
TEXT_STROKE_WIDTH = 4

# 캐릭터 프롬프트 기본 설명 (OpenAI용)
CHARACTER_BASE = (
    "a friendly Korean male insurance agent character, mid-40s, "
    "wearing a navy suit jacket and light beige dress shirt, "
    "short neat black hair with slight graying at temples, "
    "warm kind face with natural smile lines, "
    "kakao emoticon sticker style, "
    "cute chibi-like but realistic proportions, "
    "clean white sticker outline border, "
    "soft pastel colors, white background, "
    "transparent-background sticker illustration style"
)

# ====================================================================
# 유틸리티
# ====================================================================

def encode_image(image_path: str) -> str:
    """이미지를 base64로 인코딩"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def analyze_face(client: "OpenAI", photo_path: str) -> str:
    """GPT-4o Vision으로 인물 특징 분석"""
    print("🔍 인물 특징 분석 중...")
    b64 = encode_image(photo_path)
    ext = Path(photo_path).suffix.lower().lstrip(".")
    mime = "image/jpeg" if ext in ("jpg", "jpeg") else f"image/{ext}"

    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{mime};base64,{b64}"},
                    },
                    {
                        "type": "text",
                        "text": (
                            "Describe this person's distinctive facial features in 3-4 sentences "
                            "for use in a cartoon character illustration prompt. "
                            "Include: face shape, eye shape/size, nose shape, lip shape, "
                            "hair style/color, any notable features. "
                            "Be specific and concise. Reply in English."
                        ),
                    },
                ],
            }
        ],
        max_tokens=200,
    )
    desc = resp.choices[0].message.content.strip()
    print(f"   ✅ 분석 완료: {desc[:80]}...")
    return desc


def generate_emoticon_image(
    client: "OpenAI",
    emoticon: dict,
    character_desc: str,
    size: int = 512,
) -> Image.Image:
    """DALL-E 3로 이모티콘 이미지 생성"""
    prompt = (
        f"A single kawaii kakao-talk style emoticon sticker of {CHARACTER_BASE}. "
        f"Character appearance: {character_desc}. "
        f"The character is {emoticon['pose']}. "
        f"Props: {emoticon['prop']}. "
        f"Style: cute chibi proportions, large expressive eyes, "
        f"white sticker outline border around the character, "
        f"soft cel-shading, pastel palette, "
        f"white or very light background, "
        f"no text, no words, centered composition, "
        f"full body or 3/4 body visible. "
        f"KakaoTalk Friends style illustration."
    )

    resp = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
    )
    url = resp.data[0].url
    img_data = __import__("urllib.request", fromlist=["urlretrieve"])
    import urllib.request
    with urllib.request.urlopen(url) as r:
        raw = r.read()
    img = Image.open(BytesIO(raw)).convert("RGBA")
    img = img.resize((size, size), Image.LANCZOS)
    return img


# ====================================================================
# 데모 이미지 생성 (AI 없이 미리보기용)
# ====================================================================

def make_demo_character(emoticon: dict, size: int) -> Image.Image:
    """PIL만으로 귀여운 캐릭터 플레이스홀더 생성"""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    cx, cy = size // 2, size // 2
    r_head = int(size * 0.28)
    r_body = int(size * 0.20)

    # 그림자
    shadow_offset = int(size * 0.03)
    draw.ellipse(
        [cx - r_head + shadow_offset, cy - r_head // 2 + shadow_offset,
         cx + r_head + shadow_offset, cy + r_head // 2 + shadow_offset],
        fill=(200, 195, 190, 60),
    )

    # 몸 (네이비 수트)
    body_top = cy + int(r_head * 0.55)
    body_bottom = cy + int(r_head * 1.65)
    draw.ellipse(
        [cx - r_body, body_top, cx + r_body, body_bottom],
        fill=(35, 55, 100),
    )
    # 셔츠
    shirt_w = int(r_body * 0.5)
    draw.rectangle(
        [cx - shirt_w, body_top + 4, cx + shirt_w, body_top + int(r_body * 0.8)],
        fill=(240, 230, 210),
    )

    # 머리
    draw.ellipse(
        [cx - r_head, cy - r_head, cx + r_head, cy + r_head // 2 + int(r_head * 0.1)],
        fill=(245, 210, 175),
    )

    # 머리카락
    hair_y = cy - r_head
    draw.ellipse(
        [cx - r_head, hair_y, cx + r_head, cy - int(r_head * 0.2)],
        fill=(50, 35, 25),
    )
    # 앞머리
    draw.ellipse(
        [cx - r_head + int(r_head * 0.1), cy - r_head + int(r_head * 0.3),
         cx + r_head - int(r_head * 0.1), cy - int(r_head * 0.15)],
        fill=(60, 42, 30),
    )

    # 귀
    ear_r = int(r_head * 0.18)
    ear_y = cy - int(r_head * 0.1)
    for ear_x in [cx - r_head, cx + r_head]:
        draw.ellipse(
            [ear_x - ear_r, ear_y - ear_r, ear_x + ear_r, ear_y + ear_r],
            fill=(235, 200, 165),
        )

    # 눈썹
    brow_y = cy - int(r_head * 0.18)
    brow_w = int(r_head * 0.22)
    for ex in [cx - int(r_head * 0.35), cx + int(r_head * 0.35)]:
        draw.arc(
            [ex - brow_w, brow_y - int(r_head * 0.12),
             ex + brow_w, brow_y + int(r_head * 0.05)],
            start=200, end=340,
            fill=(50, 35, 20), width=max(2, size // 80),
        )

    # 눈 (큰 귀여운 눈)
    eye_y = cy - int(r_head * 0.02)
    eye_r = int(r_head * 0.18)
    for ex in [cx - int(r_head * 0.35), cx + int(r_head * 0.35)]:
        draw.ellipse([ex - eye_r, eye_y - eye_r, ex + eye_r, eye_y + eye_r],
                     fill=(40, 30, 20))
        draw.ellipse([ex - int(eye_r * 0.45), eye_y - int(eye_r * 0.45),
                      ex + int(eye_r * 0.45), eye_y + int(eye_r * 0.45)],
                     fill=(255, 255, 255))
        # 하이라이트
        draw.ellipse([ex + int(eye_r * 0.1), eye_y - int(eye_r * 0.55),
                      ex + int(eye_r * 0.45), eye_y - int(eye_r * 0.2)],
                     fill=(255, 255, 255))

    # 코
    nose_y = cy + int(r_head * 0.18)
    draw.ellipse(
        [cx - int(r_head * 0.06), nose_y - int(r_head * 0.04),
         cx + int(r_head * 0.06), nose_y + int(r_head * 0.04)],
        fill=(200, 165, 140),
    )

    # 표정별 입
    mouth_y = cy + int(r_head * 0.33)
    mouth_w = int(r_head * 0.32)
    emote_id = emoticon["id"]

    if emote_id in [0, 3, 7, 9, 11, 12, 15]:
        # 활짝 웃는 입
        draw.arc(
            [cx - mouth_w, mouth_y - mouth_w // 2,
             cx + mouth_w, mouth_y + mouth_w // 2],
            start=0, end=180,
            fill=(200, 100, 100), width=max(2, size // 70),
        )
        # 치아
        draw.arc(
            [cx - mouth_w + 4, mouth_y - mouth_w // 2 + 4,
             cx + mouth_w - 4, mouth_y + mouth_w // 2 - 4],
            start=20, end=160,
            fill=(255, 255, 255), width=max(2, size // 80),
        )
    elif emote_id in [4, 6, 10]:
        # 공손한 미소
        draw.arc(
            [cx - mouth_w // 2, mouth_y - mouth_w // 4,
             cx + mouth_w // 2, mouth_y + mouth_w // 4],
            start=10, end=170,
            fill=(190, 110, 100), width=max(2, size // 80),
        )
    elif emote_id in [8]:
        # 집중한 표정 (일자 입)
        draw.line(
            [cx - mouth_w // 2, mouth_y, cx + mouth_w // 2, mouth_y],
            fill=(160, 100, 90), width=max(2, size // 90),
        )
    else:
        # 부드러운 미소
        draw.arc(
            [cx - mouth_w * 2 // 3, mouth_y - mouth_w // 3,
             cx + mouth_w * 2 // 3, mouth_y + mouth_w // 3],
            start=15, end=165,
            fill=(195, 115, 105), width=max(2, size // 80),
        )

    # 볼 홍조
    blush_r = int(r_head * 0.13)
    blush_y = cy + int(r_head * 0.22)
    for bx in [cx - int(r_head * 0.5), cx + int(r_head * 0.5)]:
        blush_img = Image.new("RGBA", (blush_r * 2, blush_r * 2), (0, 0, 0, 0))
        blush_draw = ImageDraw.Draw(blush_img)
        blush_draw.ellipse([0, 0, blush_r * 2 - 1, blush_r * 2 - 1],
                            fill=(255, 180, 170, 120))
        img.paste(blush_img, (bx - blush_r, blush_y - blush_r), blush_img)

    # 포즈별 소품 간단 표현
    _draw_prop(draw, emoticon["id"], cx, cy, r_head, r_body, size)

    return img


def _draw_prop(draw: ImageDraw.Draw, emote_id: int, cx: int, cy: int,
               r_head: int, r_body: int, size: int):
    """포즈별 간단한 소품 표현"""
    arm_y = cy + int(r_head * 0.75)
    arm_len = int(r_body * 1.1)
    arm_w = max(3, size // 55)

    if emote_id == 0:  # 손 흔들기
        draw.line([cx + r_body, arm_y, cx + r_body + arm_len, arm_y - arm_len],
                  fill=(245, 210, 175), width=arm_w)
        draw.ellipse(
            [cx + r_body + arm_len - arm_w * 2, arm_y - arm_len - arm_w * 2,
             cx + r_body + arm_len + arm_w * 2, arm_y - arm_len + arm_w * 2],
            fill=(245, 210, 175),
        )

    elif emote_id == 1:  # 커피컵
        cup_x = cx + int(r_body * 0.8)
        cup_y = arm_y - int(r_head * 0.1)
        draw.rounded_rectangle(
            [cup_x - 12, cup_y - 20, cup_x + 12, cup_y + 20],
            radius=4, fill=(240, 120, 70), outline=(200, 80, 40), width=2,
        )
        draw.arc([cup_x + 8, cup_y - 5, cup_x + 18, cup_y + 10],
                 start=270, end=90, fill=(200, 80, 40), width=2)

    elif emote_id == 2:  # 돋보기
        mg_x = cx + int(r_body * 0.9)
        mg_y = arm_y - int(r_head * 0.15)
        mg_r = int(size * 0.055)
        draw.ellipse([mg_x - mg_r, mg_y - mg_r, mg_x + mg_r, mg_y + mg_r],
                     outline=(180, 160, 100), width=4)
        draw.line([mg_x + int(mg_r * 0.7), mg_y + int(mg_r * 0.7),
                   mg_x + int(mg_r * 1.5), mg_y + int(mg_r * 1.5)],
                  fill=(140, 120, 70), width=4)

    elif emote_id == 3:  # 체크리스트
        cl_x = cx + int(r_body * 0.75)
        cl_y = arm_y - int(r_head * 0.3)
        draw.rounded_rectangle(
            [cl_x - 14, cl_y - 22, cl_x + 14, cl_y + 22],
            radius=3, fill=(255, 255, 240), outline=(180, 180, 160), width=2,
        )
        for iy, checked in enumerate([True, True, False]):
            ly = cl_y - 12 + iy * 11
            draw.line([cl_x - 8, ly, cl_x + 8, ly], fill=(200, 200, 180), width=1)
            if checked:
                draw.text((cl_x - 10, ly - 6), "✓", fill=(80, 180, 80))

    elif emote_id == 5:  # 스마트폰
        ph_x = cx + int(r_body * 0.9)
        ph_y = arm_y - int(r_head * 0.2)
        draw.rounded_rectangle(
            [ph_x - 10, ph_y - 18, ph_x + 10, ph_y + 18],
            radius=5, fill=(40, 40, 50), outline=(80, 80, 90), width=2,
        )
        draw.rectangle([ph_x - 7, ph_y - 14, ph_x + 7, ph_y + 12],
                       fill=(100, 180, 255))

    elif emote_id == 7:  # 엄지척
        draw.line([cx + r_body, arm_y, cx + r_body + int(arm_len * 0.5), arm_y],
                  fill=(245, 210, 175), width=arm_w)
        thumb_x = cx + r_body + int(arm_len * 0.5)
        draw.rounded_rectangle(
            [thumb_x, arm_y - 16, thumb_x + 14, arm_y + 6],
            radius=6, fill=(245, 210, 175), outline=(220, 180, 150), width=1,
        )

    elif emote_id == 11:  # 케이크
        ck_x = cx + int(r_body * 0.65)
        ck_y = arm_y + int(r_head * 0.1)
        draw.rounded_rectangle(
            [ck_x - 20, ck_y - 15, ck_x + 20, ck_y + 15],
            radius=4, fill=(255, 230, 220), outline=(240, 180, 160), width=2,
        )
        draw.rectangle([ck_x - 16, ck_y - 15, ck_x + 16, ck_y - 10],
                       fill=(255, 200, 200))
        for ci in [-8, 0, 8]:
            draw.line([ck_x + ci, ck_y - 22, ck_x + ci, ck_y - 17],
                      fill=(255, 220, 100), width=2)
            draw.ellipse([ck_x + ci - 2, ck_y - 26, ck_x + ci + 2, ck_y - 22],
                         fill=(255, 150, 50))

    elif emote_id == 13:  # 꽃다발
        fl_x = cx + int(r_body * 0.75)
        fl_y = arm_y - int(r_head * 0.1)
        for angle_offset, color in [
            (-15, (255, 180, 200)), (0, (255, 150, 180)), (15, (255, 200, 220))
        ]:
            import math
            rad = math.radians(angle_offset - 90)
            fx = fl_x + int(25 * math.cos(rad))
            fy = fl_y + int(25 * math.sin(rad))
            draw.ellipse([fx - 8, fy - 8, fx + 8, fy + 8], fill=color)
        draw.line([fl_x, fl_y, fl_x, fl_y + 20], fill=(100, 170, 100), width=3)

    elif emote_id == 14:  # 머그컵
        mg_x = cx + int(r_body * 0.75)
        mg_y = arm_y + int(r_head * 0.05)
        draw.rounded_rectangle(
            [mg_x - 15, mg_y - 16, mg_x + 15, mg_y + 16],
            radius=5, fill=(200, 160, 130), outline=(160, 120, 90), width=2,
        )
        draw.arc([mg_x + 12, mg_y - 6, mg_x + 24, mg_y + 8],
                 start=270, end=90, fill=(160, 120, 90), width=3)

    elif emote_id == 15:  # 박수
        # 양손 표현
        for side, direction in [(-1, -1), (1, 1)]:
            hx = cx + side * int(r_body * 0.85)
            hy = arm_y - int(r_head * 0.1)
            hand_r = int(size * 0.04)
            draw.ellipse([hx - hand_r, hy - hand_r, hx + hand_r, hy + hand_r],
                         fill=(245, 210, 175))


# ====================================================================
# 미니 이모지 그리기
# ====================================================================

def draw_mini_emojis(
    draw: ImageDraw.Draw,
    emojis: list,
    cx: int, cy: int,
    cell_size: int,
    accent_color: tuple,
):
    """칸 모서리에 작은 장식 이모지 배치"""
    margin = int(cell_size * 0.06)
    emoji_size = max(20, int(cell_size * 0.08))
    positions = [
        (cx - cell_size // 2 + margin, cy - cell_size // 2 + margin),
        (cx + cell_size // 2 - margin - emoji_size, cy - cell_size // 2 + margin),
    ]

    try:
        # 시스템 이모지 폰트 시도
        emoji_font = _get_emoji_font(emoji_size)
    except Exception:
        emoji_font = None

    for i, (emoji_char, pos) in enumerate(zip(emojis, positions)):
        if emoji_font:
            try:
                draw.text(pos, emoji_char, font=emoji_font, embedded_color=True)
                continue
            except Exception:
                pass
        # 폰트 없으면 색깔 원으로 대체
        r = emoji_size // 2
        draw.ellipse(
            [pos[0], pos[1], pos[0] + emoji_size, pos[1] + emoji_size],
            fill=accent_color + (180,) if len(accent_color) == 3 else accent_color,
        )


def _get_emoji_font(size: int):
    """시스템에서 이모지 폰트를 찾아 반환"""
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
        "/System/Library/Fonts/Apple Color Emoji.ttc",
        "C:/Windows/Fonts/seguiemj.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    raise FileNotFoundError("No emoji font found")


# ====================================================================
# 텍스트 그리기
# ====================================================================

def _find_korean_font(size: int) -> ImageFont.FreeTypeFont | None:
    """한글 폰트 탐색"""
    candidates = [
        "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumGothicExtraBold.ttf",
        "/usr/share/fonts/truetype/nanum/NanumBarunGothicBold.ttf",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJKkr-Bold.otf",
        "/System/Library/Fonts/AppleSDGothicNeo.ttc",
        "C:/Windows/Fonts/malgunbd.ttf",
        "C:/Windows/Fonts/gulim.ttc",
    ]
    for path in candidates:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                continue
    # 폰트 못 찾으면 None
    return None


def draw_sticker_text(
    draw: ImageDraw.Draw,
    text: str,
    center_x: int,
    text_y: int,
    font_size: int,
):
    """스티커 스타일 텍스트: 짙은 테두리 + 밝은 내부색"""
    font = _find_korean_font(font_size)
    if font is None:
        font = ImageFont.load_default()

    # 텍스트 크기 측정
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    x = center_x - text_w // 2
    y = text_y

    stroke = TEXT_STROKE_WIDTH
    # 테두리 (8방향)
    for dx in range(-stroke, stroke + 1):
        for dy in range(-stroke, stroke + 1):
            if dx == 0 and dy == 0:
                continue
            draw.text((x + dx, y + dy), text, font=font, fill=TEXT_STROKE)
    # 본문
    draw.text((x, y), text, font=font, fill=TEXT_FILL)


# ====================================================================
# 스티커 카드 합성
# ====================================================================

def make_sticker_card(
    character_img: Image.Image,
    emoticon: dict,
    cell_size: int,
) -> Image.Image:
    """캐릭터 이미지 + 텍스트 + 테두리 → 하나의 스티커 카드"""
    card = Image.new("RGBA", (cell_size, cell_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)

    cx, cy = cell_size // 2, cell_size // 2
    radius = int(cell_size * 0.46)

    # ── 그림자 ──
    shadow = Image.new("RGBA", (cell_size, cell_size), (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    s_off = int(cell_size * 0.02)
    shadow_draw.ellipse(
        [cx - radius + s_off, cy - radius + s_off,
         cx + radius + s_off, cy + radius + s_off],
        fill=(210, 200, 195, 70),
    )
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=int(cell_size * 0.025)))
    card.paste(shadow, (0, 0), shadow)

    # ── 악센트 배경 원 ──
    accent = emoticon["accent_color"]
    bg_circle = Image.new("RGBA", (cell_size, cell_size), (0, 0, 0, 0))
    bg_draw = ImageDraw.Draw(bg_circle)
    bg_draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=accent + (40,),
    )
    card.paste(bg_circle, (0, 0), bg_circle)

    # ── 흰 테두리 스티커 원 ──
    border_w = STICKER_BORDER_WIDTH
    draw.ellipse(
        [cx - radius, cy - radius, cx + radius, cy + radius],
        fill=STICKER_BORDER_COLOR,
    )
    draw.ellipse(
        [cx - radius + border_w, cy - radius + border_w,
         cx + radius - border_w, cy + radius - border_w],
        fill=(252, 248, 242),
    )

    # ── 캐릭터 이미지 합성 ──
    char_size = int(radius * 2 - border_w * 2)
    char_resized = character_img.resize((char_size, char_size), Image.LANCZOS)

    # 원형 마스크로 클리핑
    mask = Image.new("L", (char_size, char_size), 0)
    mask_draw = ImageDraw.Draw(mask)
    mask_draw.ellipse([0, 0, char_size - 1, char_size - 1], fill=255)

    char_x = cx - char_size // 2
    char_y = cy - char_size // 2

    if char_resized.mode == "RGBA":
        card.paste(char_resized, (char_x, char_y), char_resized)
    else:
        card.paste(char_resized, (char_x, char_y), mask)

    # ── 텍스트 (머리 위에 살짝 걸치도록) ──
    font_size = max(18, int(cell_size * 0.085))
    # 텍스트 Y 위치: 원 상단에서 약간 아래 (머리카락에 겹치는 느낌)
    text_y = cy - radius + int(radius * 0.18)
    draw_sticker_text(draw, emoticon["text"], cx, text_y, font_size)

    # ── 미니 이모지 ──
    draw_mini_emojis(draw, emoticon["mini_emojis"], cx, cy, cell_size, accent)

    return card


# ====================================================================
# 스티커 시트 조립
# ====================================================================

def build_sticker_sheet(sticker_cards: list[Image.Image]) -> Image.Image:
    """16개 카드 → 4×4 시트"""
    sheet = Image.new("RGB", (SHEET_SIZE, SHEET_SIZE), SHEET_BG)

    for idx, card in enumerate(sticker_cards):
        row = idx // GRID_COLS
        col = idx % GRID_COLS

        x = PADDING + col * (CELL_SIZE + CELL_GAP)
        y = PADDING + row * (CELL_SIZE + CELL_GAP)

        # RGBA 카드를 흰 배경으로 합성
        bg = Image.new("RGB", (CELL_SIZE, CELL_SIZE), SHEET_BG)
        if card.mode == "RGBA":
            bg.paste(card, (0, 0), card)
        else:
            bg.paste(card, (0, 0))
        sheet.paste(bg, (x, y))

    return sheet


# ====================================================================
# 메인 워크플로
# ====================================================================

def run_demo_mode(output_path: str):
    """AI 없이 PIL만으로 데모 스티커 시트 생성"""
    print("🎨 데모 모드: PIL 기반 캐릭터로 스티커 시트를 생성합니다.")
    print(f"   (실제 사진 기반 생성은 --api-key 옵션으로 OpenAI 키를 입력하세요)\n")

    sticker_cards = []
    for i, emoticon in enumerate(EMOTICONS):
        print(f"   [{i+1:02d}/16] {emoticon['text']} 생성 중...")
        char_img = make_demo_character(emoticon, CELL_SIZE)
        card = make_sticker_card(char_img, emoticon, CELL_SIZE)
        sticker_cards.append(card)

    print("\n📐 스티커 시트 조립 중...")
    sheet = build_sticker_sheet(sticker_cards)
    sheet.save(output_path, "PNG", dpi=(300, 300))
    print(f"✅ 완료! 저장 위치: {output_path}")
    print(f"   시트 크기: {SHEET_SIZE}×{SHEET_SIZE}px  |  각 칸: {CELL_SIZE}×{CELL_SIZE}px")


def run_ai_mode(photo_path: str, api_key: str, output_path: str):
    """OpenAI API로 사진 기반 스티커 시트 생성"""
    client = OpenAI(api_key=api_key)

    # 1. 인물 특징 분석
    char_desc = analyze_face(client, photo_path)
    print()

    # 2. 16개 이모티콘 생성
    sticker_cards = []
    char_imgs_cache: dict[int, Image.Image] = {}

    for i, emoticon in enumerate(EMOTICONS):
        print(f"   [{i+1:02d}/16] {emoticon['text']} 생성 중...")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                char_img = generate_emoticon_image(client, emoticon, char_desc, CELL_SIZE)
                break
            except Exception as e:
                if attempt < max_retries - 1:
                    wait = 2 ** attempt
                    print(f"      ⚠️  오류 발생, {wait}초 후 재시도... ({e})")
                    time.sleep(wait)
                else:
                    print(f"      ❌ 생성 실패, 데모 이미지로 대체합니다.")
                    char_img = make_demo_character(emoticon, CELL_SIZE)

        card = make_sticker_card(char_img, emoticon, CELL_SIZE)
        sticker_cards.append(card)

        # API 속도 제한 방지
        if i < len(EMOTICONS) - 1:
            time.sleep(1.5)

    # 3. 시트 조립
    print("\n📐 스티커 시트 조립 중...")
    sheet = build_sticker_sheet(sticker_cards)
    sheet.save(output_path, "PNG", dpi=(300, 300))
    print(f"✅ 완료! 저장 위치: {output_path}")
    print(f"   시트 크기: {SHEET_SIZE}×{SHEET_SIZE}px  |  각 칸: {CELL_SIZE}×{CELL_SIZE}px")


# ====================================================================
# CLI 진입점
# ====================================================================

def main():
    parser = argparse.ArgumentParser(
        description="카카오톡 스타일 이모티콘 스티커 시트 생성기",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  # 데모 모드 (AI 없이 미리보기)
  python generate_kakao_stickers.py --demo

  # 사진 기반 생성 (OpenAI API 필요)
  python generate_kakao_stickers.py --photo 내사진.jpg --api-key sk-...

  # 출력 파일 지정
  python generate_kakao_stickers.py --photo 내사진.jpg --api-key sk-... --output 내스티커시트.png
        """,
    )
    parser.add_argument("--photo", type=str, help="입력 인물 사진 경로 (jpg/png)")
    parser.add_argument("--api-key", type=str, help="OpenAI API 키 (없으면 환경변수 OPENAI_API_KEY 사용)")
    parser.add_argument("--output", type=str, default="kakao_sticker_sheet.png", help="출력 파일명 (기본: kakao_sticker_sheet.png)")
    parser.add_argument("--demo", action="store_true", help="데모 모드: AI 없이 PIL 기반 캐릭터로 생성")
    args = parser.parse_args()

    print("=" * 60)
    print("  카카오톡 스타일 이모티콘 스티커 시트 생성기")
    print("=" * 60)

    # 데모 모드
    if args.demo or (not args.photo and not args.api_key):
        run_demo_mode(args.output)
        return

    # 사진 확인
    if args.photo and not os.path.exists(args.photo):
        print(f"❌ 사진 파일을 찾을 수 없습니다: {args.photo}")
        sys.exit(1)

    # API 키 확인
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        print("⚠️  OpenAI API 키가 없습니다. 데모 모드로 전환합니다.")
        run_demo_mode(args.output)
        return

    if not HAS_OPENAI:
        print("⚠️  openai 패키지가 없습니다. 데모 모드로 전환합니다.")
        print("   설치: pip install openai")
        run_demo_mode(args.output)
        return

    run_ai_mode(args.photo, api_key, args.output)


if __name__ == "__main__":
    main()
