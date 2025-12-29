import os
import sys
import shutil
import io
from PIL import Image

# ==========================================================
# [설정] 이 부분을 필요에 따라 수정하세요.
# ==========================================================
# 1. 원본 및 결과물 폴더
SOURCE_DIR = os.path.join('app', 'content', 'images')
OUTPUT_DIR = 'compressed_images'

# 2. 압축 기준 및 목표 용량 (단위: KB)
TARGET_THRESHOLD_KB = 100  # 이 용량을 초과하는 이미지만 압축합니다.
TARGET_SIZE_KB = 99        # 압축 후 목표 용량입니다.

# 3. 이미지 최대 가로 크기 및 품질 설정
MAX_WIDTH = 1200
START_QUALITY = 90  # 압축을 시작할 초기 품질 값
MIN_QUALITY = 40    # 이미지 품질 저하를 막기 위한 최소 품질 값
# ==========================================================

def compress_to_target_size(img, target_bytes):
    """
    이미지를 목표 파일 크기 미만이 될 때까지 품질을 낮추며 압축합니다.
    """
    buffer = io.BytesIO()
    
    # 품질을 5씩 낮추면서 목표 크기에 도달하는지 확인
    for quality in range(START_QUALITY, MIN_QUALITY - 1, -5):
        buffer.seek(0)
        buffer.truncate()
        img.save(buffer, 'webp', quality=quality, method=6)
        
        if buffer.tell() < target_bytes:
            print(f"    - ✅ Success! Target met with quality={quality}")
            return buffer
            
    # 최소 품질에서도 목표 크기에 도달하지 못했다면 마지막 결과라도 반환
    print(f"    - ⚠️ Warning: Target not met. Saved with lowest quality={MIN_QUALITY}")
    return buffer

def process_image(source_path, output_path):
    """
    이미지 크기에 따라 압축 또는 복사를 결정합니다.
    """
    try:
        original_size = os.path.getsize(source_path)
        
        # 1. 파일 크기가 기준보다 작으면 원본 복사
        if original_size < TARGET_THRESHOLD_KB * 1024:
            shutil.copy2(source_path, output_path)
            print(f"    - ⏩ Skipped (Already small): {original_size/1024:.1f} KB. Copied original.")
            return original_size, original_size

        # 2. 파일 크기가 기준보다 크면 압축 시도
        print(f"    -  compressing large file: {original_size/1024:.1f} KB...")
        with Image.open(source_path) as img:
            # 리사이징
            if img.width > MAX_WIDTH:
                ratio = MAX_WIDTH / float(img.width)
                new_height = int(float(img.height) * ratio)
                img = img.resize((MAX_WIDTH, new_height), Image.Resampling.LANCZOS)

            # RGBA -> RGB 변환
            if img.mode == 'RGBA':
                img = img.convert('RGB')
            
            # 목표 용량 압축 실행
            target_bytes = TARGET_SIZE_KB * 1024
            compressed_buffer = compress_to_target_size(img, target_bytes)

            # 결과 저장
            with open(output_path, 'wb') as f:
                f.write(compressed_buffer.getvalue())
            
            final_size = os.path.getsize(output_path)
            reduction = (original_size - final_size) / original_size * 100
            print(f"    - Result: {original_size/1024:.1f} KB -> {final_size/1024:.1f} KB (Saved: {reduction:.1f}%)")
            return original_size, final_size

    except Exception as e:
        print(f"    - ❌ Error processing {os.path.basename(source_path)}: {e}")
        return None, None

def main():
    if not os.path.exists(SOURCE_DIR):
        print(f"❌ Error: Source directory '{SOURCE_DIR}' not found.")
        sys.exit(1)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"✅ Created output directory: '{OUTPUT_DIR}'")
        
    print(f"\n🚀 Starting Target-Based Image Compression...")
    print(f"   - Source: '{SOURCE_DIR}'")
    print(f"   - Output: '{OUTPUT_DIR}'")
    print(f"   - Compress if > {TARGET_THRESHOLD_KB} KB, Target < {TARGET_SIZE_KB} KB\n")

    supported_formats = ('.jpg', '.jpeg', '.png', '.webp')
    
    total_original_size = 0
    total_final_size = 0
    processed_count = 0

    for filename in sorted(os.listdir(SOURCE_DIR)):
        if not filename.lower().endswith(supported_formats):
            continue

        source_path = os.path.join(SOURCE_DIR, filename)
        output_filename = os.path.splitext(filename)[0] + '.webp'
        output_path = os.path.join(OUTPUT_DIR, output_filename)
        
        print(f"[{processed_count + 1}] Processing '{filename}'...")
        
        original, final = process_image(source_path, output_path)
        
        if original is not None and final is not None:
            total_original_size += original
            total_final_size += final
            processed_count += 1
            
    if processed_count == 0:
        print("No images found to process.")
        return

    total_reduction = (total_original_size - total_final_size) / total_original_size * 100
    
    print("\n" + "="*50)
    print("✨ Compression Complete!")
    print(f"   - Processed images: {processed_count}")
    print(f"   - Total original size:  {total_original_size/1024/1024:.2f} MB")
    print(f"   - Total final size:     {total_final_size/1024/1024:.2f} MB")
    print(f"   - Total space saved:    {total_reduction:.1f}%")
    print("="*50)
    print(f"\n👉 Check the final results in the '{OUTPUT_DIR}' folder.")

if __name__ == '__main__':
    try:
        from PIL import Image
    except ImportError:
        print("❌ Error: Pillow library not found.")
        print("Please install it by running: pip install Pillow")
        sys.exit(1)
        
    main()