/**
 * OKOnsen - Global Multi-language Core Logic (EN, KO, JA)
 */

let onsensData =[]; // 전체 원본 온천 데이터
let map;
let markers =[];
let currentInfoWindow = null;
let isMapLoaded = false;

// 상태 관리
let currentLang = localStorage.getItem('preferredLang') || 'en'; // 저장된 언어 불러오기
let currentTheme = 'all';

// [1] 다국어 UI 번역 사전 (온천에 맞게 수정됨)
const i18n = {
    en: {
        viewGuide: "View Details",
        directions: "Directions",
        readMore: "Read More →",
        noResult: "No onsens found matching your criteria.",
        new: "NEW",
    },
    ko: {
        viewGuide: "상세보기",
        directions: "길찾기",
        readMore: "자세히 보기 →",
        noResult: "해당 조건에 맞는 온천이 없습니다.",
        new: "신규",
    },
    ja: {
        viewGuide: "詳細を見る",
        directions: "経路案内",
        readMore: "詳しく見る →",
        noResult: "該当する温泉がありません。",
        new: "新着",
    }
};

// [2] 카테고리 매핑 테이블 (Markdown의 다국어 카테고리를 내부 테마 키값으로 연결)
function getCategoryKey(cat) {
    if (!cat) return 'all';
    const map = {
        // 가족탕 / 개인탕 (Private Bath)
        "Private Bath": "private", "가족탕": "private", "개인탕": "private", "貸切風呂": "private", "家族風呂": "private",
        // 타투 허용 (Tattoo OK)
        "Tattoo OK": "tattoo", "Tattoo Friendly": "tattoo", "타투 허용": "tattoo", "문신 허용": "tattoo", "タトゥーOK": "tattoo",
        // 절경 / 뷰 (Great View)
        "Great View": "view", "절경": "view", "경치": "view", "뷰": "view", "絶景": "view",
        // 럭셔리 / 고급 (Luxury)
        "Luxury": "luxury", "고급 료칸": "luxury", "럭셔리": "luxury", "高級": "luxury",
        // 로컬 / 비탕 (Local)
        "Local": "local", "로컬": "local", "현지인": "local", "ローカル": "local", "秘湯": "local"
    };
    return map[cat] || cat.toLowerCase().trim();
}

// [3] 앱 초기화
document.addEventListener('DOMContentLoaded', () => {
    fetchOnsens();
    initThemeFilters();
    initLangFilters();
    initMap(); 
});

// [4] 데이터 가져오기 (API 엔드포인트 변경됨)
async function fetchOnsens() {
    try {
        const response = await fetch('/api/onsens');
        const data = await response.json();
        
        // 최신순 정렬
        onsensData = data.onsens.sort((a, b) => 
            new Date(b.published) - new Date(a.published)
        );

        if (data.last_updated) {
            const dateEl = document.getElementById('last-updated-date');
            if(dateEl) dateEl.textContent = data.last_updated;
        }

        updateUI(); // 초기 렌더링

    } catch (error) {
        console.error('Error loading data:', error);
    }
}

// [5] 언어 필터 초기화
function initLangFilters() {
    const langBtns = document.querySelectorAll('.lang-btn');
    langBtns.forEach(btn => {
        // 초기 로드 시 활성화 스타일 적용
        if (btn.dataset.lang === currentLang) btn.classList.add('active');

        btn.addEventListener('click', () => {
            langBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentLang = btn.dataset.lang;
            localStorage.setItem('preferredLang', currentLang); // 설정 저장
            updateUI();
        });
    });
}

// [6] 테마 필터 초기화
function initThemeFilters() {
    const buttons = document.querySelectorAll('.theme-button');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentTheme = btn.dataset.theme;
            updateUI();
        });
    });
}

// [7] 통합 UI 업데이트 (언어 + 테마 동시 적용)
function updateUI() {
    // 필터링 로직
    const filtered = onsensData.filter(item => {
        const isCorrectLang = item.lang === currentLang;
        const isCorrectTheme = currentTheme === 'all' || 
            item.categories.some(cat => getCategoryKey(cat) === currentTheme);
        return isCorrectLang && isCorrectTheme;
    });

    updateCategoryCounts(); 
    renderCards(filtered);
    if (isMapLoaded) {
        updateMapMarkers(filtered);
    }

    const totalEl = document.getElementById('total-onsens');
    if(totalEl) totalEl.textContent = filtered.length;
}

// [8] 구글 맵 초기화
async function initMap() {
    const mapEl = document.getElementById('map');
    if (!mapEl) return;

    try {
        const { Map } = await google.maps.importLibrary("maps");
        // 일본 중심 좌표
        const center = { lat: 36.2048, lng: 138.2529 };

        map = new Map(mapEl, {
            zoom: 5,
            center: center,
            mapId: "2938bb3f7f034d78a2dbaf56", // 구글 클라우드 콘솔의 Map ID 유지
            disableDefaultUI: false,
            zoomControl: true,
            streetViewControl: false,
            mapTypeControl: false,
        });

        isMapLoaded = true;
        updateUI();

    } catch (error) {
        console.error("❌ Map Init Error:", error);
    }
}

// [9] 마커 업데이트 (Advanced Markers)
async function updateMapMarkers(data) {
    if (!map) return;
    markers.forEach(m => m.map = null);
    markers =[];
    if (data.length === 0) return;

    const bounds = new google.maps.LatLngBounds();

    try {
        const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");
        const { InfoWindow } = await google.maps.importLibrary("maps");
        const t = i18n[currentLang];

        data.forEach(onsen => {
            const position = { lat: parseFloat(onsen.lat), lng: parseFloat(onsen.lng) };
            
            // 커스텀 마커 아이콘 생성
            const markerIcon = document.createElement('div');
            markerIcon.className = 'marker-icon';

            const marker = new AdvancedMarkerElement({
                map: map,
                position: position,
                title: onsen.title,
                content: markerIcon,
            });

            marker.addListener('click', () => {
                if (currentInfoWindow) currentInfoWindow.close();

                const infoContent = `
                    <div class="infowindow-content">
                        <div style="position:relative;">
                            <img src="${onsen.thumbnail}" alt="${onsen.title}" loading="lazy">
                        </div>
                        <h3>${onsen.title}</h3>
                        <p>📍 ${onsen.address}</p>
                        <div class="info-btn-group">
                            <a href="${onsen.link}" class="info-btn blog-btn">${t.viewGuide}</a>
                            <a href="https://www.google.com/maps/dir/?api=1&destination=${onsen.lat},${onsen.lng}" target="_blank" class="info-btn dir-btn">${t.directions}</a>
                        </div>
                    </div>`;
                
                const infoWindow = new InfoWindow({ content: infoContent, maxWidth: 250 });
                infoWindow.open(map, marker);
                currentInfoWindow = infoWindow;
            });
            markers.push(marker);
            bounds.extend(position);
        });
        map.fitBounds(bounds);
    } catch (e) { console.error("Marker Error:", e); }
}

// [10] 카운트 배지 업데이트 (현재 언어 기준, 온천 카테고리로 변경)
function updateCategoryCounts() {
    const counts = { all: 0, private: 0, tattoo: 0, view: 0, luxury: 0, local: 0 };
    const currentLangData = onsensData.filter(s => s.lang === currentLang);
    counts.all = currentLangData.length;

    currentLangData.forEach(onsen => {
        if(onsen.categories) {
            onsen.categories.forEach(cat => {
                const key = getCategoryKey(cat);
                if (counts.hasOwnProperty(key)) counts[key]++;
            });
        }
    });

    for (const[key, value] of Object.entries(counts)) {
        const badge = document.getElementById(`count-${key}`);
        if (badge) badge.textContent = value;
    }
}

// [11] 리스트 카드 렌더링
function renderCards(data) {
    const listContainer = document.getElementById('onsen-list');
    if(!listContainer) return;
    listContainer.innerHTML = '';
    const t = i18n[currentLang];
    
    if (data.length === 0) {
        listContainer.innerHTML = `<p style="text-align:center; width:100%; color:#666; margin-top:30px;">${t.noResult}</p>`;
        return;
    }

    data.forEach(onsen => {
        const pubDate = new Date(onsen.published);
        const isNew = (new Date() - pubDate) / (1000 * 60 * 60 * 24) <= 14; 

        const card = document.createElement('div');
        card.className = 'onsen-card'; // 클래스명 변경
        
        card.innerHTML = `
            <a href="${onsen.link}" class="card-thumb-link">
                ${isNew ? `<span class="new-badge">${t.new}</span>` : ''}
                <img src="${onsen.thumbnail}" alt="${onsen.title}" class="card-thumb" loading="lazy">
            </a>
            <div class="card-content">
                <div class="card-meta">
                    <span>${onsen.categories.join(', ')}</span> • <span>${onsen.published.replace(/-/g, '.')}</span>
                </div>
                <h3 class="card-title"><a href="${onsen.link}">${onsen.title}</a></h3>
                <p class="card-summary">${onsen.summary}</p>
                <div class="card-footer">
                    <a href="${onsen.link}" class="card-btn">${t.readMore}</a>
                </div>
            </div>`;
        listContainer.appendChild(card);
    });
}