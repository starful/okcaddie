import os
from PIL import Image

# ==========================================
# ⚙️ 설정 (Configuration)
# ==========================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
IMAGES_DIR = os.path.join(BASE_DIR, 'app', 'static', 'images')

EXCLUDE_FILES =[
    'logo.png', 
    'logo.svg', 
    'favicons.ico', 
    'onsen_marker.png',
    'og_image.png',
    'default.png'
]

# 💡 압축 강도 강화 (가로 800px, 품질 75면 화질 저하 없이 용량만 1/10 수준으로 깎입니다)
MAX_WIDTH = 800  
QUALITY = 75     

def get_size_kb(filepath):
    """파일 용량을 KB 단위로 반환합니다."""
    return os.path.getsize(filepath) / 1024

def optimize_images():
    print(f"📸 이미지 최적화 시작... 폴더: {IMAGES_DIR}")
    print("-" * 50)
    
    if not os.path.exists(IMAGES_DIR):
        print("❌ 이미지 폴더를 찾을 수 없습니다.")
        return

    success_count = 0
    
    for filename in os.listdir(IMAGES_DIR):
        if filename in EXCLUDE_FILES:
            print(f"⏭️ 건너뜀 (보호된 파일): {filename}")
            continue
            
        ext = os.path.splitext(filename)[1].lower()
        if ext not in['.jpg', '.jpeg', '.png', '.webp']:
            continue

        filepath = os.path.join(IMAGES_DIR, filename)
        original_size = get_size_kb(filepath)
        
        try:
            # 1. 파일을 메모리에 올린 뒤 원본 파일은 바로 닫아버립니다. (파일 잠금 해결!)
            with Image.open(filepath) as img:
                rgb_img = img.convert("RGB")
                
                # 2. 크기 조절
                if rgb_img.width > MAX_WIDTH:
                    ratio = MAX_WIDTH / rgb_img.width
                    new_height = int(rgb_img.height * ratio)
                    rgb_img = rgb_img.resize((MAX_WIDTH, new_height), Image.Resampling.LANCZOS)
            
            # 3. 파일 닫힌 상태에서 덮어쓰기 저장 진행
            new_filename = os.path.splitext(filename)[0] + '.jpg'
            new_filepath = os.path.join(IMAGES_DIR, new_filename)
            
            rgb_img.save(new_filepath, 'JPEG', quality=QUALITY, optimize=True)
            
            # 4. 기존 파일이 png, jpeg 등이었다면 원본 삭제
            if filename != new_filename:
                os.remove(filepath)
            
            new_size = get_size_kb(new_filepath)
            
            # 5. 용량 감소 결과 출력
            print(f"✅ 완료: {filename} ({original_size:.1f}KB ➡️ {new_size:.1f}KB)")
            success_count += 1
            
        except Exception as e:
            print(f"❌ 에러 발생 ({filename}): {e}")

    print("-" * 50)
    print(f"🎉 총 {success_count}개의 이미지 최적화가 완료되었습니다!")

if __name__ == '__main__':
    optimize_images()