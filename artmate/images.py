"""이미지 검증·리사이즈·인코딩 (design.md §4, §8.3)."""
import base64
from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from artmate import config

ALLOWED_FORMATS = {"JPEG", "PNG"}


def load_image(file) -> Image.Image:
    """업로드 파일을 검증하고 긴 변을 IMAGE_MAX_SIDE 이하로 줄인 RGB 이미지를 반환한다.
    형식·크기가 맞지 않으면 학생용 안내 문구로 ValueError를 낸다."""
    if len(file.getvalue()) > config.MAX_IMAGE_MB * 1024 * 1024:
        raise ValueError(f"{config.MAX_IMAGE_MB}MB 이하의 이미지만 올릴 수 있어요.")
    try:
        img = Image.open(file)
    except UnidentifiedImageError:
        raise ValueError("JPG 또는 PNG 이미지만 올릴 수 있어요.") from None
    # 확장자가 아니라 실제 파일 형식으로 판단
    if img.format not in ALLOWED_FORMATS:
        raise ValueError("JPG 또는 PNG 이미지만 올릴 수 있어요.")

    img = ImageOps.exif_transpose(img)  # 휴대폰 사진 회전 보정
    img.thumbnail((config.IMAGE_MAX_SIDE, config.IMAGE_MAX_SIDE))
    # 투명 배경은 흰색으로 채워 JPEG로 보낼 수 있게 한다
    rgba = img.convert("RGBA")
    rgb = Image.new("RGB", rgba.size, "white")
    rgb.paste(rgba, mask=rgba)
    return rgb


def to_data_url(img: Image.Image) -> str:
    """모델 전송용 base64 데이터 URL. 다시 인코딩하므로 위치 정보 등 EXIF는 빠진다."""
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
