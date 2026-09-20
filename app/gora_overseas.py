"""Rakuten GORA overseas catalog (Hawaii, Guam, Thailand, Vietnam).

Japan tee times stay on /search/result/. These courses book via c_id pages.
Hub fallback: https://a.r10.to/h5wlL0
"""

from __future__ import annotations

from urllib.parse import quote

GORA_HGC = "53117f43.0bea4fc1.53117f44.cd5b3814"
GORA_UT = "eyJwYWdlIjoidXJsIiwidHlwZSI6InRleHQiLCJjb2wiOjF9"
OVERSEAS_HUB_URL = "https://a.r10.to/h5wlL0"

COUNTRY_ISO = {
    "jp": "JP",
    "us": "US",
    "gu": "GU",
    "th": "TH",
    "vn": "VN",
}

# GORA overseas TOP featured courses (2026-09-15).
OVERSEAS_COURSES: tuple[dict[str, str], ...] = (
    {
        "slug": "onward_mangilao_golf",
        "gora_cid": "510003",
        "country": "gu",
        "title": "Onward Mangilao Golf Club",
        "address": "Mangilao, Guam",
        "lat": "13.4470",
        "lng": "144.8470",
        "categories": "Ocean View, Resort, Scenic",
        "airport": "GUM, about 25 minutes by car",
        "note_en": "East-coast Guam course looking over the Pacific. Resort-style cart golf; trade winds matter on exposed holes.",
        "note_ko": "괌 동해안에서 태평양이 보이는 리조트 코스. 카트 플레이가 기본이고, 바람 부는 홀은 클럽 선택이 갈립니다.",
        "season_en": "Year-round. Mornings are cooler; mid-day sun is strong.",
        "season_ko": "연중 플레이. 오전 티타임이 덜 덥고, 한낮은 햇볕이 강합니다.",
        "airport_ja": "GUMから車で約25分",
        "note_ja": "グアム東海岸、太平洋を望むリゾートコース。カートプレーが基本で、風の強いホールではクラブ選択が変わります。",
        "season_ja": "通年。午前のティーが涼しく、日中は日差しが強いです。",
    },
    {
        "slug": "leopalace_resort_guam",
        "gora_cid": "520024",
        "country": "gu",
        "title": "Leopalace Resort Country Club",
        "address": "Yona, Guam",
        "lat": "13.3890",
        "lng": "144.7240",
        "categories": "Resort, Value for Money, Scenic",
        "airport": "GUM, about 25 minutes by car",
        "note_en": "South Guam resort club with a hotel stay-and-play option. A practical first Guam round from the airport.",
        "note_ko": "괌 남쪽 리조트 클럽. 호텔 패키지와 함께 잡는 경우가 많고, 공항에서 첫 라운드로 쓰기 쉽습니다.",
        "season_en": "Year-round tropical. Book an early tee to avoid heat and showers.",
        "season_ko": "연중 열대 기후. 더위와 소나기를 피하려면 이른 티타임이 안전합니다.",
        "airport_ja": "GUMから車で約25分",
        "note_ja": "グアム南部のリゾートクラブ。ホテル滞在とセットで予約しやすく、空港からの最初のラウンド向きです。",
        "season_ja": "通年の熱帯気候。暑さと驟雨を避けるなら早朝ティーが安心です。",
    },
    {
        "slug": "onward_talofofo_golf",
        "gora_cid": "520058",
        "country": "gu",
        "title": "Onward Talofofo Golf Club",
        "address": "Talofofo, Guam",
        "lat": "13.3380",
        "lng": "144.7590",
        "categories": "Championship, Ocean View, Scenic",
        "airport": "GUM, about 35 minutes by car",
        "note_en": "Hillside layout in southern Guam with Pacific views. Firmer and more exposed than Mangilao.",
        "note_ko": "괌 남쪽 언덕 코스. 태평양 조망이 있고, 만길라오보다 노출되고 페어웨이가 단단한 편입니다.",
        "season_en": "Year-round. Wind is part of the course — take an extra club on ocean holes.",
        "season_ko": "연중. 바다 홀은 바람이 기본이라 클럽을 하나 더 잡는 경우가 많습니다.",
        "airport_ja": "GUMから車で約35分",
        "note_ja": "グアム南部の丘陵コース。太平洋の眺望があり、マンギラオより露出が多くフェアウェイが締まった印象です。",
        "season_ja": "通年。海沿いホールは風が前提なので、クラブを1本長く持つことが多いです。",
    },
    {
        "slug": "finest_guam_golf",
        "gora_cid": "520698",
        "country": "gu",
        "title": "Finest Guam Golf & Resort",
        "address": "Dededo, Guam",
        "lat": "13.5180",
        "lng": "144.8360",
        "categories": "Resort, Public Tournament, Value for Money",
        "airport": "GUM, about 15 minutes by car",
        "note_en": "Northern Guam (Dededo), close to Tumon hotels. Formerly Starts Guam Golf Resort.",
        "note_ko": "괌 북쪽 데데도. 투몬 호텔가에서 가깝고, 예전 스타츠 괌 골프 리조트입니다.",
        "season_en": "Year-round. Easy add-on round if you are staying in Tumon.",
        "season_ko": "연중. 투몬에 묵는다면 이동이 짧은 라운드입니다.",
        "airport_ja": "GUMから車で約15分",
        "note_ja": "グアム北部デデド。トゥモンのホテル街から近く、旧スターツ・グアム・ゴルフ・リゾートです。",
        "season_ja": "通年。トゥモン滞在なら移動が短いラウンドです。",
    },
    {
        "slug": "alpine_golf_club_bangkok",
        "gora_cid": "520401",
        "country": "th",
        "title": "Alpine Golf Club",
        "address": "Pathum Thani, Thailand",
        "lat": "14.1170",
        "lng": "100.6170",
        "categories": "Championship, Premium / Luxury, Tournament",
        "airport": "BKK, about 60–75 minutes by car",
        "note_en": "Ronald Fream championship course north of Bangkok. One of the region's better-known tests.",
        "note_ko": "방콕 북쪽 파툼타니의 로널드 프림 설계 챔피언십 코스. 태국에서 이름이 가장 알려진 코스 중 하나입니다.",
        "season_en": "Cooler season November–February. April heat is harsh for a full 18.",
        "season_ko": "11–2월이 선선합니다. 4월 더위에는 18홀이 부담스럽습니다.",
        "airport_ja": "BKKから車で約60〜75分",
        "note_ja": "バンコク北パトゥムターニーのロナルド・フリーム設計チャンピオンシップコース。タイでも知名度の高いコースのひとつです。",
        "season_ja": "11〜2月が涼しいです。4月の暑さでは18ホールがきつくなります。",
    },
    {
        "slug": "nikanti_golf_club",
        "gora_cid": "520402",
        "country": "th",
        "title": "NiKanti Golf Club",
        "address": "Nakhon Pathom, Thailand",
        "lat": "13.7870",
        "lng": "100.2730",
        "categories": "Championship, Scenic, Premium / Luxury",
        "airport": "BKK, about 50–70 minutes by car",
        "note_en": "Southwest of Bangkok. Distinctive shaping and a quieter round than the inner-city clubs.",
        "note_ko": "방콕 남서쪽 나콘파톰. 시내 클럽보다 한적하고, 코스 조형이 뚜렷합니다.",
        "season_en": "November–February is the comfortable window. Carry extra water in the hot months.",
        "season_ko": "11–2월이 편합니다. 더운 달에는 물을 충분히 챙기세요.",
        "airport_ja": "BKKから車で約50〜70分",
        "note_ja": "バンコク南西ナコーンパトム。都心部のクラブより静かで、造形がはっきりしています。",
        "season_ja": "11〜2月が快適です。暑い月は水分を十分に。",
    },
    {
        "slug": "thai_country_club",
        "gora_cid": "520405",
        "country": "th",
        "title": "Thai Country Club",
        "address": "Samut Prakan, Thailand",
        "lat": "13.5850",
        "lng": "100.6380",
        "categories": "Championship, Premium / Luxury, Historic",
        "airport": "BKK, about 30–45 minutes by car",
        "note_en": "Peninsula Hotels group club near Suvarnabhumi. Convenient if you land in Bangkok and want a serious round the same trip.",
        "note_ko": "수완나품 공항과 가까운 페닌슐라 그룹 클럽. 방콕 도착 일정에 본격 라운드를 넣기 쉽습니다.",
        "season_en": "November–February. Weekday mornings are the practical booking window.",
        "season_ko": "11–2월. 평일 오전이 예약·더위 면에서 현실적입니다.",
        "airport_ja": "BKKから車で約30〜45分",
        "note_ja": "スワンナプーム空港に近いペニンシュラ系クラブ。バンコク到着の行程に本格ラウンドを入れやすいです。",
        "season_ja": "11〜2月。平日午前が予約・暑さの面で現実的です。",
    },
    {
        "slug": "thana_city_golf",
        "gora_cid": "520406",
        "country": "th",
        "title": "Thana City Golf & Sports Club",
        "address": "Samut Prakan, Thailand",
        "lat": "13.6600",
        "lng": "100.6800",
        "categories": "Public Tournament, Value for Money, Resort",
        "airport": "BKK, about 25–40 minutes by car",
        "note_en": "Close to Bangkok downtown and the airport. A practical public-style option versus members-only clubs.",
        "note_ko": "방콕 시내·공항에서 가깝습니다. 회원제보다 방문객 라운드가 수월한 편입니다.",
        "season_en": "Cooler months November–February. Confirm caddie and cart package on GORA.",
        "season_ko": "11–2월이 선선합니다. 캐디·카트 포함 여부는 GORA에서 확인하세요.",
        "airport_ja": "BKKから車で約25〜40分",
        "note_ja": "バンコク市街・空港から近いです。会員制より訪問者ラウンドがしやすい傾向です。",
        "season_ja": "11〜2月が涼しいです。キャディ・カート込みかはGORAで確認してください。",
    },
    {
        "slug": "tan_son_nhat_golf",
        "gora_cid": "520462",
        "country": "vn",
        "title": "Tan Son Nhat Golf Course",
        "address": "Ho Chi Minh City, Vietnam",
        "lat": "10.8180",
        "lng": "106.6590",
        "categories": "Public Tournament, Value for Money, City Course",
        "airport": "SGN, about 10–20 minutes by car",
        "note_en": "Public course next to Tan Son Nhat airport. Easy add-on round on a Ho Chi Minh layover or city stay.",
        "note_ko": "탄손녓 공항 옆 퍼블릭 코스. 호치민 시내 체류나 경유 일정에 라운드를 넣기 쉽습니다.",
        "season_en": "December–April is drier in the south. Watch afternoon storms in the wet season.",
        "season_ko": "남부는 12–4월이 건조합니다. 우기에는 오후 소나기를 보세요.",
        "airport_ja": "SGNから車で約10〜20分",
        "note_ja": "タンソンニャット空港そばのパブリックコース。ホーチミン滞在や乗り継ぎにラウンドを入れやすいです。",
        "season_ja": "南部は12〜4月が乾季です。雨季は午後の驟雨に注意。",
    },
    {
        "slug": "brg_kings_island_golf",
        "gora_cid": "520467",
        "country": "vn",
        "title": "BRG Kings Island Golf Resort",
        "address": "Hanoi, Vietnam",
        "lat": "21.1180",
        "lng": "105.3280",
        "categories": "Resort, Scenic, Championship",
        "airport": "HAN, about 60 minutes by car plus a short boat to the island",
        "note_en": "Lake-island resort west of Hanoi (Dong Mo). Mountain-view nines; allow transfer time from the city.",
        "note_ko": "하노이 서쪽 동모 호수 섬 리조트. 마운틴 뷰 나인이 있고, 시내에서 이동 시간을 넉넉히 보세요.",
        "season_en": "October–April is the north's comfortable window. Winter mornings can be cool and misty.",
        "season_ko": "북부는 10–4월이 편합니다. 겨울 아침은 쌀쌀하고 안개가 끼기도 합니다.",
        "airport_ja": "HANから車で約60分＋ボート短い移動",
        "note_ja": "ハノイ西ドンモー湖の島リゾート。マウンテンビューのナインがあり、市内からの移動時間を余裕で見てください。",
        "season_ja": "北部は10〜4月が快適。冬の朝は冷え込み、霧が出ることもあります。",
    },
    {
        "slug": "long_bien_golf",
        "gora_cid": "520468",
        "country": "vn",
        "title": "Long Bien Golf Course",
        "address": "Hanoi, Vietnam",
        "lat": "21.0540",
        "lng": "105.8860",
        "categories": "Championship, Public Tournament, City Course",
        "airport": "HAN, about 30–40 minutes by car",
        "note_en": "27-hole Nelson & Haworth course in Hanoi. More city-accessible than Kings Island.",
        "note_ko": "하노이 시내권 27홀(Nelson & Haworth). 킹스 아일랜드보다 접근이 쉽습니다.",
        "season_en": "October–April. Confirm which two nines you are playing when you check in.",
        "season_ko": "10–4월. 체크인 때 어느 두 나인을 도는지 확인하세요.",
        "airport_ja": "HANから車で約30〜40分",
        "note_ja": "ハノイ都市圏の27ホール（Nelson & Haworth）。キングスアイランドよりアクセスしやすいです。",
        "season_ja": "10〜4月。チェックイン時にどの2ナインかを確認してください。",
    },
    {
        "slug": "montgomerie_links_vietnam",
        "gora_cid": "520472",
        "country": "vn",
        "title": "Montgomerie Links Vietnam",
        "address": "Da Nang, Vietnam",
        "lat": "15.9730",
        "lng": "108.3470",
        "categories": "Links Style, Championship, Ocean View",
        "airport": "DAD, about 30 minutes by car",
        "note_en": "Colin Montgomerie links-style course between Da Nang and Hoi An. Wind and sandy waste are the defense.",
        "note_ko": "다낭–호이안 사이 콜린 몬고메리 링크스 스타일. 바람과 샌디 웨이스트가 핵심 방어입니다.",
        "season_en": "February–May and September are the usual windows. Late-year storms can close coastal holes.",
        "season_ko": "2–5월, 9월이 무난합니다. 연말 폭풍 시기에는 해안 홀 운영을 확인하세요.",
        "airport_ja": "DADから車で約30分",
        "note_ja": "ダナン〜ホイアン間のコリン・モントゴメリー設計リンクス風。風とサンディ・ウェイストが主な守りです。",
        "season_ja": "2〜5月、9月が無難。年末の嵐の時期は海岸ホールの営業を確認してください。",
    },
    {
        "slug": "kapolei_golf_course",
        "gora_cid": "520480",
        "country": "us",
        "title": "Kapolei Golf Course",
        "address": "Kapolei, Oahu, Hawaii",
        "lat": "21.3350",
        "lng": "-158.0780",
        "categories": "Championship, Public Tournament, Scenic",
        "airport": "HNL, about 30 minutes by car; 43 km west of Waikiki",
        "note_en": "Ted Robinson public course in West Oahu. Former LPGA / Champions Tour host. Rental clubs are standard for visitors.",
        "note_ko": "오아후 서쪽 테드 로빈슨 퍼블릭 코스. LPGA·챔피언스 투어 개최지. 방문객은 렌탈 클럽이 일반적입니다.",
        "season_en": "Year-round. Winter (Dec–Mar) is peak visitor season — book well ahead.",
        "season_ko": "연중. 12–3월 성수기에는 미리 예약하세요.",
        "airport_ja": "HNLから車で約30分、ワイキキから西へ約43km",
        "note_ja": "オアフ西のテッド・ロビンソン設計パブリック。LPGA・チャンピオンズツアー開催歴あり。訪問者はレンタルクラブが一般的です。",
        "season_ja": "通年。12〜3月のハイシーズンは早めの予約を。",
    },
    {
        "slug": "ko_olina_golf_club",
        "gora_cid": "520483",
        "country": "us",
        "title": "Ko Olina Golf Club",
        "address": "Kapolei, Oahu, Hawaii",
        "lat": "21.3370",
        "lng": "-158.1190",
        "categories": "Resort, Championship, Premium / Luxury",
        "airport": "HNL, about 30–35 minutes; 49 km west of Waikiki",
        "note_en": "Resort course at Ko Olina. Stay-and-play with the nearby hotels; LPGA Hawaiian Ladies host in past years.",
        "note_ko": "코올리나 리조트 코스. 인근 호텔 스테이앤플레이가 자연스럽고, LPGA 하와이안 레이디스 개최 이력이 있습니다.",
        "season_en": "Year-round resort golf. Afternoon trade winds pick up — morning tees are calmer.",
        "season_ko": "연중 리조트 골프. 오후 무역풍이 강해져서 오전 티타임이 잔잔합니다.",
        "airport_ja": "HNLから車で約30〜35分、ワイキキから西へ約49km",
        "note_ja": "コオリナのリゾートコース。近隣ホテルのステイ＆プレー向きで、LPGA Hawaiian Ladies開催歴があります。",
        "season_ja": "通年のリゾートゴルフ。午後の貿易風が強まるので午前ティーが穏やかです。",
    },
    {
        "slug": "turtle_bay_palmer",
        "gora_cid": "520484",
        "country": "us",
        "title": "Turtle Bay Resort Palmer Course",
        "address": "Kahuku, Oahu, Hawaii",
        "lat": "21.7060",
        "lng": "-157.9980",
        "categories": "Championship, Ocean View, Resort",
        "airport": "HNL, about 55–70 minutes to the North Shore",
        "note_en": "Arnold Palmer course at Turtle Bay on Oahu's North Shore. Ocean holes and wind; the Fazio course is the sister layout.",
        "note_ko": "오아후 북쇼어 터틀베이의 아놀드 파머 코스. 바다 홀과 바람이 있고, 파지오 코스가 형제 레이아웃입니다.",
        "season_en": "Year-round. North Shore swell season (winter) makes the ocean holes dramatic — and windier.",
        "season_ko": "연중. 겨울 북쇼어 스웰 시즌에는 바다 홀이 더 극적이고 바람도 셉니다.",
        "airport_ja": "HNLからノースショアまで車で約55〜70分",
        "note_ja": "オアフ北岸タートルベイのアーノルド・パーマーコース。海ホールと風が特徴で、ファジオコースが姉妹レイアウトです。",
        "season_ja": "通年。冬のノースショア・スウェル期は海ホールがより劇的で風も強いです。",
    },
    {
        "slug": "hawaii_prince_golf",
        "gora_cid": "520488",
        "country": "us",
        "title": "Hawaii Prince Golf Club",
        "address": "Ewa Beach, Oahu, Hawaii",
        "lat": "21.3330",
        "lng": "-158.0470",
        "categories": "Resort, Championship, Value for Money",
        "airport": "HNL, about 30 minutes; ~40 minutes west of Waikiki",
        "note_en": "27-hole West Oahu club (three nines). A common visitor booking versus Waikiki hotel golf.",
        "note_ko": "오아후 서쪽 27홀(나인 3개). 와이키키 호텔 골프보다 방문객 예약이 많은 편입니다.",
        "season_en": "Year-round. Confirm which two nines you drew when you check in.",
        "season_ko": "연중. 체크인 때 어느 두 나인을 도는지 확인하세요.",
        "airport_ja": "HNLから車で約30分、ワイキキから西へ約40分",
        "note_ja": "オアフ西の27ホール（ナイン3つ）。ワイキキホテルゴルフより訪問者予約が多い傾向です。",
        "season_ja": "通年。チェックイン時にどの2ナインかを確認してください。",
    },
    {
        "slug": "waikele_country_club",
        "gora_cid": "520494",
        "country": "us",
        "title": "Waikele Country Club",
        "address": "Waipahu, Oahu, Hawaii",
        "lat": "21.4020",
        "lng": "-158.0060",
        "categories": "Public Tournament, Scenic, Value for Money",
        "airport": "HNL, about 25–35 minutes",
        "note_en": "Central Oahu views toward Pearl Harbor and the Koolau range. Shorter transfer than North Shore.",
        "note_ko": "오아후 중앙. 진주만·코오라우 방향 조망이 있고, 북쇼어보다 이동이 짧습니다.",
        "season_en": "Year-round. A practical round if you are staying in Waikiki without a west-side hotel.",
        "season_ko": "연중. 와이키키에 묵고 서쪽 호텔이 없다면 현실적인 라운드입니다.",
        "airport_ja": "HNLから車で約25〜35分",
        "note_ja": "オアフ中央。パールハーバー・コオラウ方面の眺望があり、ノースショアより移動が短いです。",
        "season_ja": "通年。ワイキキ滞在で西ホテルがないなら現実的なラウンドです。",
    },
)

OVERSEAS_BY_SLUG = {c["slug"]: c for c in OVERSEAS_COURSES}
THUMBNAILS = (
    "https://images.unsplash.com/photo-1587174486073-ae5e5cff23aa?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1535131749006-b7f58c99034b?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1591491640784-3232eb748d4b?auto=format&fit=crop&w=1200",
    "https://images.unsplash.com/photo-1563299796-17596ed6b017?auto=format&fit=crop&w=1200",
)


def gora_affiliate_wrap(destination_url: str) -> str:
    pc = quote(destination_url, safe="")
    return (
        f"https://hb.afl.rakuten.co.jp/hgc/{GORA_HGC}/"
        f"?pc={pc}&link_type=text&ut={GORA_UT}"
    )


def overseas_course_url(gora_cid: str) -> str:
    cid = (gora_cid or "").strip()
    if not cid.isdigit():
        return ""
    return f"https://booking.gora.golf.rakuten.co.jp/guide/disp/c_id/{cid}/"


def japan_course_calendar_url(gora_cid: str) -> str:
    """Japan domestic tee-time calendar — better conversion than keyword search."""
    cid = (gora_cid or "").strip()
    if not cid.isdigit():
        return ""
    return f"https://search.gora.golf.rakuten.co.jp/cal/disp/c_id/{cid}/"


def overseas_booking_dest(*, gora_cid: str = "", slug: str = "") -> str:
    cid = (gora_cid or "").strip()
    if not cid and slug:
        row = OVERSEAS_BY_SLUG.get(slug) or {}
        cid = str(row.get("gora_cid") or "")
    course_url = overseas_course_url(cid)
    if course_url:
        return gora_affiliate_wrap(course_url)
    return OVERSEAS_HUB_URL


def japan_booking_dest(gora_cid: str) -> str:
    cal = japan_course_calendar_url(gora_cid)
    if cal:
        return gora_affiliate_wrap(cal)
    return ""


def is_overseas_slug(slug: str) -> bool:
    return (slug or "").strip() in OVERSEAS_BY_SLUG
