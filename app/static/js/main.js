/**
 * OKCaddie - Japan Golf Course Discovery Map
 * Features: Multi-language(EN/KO), Category Filtering with Icons, Google Maps Integration
 */

let allCourses = [];
let markers = [];
let map;
let currentLang = 'en'; // 기본 언어
let currentTheme = 'all'; // 기본 필터

// [데이터 매퍼] AI가 한국어 파일에 한국어 태그를 넣었을 경우를 대비한 표준 매핑 테이블
const CATEGORY_MAP = {
    "가성비": "Value for Money",
    "프리미엄": "Premium / Luxury",
    "대회코스": "Public Tournament",
    "숙박/리조트": "Stay & Play",
    "예약편리": "Easy Booking",
    "회원제": "Private Club"
};

/**
 * 1. 초기 데이터 로드 및 실행
 */
async function init() {
    try {
        const response = await fetch('/api/courses');
        const data = await response.json();
        allCourses = data.courses || [];
        
        // 푸터의 업데이트 날짜 갱신 (ID가 존재할 경우)
        const dateEl = document.getElementById('last-updated-date');
        if (dateEl) dateEl.textContent = data.last_updated || '-';
        
        // 초기 UI 설정 및 렌더링
        updateFilterButtonUI(); 
        renderApp();
        initMap();
    } catch (e) {
        console.error("Failed to load course data:", e);
    }
}

/**
 * 2. 필터 버튼 UI 업데이트 (언어 전환 시 텍스트 및 아이콘 교체)
 */
function updateFilterButtonUI() {
    document.querySelectorAll('.theme-button').forEach(btn => {
        // HTML의 data-en/ko에 저장된 아이콘 포함 텍스트를 가져옴
        const text = currentLang === 'en' ? btn.dataset.en : btn.dataset.ko;
        const badge = btn.querySelector('.count-badge');
        
        // 버튼 내부 초기화 후 텍스트와 숫자 배지를 다시 조립 (아이콘 보존 핵심)
        btn.innerHTML = ''; 
        btn.appendChild(document.createTextNode(text + " "));
        if (badge) btn.appendChild(badge);
    });
}

/**
 * 3. 카테고리별 데이터 개수 계산 (다국어 매핑 적용)
 */
function updateCategoryCounts(langFilteredData) {
    const counts = {
        "all": langFilteredData.length,
        "Value for Money": 0,
        "Premium / Luxury": 0,
        "Public Tournament": 0,
        "Stay & Play": 0,
        "Easy Booking": 0,
        "Private Club": 0
    };

    langFilteredData.forEach(course => {
        if (course.categories && Array.isArray(course.categories)) {
            course.categories.forEach(cat => {
                // 태그가 한국어라면 영어 표준 키로 변환, 아니면 그대로 사용
                const key = CATEGORY_MAP[cat] || cat;
                if (counts.hasOwnProperty(key)) {
                    counts[key]++;
                }
            });
        }
    });

    // HTML 내의 각 카운트 스팬에 숫자 삽입
    const idMap = {
        "count-all": counts["all"],
        "count-value": counts["Value for Money"],
        "count-premium": counts["Premium / Luxury"],
        "count-tour": counts["Public Tournament"],
        "count-resort": counts["Stay & Play"],
        "count-easy": counts["Easy Booking"],
        "count-private": counts["Private Club"]
    };

    for (const [id, val] of Object.entries(idMap)) {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    }
}

/**
 * 4. 메인 앱 렌더링 (리스트 및 카운트 업데이트)
 */
function renderApp() {
    // (1) 현재 언어셋 필터링
    const langFiltered = allCourses.filter(c => c.lang === currentLang);

    // (2) 카운트 계산 실행
    updateCategoryCounts(langFiltered);

    // (3) 선택된 테마 필터링 (영어/한국어 태그 동시 대응)
    const finalFiltered = langFiltered.filter(c => {
        if (currentTheme === 'all') return true;
        const themes = c.categories || [];
        const korTheme = Object.keys(CATEGORY_MAP).find(key => CATEGORY_MAP[key] === currentTheme);
        return themes.includes(currentTheme) || themes.includes(korTheme);
    });

    // (4) 총 개수 텍스트 업데이트 (푸터 또는 상태바)
    const totalEl = document.getElementById('total-courses');
    if (totalEl) totalEl.textContent = finalFiltered.length;

    // (5) 코스 리스트 그리드 생성
    const listContainer = document.getElementById('course-list');
    if (!listContainer) return;
    listContainer.innerHTML = '';

    finalFiltered.forEach(course => {
        const card = document.createElement('div');
        card.className = 'course-card';
        card.innerHTML = `
            <a href="${course.link}" class="card-thumb-link">
                <img src="${course.thumbnail}" class="card-thumb" alt="${course.title}" loading="lazy">
            </a>
            <div class="card-content">
                <h3 class="card-title"><a href="${course.link}">${course.title}</a></h3>
                <p class="card-summary">${course.summary}</p>
                <div class="card-footer">
                    <span class="view-link">${currentLang === 'en' ? 'View Details →' : '상세보기 →'}</span>
                </div>
            </div>
        `;
        listContainer.appendChild(card);
    });

    // (6) 지도 마커 업데이트
    updateMarkers(finalFiltered);
}

/**
 * 5. 구글 맵 초기화
 */
async function initMap() {
    const { Map } = await google.maps.importLibrary("maps");
    map = new Map(document.getElementById("map"), {
        center: { lat: 36.5, lng: 138.0 },
        zoom: 6,
        mapId: "OKCADDIE_MAP_ID", // 구글 클라우드에서 발급받은 Map ID (선택사항)
        mapTypeControl: false,
        streetViewControl: false,
        fullscreenControl: false
    });
}

/**
 * 6. 마커 생성 및 정보창(InfoWindow) 설정
 */
async function updateMarkers(courses) {
    if (!map) return;
    const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");

    // 기존 마커 제거
    markers.forEach(m => m.setMap(null));
    markers = [];

    const infoWindow = new google.maps.InfoWindow();

    courses.forEach(course => {
        if (!course.lat || !course.lng) return;

        // 커스텀 ⛳ 핀 디자인
        const pin = new PinElement({
            background: "#27ae60",
            borderColor: "#ffffff",
            glyph: "⛳",
            glyphColor: "#ffffff",
        });

        const marker = new AdvancedMarkerElement({
            map: map,
            position: { lat: parseFloat(course.lat), lng: parseFloat(course.lng) },
            title: course.title,
            content: pin.element,
        });

        // 마커 클릭 시 팝업 정보창
        marker.addListener("click", () => {
            const infoBox = `
                <div class="infowindow-content" style="padding:5px; max-width:200px;">
                    <img src="${course.thumbnail}" style="width:100%; border-radius:4px; margin-bottom:8px;">
                    <h4 style="margin:0 0 5px; font-size:14px;">${course.title}</h4>
                    <p style="margin:0 0 10px; font-size:12px; color:#666;">${course.address}</p>
                    <a href="${course.link}" style="display:block; background:#27ae60; color:#fff; text-align:center; padding:6px; border-radius:4px; text-decoration:none; font-size:12px; font-weight:bold;">
                        ${currentLang === 'en' ? 'View Details' : '상세보기'}
                    </a>
                </div>`;
            infoWindow.setContent(infoBox);
            infoWindow.open(map, marker);
        });

        markers.push(marker);
    });
}

/**
 * 7. 이벤트 리스너 설정
 */
// (1) 언어 전환 버튼
document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const target = e.target;
        if (currentLang === target.dataset.lang) return;

        // 버튼 활성화 상태 교체
        document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
        target.classList.add('active');

        // 상태 변경 및 전체 UI 갱신
        currentLang = target.dataset.lang;
        updateFilterButtonUI(); 
        renderApp();
    });
});

// (2) 테마 필터 버튼
document.querySelectorAll('.theme-button').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const themeBtn = e.currentTarget; // span 클릭 시에도 버튼 개체 인식

        // 버튼 활성화 상태 교체
        document.querySelectorAll('.theme-button').forEach(b => b.classList.remove('active'));
        themeBtn.classList.add('active');

        // 필터 적용 및 렌더링
        currentTheme = themeBtn.dataset.theme;
        renderApp();
    });
});

// 실행 시작
init();