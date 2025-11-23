# hatena_client.py
import os
import requests
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup
import base64
import hashlib
from datetime import datetime, timezone
import random
import re

# 환경 변수
HATENA_USERNAME = os.getenv('HATENA_USERNAME')
HATENA_BLOG_ID = os.getenv('HATENA_BLOG_ID')
HATENA_API_KEY = os.getenv('HATENA_API_KEY')

def create_wsse_header(username, api_key):
    nonce = hashlib.sha1(str(random.random()).encode()).digest()
    created = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    digest_base = nonce + created.encode() + api_key.encode()
    digest = hashlib.sha1(digest_base).digest()
    return f'UsernameToken Username="{username}", PasswordDigest="{base64.b64encode(digest).decode()}", Nonce="{base64.b64encode(nonce).decode()}", Created="{created}"'

def get_all_posts():
    print("🔎 하테나 블로그 데이터 수집 시작...")
    posts = []
    url = f"https://blog.hatena.ne.jp/{HATENA_USERNAME}/{HATENA_BLOG_ID}/atom/entry"
    
    max_pages = 5 
    current_page = 0

    while url and current_page < max_pages:
        headers = {'X-WSSE': create_wsse_header(HATENA_USERNAME, HATENA_API_KEY)}
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
        except Exception as e:
            print(f"❌ API 요청 실패: {e}")
            break

        root = ET.fromstring(response.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'app': 'http://www.w3.org/2007/app'}
        
        entries = root.findall('atom:entry', ns)
        
        for entry in entries:
            title = entry.find('atom:title', ns).text
            link_tag = entry.find('atom:link[@rel="alternate"]', ns)
            link = link_tag.get('href') if link_tag is not None else ""
            categories = [cat.get('term') for cat in entry.findall('atom:category', ns)]

            content_tag = entry.find('atom:content', ns)
            content_html = content_tag.text if content_tag is not None else ""
            soup = BeautifulSoup(content_html, 'html.parser')
            content_text = soup.get_text(separator=" ")

            # --- [이미지 추출 로직 복구] ---
            # 1. 기본값은 로고 이미지로 설정 (사진 없을 때 대비)
            thumbnail = "assets/images/JinjaMapLogo_Horizontal.png"
            
            # 2. 본문에서 모든 이미지 태그 찾기
            images = soup.find_all('img')
            
            for img in images:
                src = img.get('src')
                if not src: continue
                
                # 아이콘이나 로고 파일은 건너뜀
                if "icon" in src or "JinjaMapLogo" in src:
                    continue
                
                # 하테나 포토라이프(f.st-hatena.com) 또는 일반 이미지 파일이면 채택
                if "f.st-hatena.com" in src or src.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    thumbnail = src
                    break # 첫 번째 유효한 사진을 찾으면 중단
            # ------------------------------

            # --- [주소 추출 로직] ---
            address = None
            match = re.search(r'(소재지|주소|위치|Address)\s*[:：]?\s*([^\n\r]+)', content_text)
            if match:
                candidate = match.group(2).strip()
                if len(candidate) < 30 and ('〒' in candidate or any(x in candidate for x in ['도', '시', '구', '현', '町', '県', '市', '区'])):
                    address = candidate
            
            if not address:
                clean_title = re.sub(r'\[.*?\]', '', title)
                clean_title = re.split(r'[:：|\-–~]', clean_title)[0].strip()
                
                parenthesis_match = re.search(r'\(([^)]+)\)', clean_title)
                if parenthesis_match:
                    inner_text = parenthesis_match.group(1)
                    if re.search(r'[\u3000-\u303f\u3040-\u309f\u30a0-\u30ff\uff00-\uff9f\u4e00-\u9faf\u3400-\u4dbf]', inner_text):
                        clean_title = inner_text
                    else:
                        clean_title = re.sub(r'\(.*?\)', '', clean_title).strip()

                clean_title = clean_title.replace("를 찾아서", "").replace("방문", "").replace("여행", "").strip()
                
                if len(clean_title) > 1 and len(clean_title) < 30:
                    address = clean_title
                else:
                    continue

            posts.append({
                "title": title,
                "link": link,
                "categories": categories,
                "thumbnail": thumbnail,
                "address": address, 
                "summary": content_text[:100] + "..."
            })

        next_link = root.find('atom:link[@rel="next"]', ns)
        url = next_link.get('href') if next_link is not None else None
        current_page += 1
        
    return posts