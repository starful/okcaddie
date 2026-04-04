let allCourses = [];
let markers = [];
let map;
let currentLang = 'en';
let currentTheme = 'all';

// 1. 초기 데이터 로드
async function init() {
    try {
        const response = await fetch('/api/courses');
        const data = await response.json();
        allCourses = data.courses || [];
        
        document.getElementById('last-updated-date').textContent = data.last_updated || '-';
        
        renderApp();
        initMap();
    } catch (e) {
        console.error("Data load failed:", e);
    }
}

// 2. 메인 렌더링 함수
function renderApp() {
    const filtered = allCourses.filter(c => {
        const langMatch = c.lang === currentLang;
        const themeMatch = currentTheme === 'all' || (c.categories && c.categories.includes(currentTheme));
        return langMatch && themeMatch;
    });

    // 상단 카운트 업데이트
    document.getElementById('total-courses').textContent = filtered.length;

    // 리스트 렌더링
    const listContainer = document.getElementById('course-list');
    listContainer.innerHTML = '';

    filtered.forEach(course => {
        const card = document.createElement('div');
        card.className = 'course-card';
        card.innerHTML = `
            <a href="${course.link}"><img src="${course.thumbnail}" class="card-thumb" alt="${course.title}"></a>
            <div class="card-content">
                <h3 class="card-title"><a href="${course.link}">${course.title}</a></h3>
                <p class="card-summary">${course.summary}</p>
                <div class="card-meta">📍 ${course.address.split(',')[0]}</div>
            </div>
            <div class="card-footer">
                <span class="view-link">View Detail →</span>
            </div>
        `;
        listContainer.appendChild(card);
    });

    updateMarkers(filtered);
}

// 3. 지도 초기화 (Google Maps)
async function initMap() {
    const { Map } = await google.maps.importLibrary("maps");
    
    map = new Map(document.getElementById("map"), {
        center: { lat: 36.0, lng: 138.0 }, // 일본 중심
        zoom: 6,
        mapId: "OKCADDIE_MAP_ID", // Google Cloud Console에서 생성한 Map ID (선택사항)
        mapTypeControl: false,
        streetViewControl: false
    });
}

// 4. 마커 업데이트
async function updateMarkers(courses) {
    if (!map) return;
    const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");

    // 기존 마커 제거
    markers.forEach(m => m.setMap(null));
    markers = [];

    const infoWindow = new google.maps.InfoWindow();

    courses.forEach(course => {
        if (!course.lat || !course.lng) return;

        // 커스텀 핀 디자인
        const pin = new PinElement({
            background: "#27ae60",
            borderColor: "#ffffff",
            glyph: "⛳",
            glyphColor: "#ffffff",
        });

        const marker = new AdvancedMarkerElement({
            map: map,
            position: { lat: course.lat, lng: course.lng },
            title: course.title,
            content: pin.element,
        });

        marker.addListener("click", () => {
            const content = `
                <div class="infowindow-content">
                    <img src="${course.thumbnail}" alt="">
                    <h3>${course.title}</h3>
                    <p>${course.address}</p>
                    <a href="${course.link}">View Details</a>
                </div>
            `;
            infoWindow.setContent(content);
            infoWindow.open(map, marker);
        });

        markers.push(marker);
    });
}

// 5. 이벤트 리스너 (언어 및 필터)
document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        currentLang = e.target.dataset.lang;
        renderApp();
    });
});

document.querySelectorAll('.theme-button').forEach(btn => {
    btn.addEventListener('click', (e) => {
        document.querySelectorAll('.theme-button').forEach(b => b.classList.remove('active'));
        e.target.classList.add('active');
        currentTheme = e.target.dataset.theme;
        renderApp();
    });
});

// 실행
init();