/**
 * OKCaddie - Main Business Logic
 * (Full Version: Advanced Markers, Filters, i18n, Bug Fixed)
 */

let state = {
    allCourses: [],
    currentLang: 'en', // 기본 언어: 영어
    activeTheme: 'all',
    map: null,
    markers: [],
    infoWindow: null
};

// 언어별 공통 텍스트
const i18n = {
    en: { viewDetails: "View Details", address: "Address" },
    ko: { viewDetails: "상세 보기", address: "주소" }
};

async function initApp() {
    setupEventListeners();
    updateLanguageUI(); // 🔥 핵심 수정: 초기 로딩 시 기본 언어(en)에 맞춰 필터 텍스트 즉시 변경
    await initMap();
    await fetchCourses();
}

/**
 * [신규 추가] 테마 필터 버튼의 텍스트를 현재 언어에 맞게 동기화하는 함수
 */
function updateLanguageUI() {
    document.querySelectorAll('.theme-button').forEach(tBtn => {
        const text = state.currentLang === 'ko' ? tBtn.dataset.ko : tBtn.dataset.en;
        const badgeHtml = tBtn.querySelector('.count-badge').outerHTML;
        tBtn.innerHTML = `${text} ${badgeHtml}`;
    });
}

/**
 * 1. Google Maps 초기화 (Advanced Markers 적용)
 */
async function initMap() {
    const { Map, InfoWindow } = await google.maps.importLibrary("maps");
    
    state.map = new Map(document.getElementById("map"), {
        center: { lat: 36.5, lng: 138.0 },
        zoom: 6,
        mapId: "OKCADDIE_MAP_ID", // 필수: Google Cloud에서 발급받은 Map ID 입력
        disableDefaultUI: false,
        zoomControl: true,
    });

    // 둥근 모서리와 여백을 위한 InfoWindow 설정
    state.infoWindow = new InfoWindow({
        pixelOffset: new google.maps.Size(0, -10)
    });
}

/**
 * 2. 골프장 데이터 불러오기
 */
async function fetchCourses() {
    try {
        const response = await fetch('/api/courses');
        const data = await response.json();
        state.allCourses = data.courses;
        
        // 푸터 메타 데이터 갱신
        const totalCoursesEl = document.getElementById('total-courses');
        const lastUpdatedEl = document.getElementById('last-updated-date');
        
        if (totalCoursesEl) totalCoursesEl.textContent = state.allCourses.length;
        if (lastUpdatedEl) lastUpdatedEl.textContent = data.last_updated;

        renderApp();
    } catch (error) {
        console.error("Data load error:", error);
    }
}

/**
 * 3. 메인 화면 렌더링 (지도 + 리스트)
 */
function renderApp() {
    // 선택된 언어와 카테고리에 맞는 데이터 필터링
    const filtered = state.allCourses.filter(c => {
        const langMatch = c.lang === state.currentLang;
        const themeMatch = state.activeTheme === 'all' || c.categories.includes(state.activeTheme);
        return langMatch && themeMatch;
    });

    updateMarkers(filtered);
    updateList(filtered);
    updateCategoryCounts();
}

/**
 * 4. 지도에 고급 사진 마커 그리기
 */
async function updateMarkers(courses) {
    const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");
    
    // 이전 마커 초기화
    state.markers.forEach(m => m.map = null);
    state.markers = [];

    courses.forEach(course => {
        // 커스텀 마커 HTML 요소 생성
        const markerTag = document.createElement('div');
        markerTag.className = 'caddie-marker';
        markerTag.innerHTML = `<img src="${course.thumbnail}" alt="${course.title}">`;

        // AdvancedMarkerElement 생성
        const marker = new AdvancedMarkerElement({
            map: state.map,
            position: { lat: course.lat, lng: course.lng },
            title: course.title,
            content: markerTag,
        });

        // 마커 클릭 시 정보창(InfoWindow) 표시
        marker.addListener('click', () => {
            const contentString = `
                <div class="info-card">
                    <div class="info-title">${course.title}</div>
                    <div class="info-address"><b>${i18n[state.currentLang].address}:</b> ${course.address}</div>
                    <a href="${course.link}" class="info-btn">${i18n[state.currentLang].viewDetails}</a>
                </div>
            `;
            state.infoWindow.setContent(contentString);
            state.infoWindow.open(state.map, marker);
            google.maps.event.addListenerOnce(state.infoWindow, 'domready', () => {
                const btn = document.querySelector('.info-btn');
                if (btn) {
                    btn.addEventListener('click', () => {
                        if (typeof gtag === 'function') {
                            gtag('event', 'map_infowindow_detail_click', {
                                event_category: 'map_home',
                                event_label: (btn.getAttribute('href') || '').split('?')[0]
                            });
                        }
                    }, { once: true });
                }
            });
        });

        state.markers.push(marker);
    });
}

/**
 * 5. 썸네일 카드 리스트 업데이트
 */
function updateList(courses) {
    const listContainer = document.getElementById('course-list');
    if (!listContainer) return;

    listContainer.innerHTML = courses.map(c => `
        <article class="course-card">
            <a href="${c.link}">
                <img src="${c.thumbnail}" class="card-thumb" alt="${c.title}" loading="lazy">
                <div class="card-content">
                    <div class="card-title">${c.title}</div>
                    <p style="font-size:0.9rem; color:#666;">${c.summary.substring(0, 100)}...</p>
                </div>
            </a>
        </article>
    `).join('');
}

/**
 * 6. 상단 필터 버튼의 아이템 개수(Badge) 동기화
 */
function updateCategoryCounts() {
    const currentLangCourses = state.allCourses.filter(c => c.lang === state.currentLang);
    
    const countAllEl = document.getElementById('count-all');
    if (countAllEl) countAllEl.textContent = currentLangCourses.length;
    
    const mapping = {
        'count-value': "Value for Money",
        'count-premium': "Premium / Luxury",
        'count-tour': "Public Tournament",
        'count-resort': "Stay & Play",
        'count-easy': "Easy Booking",
        'count-private': "Private Club"
    };

    Object.keys(mapping).forEach(id => {
        const count = currentLangCourses.filter(c => c.categories.includes(mapping[id])).length;
        const el = document.getElementById(id);
        if (el) el.textContent = count;
    });
}

/**
 * 7. 사용자의 클릭 이벤트 설정
 */
function setupEventListeners() {
    // 언어 전환
    document.querySelectorAll('.lang-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            state.currentLang = btn.dataset.lang;
            
            // 버튼 활성화 클래스 토글
            document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            // UI 업데이트 함수 호출 (중복 제거)
            updateLanguageUI();
            renderApp();
        });
    });

    // 테마 필터링
    document.querySelectorAll('.theme-button').forEach(btn => {
        btn.addEventListener('click', () => {
            state.activeTheme = btn.dataset.theme;
            
            // 버튼 활성화 클래스 토글
            document.querySelectorAll('.theme-button').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            renderApp();
        });
    });

    // 코스 카드 클릭 → GA4 (광고 전환·퍼널 분석)
    const listContainer = document.getElementById('course-list');
    if (listContainer && !listContainer.dataset.gaBound) {
        listContainer.dataset.gaBound = '1';
        listContainer.addEventListener('click', (e) => {
            const a = e.target.closest('a');
            if (!a || !a.getAttribute('href')) return;
            if (typeof gtag === 'function') {
                gtag('event', 'course_card_click', {
                    event_category: 'map_home',
                    event_label: (a.getAttribute('href') || '').split('#')[0]
                });
            }
        });
    }
}

// 스크립트 로드 완료 후 실행
window.onload = initApp;