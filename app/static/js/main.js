/**
 * OKCaddie - Japan Golf Course Discovery
 * Full Logic for Map, Multi-Language UI, and Dynamic Category Counting
 */

let allCourses = [];
let markers = [];
let map;
let currentLang = 'en'; 
let currentTheme = 'all';

// [매퍼] 데이터가 한국어로 들어와도 영어 필터와 연동되게 함
const CATEGORY_MAP = {
    "가성비 골프": "Value for Money",
    "프리미엄": "Premium / Luxury",
    "대회 코스": "Public Tournament",
    "숙박/리조트": "Stay & Play",
    "예약 편리": "Easy Booking",
    "회원제/명문": "Private Club"
};

async function init() {
    try {
        const response = await fetch('/api/courses');
        const data = await response.json();
        allCourses = data.courses || [];
        
        const dateEl = document.getElementById('last-updated-date');
        if (dateEl) dateEl.textContent = data.last_updated || '-';
        
        // 버튼 텍스트 초기화 및 첫 렌더링
        updateFilterButtonUI(); 
        renderApp();
        initMap();
    } catch (e) {
        console.error("Data load failed:", e);
    }
}

// 1. 버튼 텍스트 언어 전환 (배지 보존)
function updateFilterButtonUI() {
    document.querySelectorAll('.theme-button').forEach(btn => {
        const text = currentLang === 'en' ? btn.dataset.en : btn.dataset.ko;
        const badge = btn.querySelector('.count-badge');
        
        // 텍스트 노드만 안전하게 교체
        btn.innerHTML = ''; 
        btn.appendChild(document.createTextNode(text + " "));
        if (badge) btn.appendChild(badge);
    });
}

// 2. 카테고리별 개수 실시간 계산 (다국어 대응)
function updateCategoryCounts(langData) {
    const counts = {
        "all": langData.length,
        "Value for Money": 0,
        "Premium / Luxury": 0,
        "Public Tournament": 0,
        "Stay & Play": 0,
        "Easy Booking": 0,
        "Private Club": 0
    };

    langData.forEach(course => {
        if (course.categories && Array.isArray(course.categories)) {
            course.categories.forEach(cat => {
                // 한글 태그면 영어 키로 변환, 영어면 그대로 사용
                const key = CATEGORY_MAP[cat] || cat;
                if (counts.hasOwnProperty(key)) {
                    counts[key]++;
                }
            });
        }
    });

    // 화면에 숫자 대입
    const countIds = {
        "count-all": counts["all"],
        "count-value": counts["Value for Money"],
        "count-premium": counts["Premium / Luxury"],
        "count-tour": counts["Public Tournament"],
        "count-resort": counts["Stay & Play"],
        "count-easy": counts["Easy Booking"],
        "count-private": counts["Private Club"]
    };

    for (const [id, val] of Object.entries(countIds)) {
        const el = document.getElementById(id);
        if (el) el.textContent = val;
    }
}

// 3. 메인 렌더링 로직
function renderApp() {
    // (1) 현재 언어셋 필터링
    const langFiltered = allCourses.filter(c => c.lang === currentLang);

    // (2) 카테고리 개수 계산 (UI 업데이트)
    updateCategoryCounts(langFiltered);

    // (3) 선택한 테마 필터링 (영어/한국어 태그 동시 대응)
    const finalFiltered = langFiltered.filter(c => {
        if (currentTheme === 'all') return true;
        const themes = c.categories || [];
        const korTheme = Object.keys(CATEGORY_MAP).find(key => CATEGORY_MAP[key] === currentTheme);
        return themes.includes(currentTheme) || themes.includes(korTheme);
    });

    // (4) 총 개수 텍스트
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
                <div class="card-meta">📍 ${course.address.split(',')[0]}</div>
                <h3 class="card-title"><a href="${course.link}">${course.title}</a></h3>
                <p class="card-summary">${course.summary}</p>
                <div class="card-footer">
                    <span class="view-link">${currentLang === 'en' ? 'View Details →' : '상세보기 →'}</span>
                </div>
            </div>
        `;
        listContainer.appendChild(card);
    });

    // (6) 지도 마커 갱신
    updateMarkers(finalFiltered);
}

// 4. 지도 초기화
// main.js 내부의 initMap 함수 부분
async function initMap() {
    try {
        // google 객체가 있는지 확인 후 라이브러리 로드
        const { Map } = await google.maps.importLibrary("maps");
        const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");
        
        map = new Map(document.getElementById("map"), {
            center: { lat: 36.5, lng: 138.0 },
            zoom: 6,
            mapId: "OKCADDIE_MAP_ID",
            mapTypeControl: false,
            streetViewControl: false,
            fullscreenControl: false
        });

        // 지도가 로드된 후에 마커를 그릴 수 있도록 renderApp 호출 시점 조절 가능
        renderApp(); 
    } catch (error) {
        console.error("Google Maps load error:", error);
    }
}

// 5. 마커 갱신 및 정보창 설정
async function updateMarkers(courses) {
    if (!map) return;
    const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");

    markers.forEach(m => m.setMap(null));
    markers = [];

    const infoWindow = new google.maps.InfoWindow();

    courses.forEach(course => {
        if (!course.lat || !course.lng) return;

        const pin = new PinElement({
            background: "#27ae60",
            borderColor: "#ffffff",
            glyph: "⛳",
            glyphColor: "#ffffff"
        });

        const marker = new AdvancedMarkerElement({
            map: map,
            position: { lat: parseFloat(course.lat), lng: parseFloat(course.lng) },
            title: course.title,
            content: pin.element
        });

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

// 6. 이벤트 핸들러
document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const target = e.target;
        if (currentLang === target.dataset.lang) return;
        document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
        target.classList.add('active');
        currentLang = target.dataset.lang;
        updateFilterButtonUI(); 
        renderApp();
    });
});

document.querySelectorAll('.theme-button').forEach(btn => {
    btn.addEventListener('click', (e) => {
        const themeBtn = e.currentTarget;
        document.querySelectorAll('.theme-button').forEach(b => b.classList.remove('active'));
        themeBtn.classList.add('active');
        currentTheme = themeBtn.dataset.theme;
        renderApp();
    });
});

// 실행
init();