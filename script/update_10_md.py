import os
import random
import frontmatter

# ==========================================================
# [수정] 스크립트 위치에 상관없이 경로를 올바르게 설정합니다.
# ==========================================================
# 현재 스크립트 파일이 있는 디렉토리 (jinjaMap/script/)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# 프로젝트 최상위 디렉토리 (jinjaMap/)
BASE_DIR = os.path.dirname(SCRIPT_DIR)

# 1. 한 번에 수정할 파일 개수
FILES_TO_UPDATE_COUNT = 10

# 2. 마크다운 파일이 있는 폴더 경로 (BASE_DIR 기준으로 재설정)
CONTENT_DIR = os.path.join(BASE_DIR, 'app', 'content')
# ==========================================================

# 3. 변경할 소제목(헤더) 목록
TITLE_VARIATIONS = {
    "🙏 Introduction: Deities & History": [
        "🙏 A Divine Welcome: Deities and Legends",
        "📜 The Story Begins: Gods and History",
        "⛩️ Gateway to the Gods: An Introduction",
        "✨ The Heart of the Shrine: Deities & Origins"
    ],
    "⛩️ Exploring the Grounds": [
        "⛩️ A Walk Through Sacred Grounds",
        "🌳 Highlights of the Shrine Precinct",
        "🌿 What to See: A Tour of the Grounds",
        "🚶‍♂️ Discovering the Shrine's Treasures"
    ],
    "📜 Goshuin & Omamori": [
        "📜 Sacred Souvenirs: Goshuin & Omamori",
        "🧧 Blessings to Take Home: Charms and Stamps",
        "🔖 Unique Goshuin and Lucky Charms",
        "✨ Special Amulets and Shrine Stamps"
    ],
    "🗺️ Access & Info": [
        "🗺️ Plan Your Visit: Access & Information",
        "📍 Visitor's Guide: How to Get There",
        "🚗 Access Details and Practical Info",
        "🧭 Getting Here: Location and Hours"
    ],
    "✨ Conclusion": [
        "✨ Final Thoughts: A Lasting Impression",
        "🌟 A Memorable Visit: Conclusion",
        "🙏 Why You Should Visit: A Summary",
        "💫 Final Reflections on a Sacred Place"
    ]
}


def get_all_shrine_data():
    """내부 링크 생성을 위해 모든 신사 정보를 미리 로드합니다."""
    all_shrines = []
    if not os.path.exists(CONTENT_DIR):
        return []
        
    for filename in os.listdir(CONTENT_DIR):
        if not filename.endswith('.md'):
            continue
        filepath = os.path.join(CONTENT_DIR, filename)
        try:
            post = frontmatter.load(filepath)
            region_tag = next((tag for tag in post.get('tags', []) if tag[0].isupper() and tag not in ["Japan", "Shrine", "Travel"]), None)
            
            all_shrines.append({
                'id': filename.replace('.md', ''),
                'title': post.get('title', ''),
                'category': post.get('categories', ['History'])[0],
                'region': region_tag
            })
        except Exception:
            pass
    return all_shrines

def update_file_content(filepath, all_shrines_data):
    print(f"🔄 Processing: {os.path.basename(filepath)}")
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
        
        content = post.content
        original_content = content
        
        # 1. 소제목 변경
        for original_title, variations in TITLE_VARIATIONS.items():
            if original_title in content:
                new_title = random.choice(variations)
                content = content.replace(original_title, new_title, 1)
                print(f"    - Title changed: '{original_title}' -> '{new_title}'")

        # 2. 내부 링크 섹션 추가
        if "Nearby Recommendations" not in content and "함께 둘러보기" not in content:
            current_id = os.path.basename(filepath).replace('.md', '')
            current_post_info = next((s for s in all_shrines_data if s['id'] == current_id), None)
            
            if current_post_info:
                same_cat_shrine = next((s for s in random.sample(all_shrines_data, len(all_shrines_data)) if s['category'] == current_post_info['category'] and s['id'] != current_id), None)
                same_region_shrine = next((s for s in random.sample(all_shrines_data, len(all_shrines_data)) if s['region'] and s['region'] == current_post_info['region'] and s['id'] != current_id), None)
                
                links_md = ""
                if same_cat_shrine:
                    links_md += f"- **For {same_cat_shrine['category']} Luck:** Discover [{same_cat_shrine['title']}](/shrine/{same_cat_shrine['id']}), another powerful spot for your wishes.\n"
                if same_region_shrine and same_region_shrine != same_cat_shrine:
                     links_md += f"- **While in {same_region_shrine['region']}:** Don't miss a visit to [{same_region_shrine['title']}](/shrine/{same_region_shrine['id']}) nearby.\n"

                if links_md:
                    recommendation_section = f"""
***
### 🗺️ Nearby Recommendations

If you enjoyed your visit, consider exploring these other sacred sites:

{links_md}
"""
                    insert_points = ["### ✨ Conclusion", "### 🗺️ Access & Info"]
                    inserted = False
                    for point in insert_points:
                        if point in content:
                            content = content.replace(point, recommendation_section + point, 1)
                            inserted = True
                            break
                    if not inserted: content += recommendation_section
                    print("    - Added internal links section.")

        if content != original_content:
            post.content = content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(frontmatter.dumps(post))
            print("    - ✅ File updated successfully.")
        else:
            print("    - No changes needed.")

    except Exception as e:
        print(f"    - ❌ Error processing file: {e}")

def main():
    if not os.path.exists(CONTENT_DIR):
        print(f"Error: Directory not found at '{CONTENT_DIR}'")
        return

    print("="*50)
    print("🚀 Starting Markdown Updater (LIVE MODE)")
    print("   (Files will be overwritten. Make sure you have a backup!)")
    print("="*50 + "\n")

    # 모든 md 파일 목록 가져오기
    all_md_files = [f for f in os.listdir(CONTENT_DIR) if f.endswith('.md')]
    
    if not all_md_files:
        print("No .md files found to process.")
        return

    # 파일 목록을 무작위로 섞기
    random.shuffle(all_md_files)
    
    # 설정된 개수만큼 파일 선택 (최대 파일 개수 초과하지 않도록)
    files_to_process = all_md_files[:FILES_TO_UPDATE_COUNT]
    
    print(f"Found {len(all_md_files)} files. Will process {len(files_to_process)} random files.\n")
    
    all_shrines = get_all_shrine_data()
    
    for filename in files_to_process:
        filepath = os.path.join(CONTENT_DIR, filename)
        update_file_content(filepath, all_shrines)
        print("-" * 20)

    print("\n🎉 Process complete.")

if __name__ == "__main__":
    main()