// 전역 변수 선언
let map;
let allMarkers = [];
let infoWindow;
let allShrinesData = [];

/**
 * [핵심] 한글 카테고리를 웹사이트의 영어 테마 키워드로 매핑하는 객체.
 * 데이터('사랑')와 UI('love') 사이의 다리 역할을 합니다.
 * 새로운 카테고리가 생기면 여기만 추가하면 됩니다.
 */
const CATEGORY_THEME_MAP = {
    '재물': 'wealth',
    '사랑': 'love',
    '연애': 'love', // '연애'도 'love' 테마로 취급
    '건강': 'health',
    '학업': 'study',
    '안전': 'safety',
    '성공': 'success',
    '역사': 'history',
};

// 테마별 색상 정의 (마커 테두리용)
const THEME_COLORS = {
    'wealth': '#FBC02D',
    'love': '#E91E63',
    'health': '#2E7D32',
    'study': '#1565C0',
    'safety': '#455A64',
    'success': '#512DA8',
    'history': '#EF6C00',
    'default': '#757575' // 기본값
};

/**
 * 지도 초기화 함수
 */
async function initMap() {
    const tokyoCoords = { lat: 35.6895, lng: 139.6917 };

    map = new google.maps.Map(document.getElementById("map"), {
        zoom: 11,
        center: tokyoCoords,
        mapId: "2938bb3f7f034d78", // 실제 서비스용 Map ID로 교체
        mapTypeControl: false,
        fullscreenControl: false,
        streetViewControl: false,
        gestureHandling: 'greedy'
    });

    infoWindow = new google.maps.InfoWindow();
    addLocationButton();

    try {
        const response = await fetch('/api/shrines');
        const jsonData = await response.json();
        
        allShrinesData = jsonData.shrines || []; // 데이터가 없어도 빈 배열로 초기화

        if (jsonData.last_updated) {
            document.getElementById('update-msg').textContent = `데이터 업데이트: ${jsonData.last_updated}`;
        }

        // 데이터 로딩 후 UI 관련 함수들 순차 실행
        addMarkers(allShrinesData);
        renderRecentShrines(allShrinesData.slice(0, 4)); // 최신 4개만 렌더링
        updateFilterButtonCounts(allShrinesData);
        setupFilterButtons();

    } catch (error) {
        console.error("데이터 로딩 및 지도 초기화 오류:", error);
        document.getElementById('update-msg').textContent = '데이터를 불러오는 데 실패했습니다.';
    }
}

/**
 * 모든 신사 데이터를 기반으로 마커를 지도에 추가하는 함수
 */
function addMarkers(shrines) {
    shrines.forEach((shrine) => {
        if (!shrine.lat || !shrine.lng) return;

        const mainTheme = findMainTheme(shrine.categories);
        const borderColor = THEME_COLORS[mainTheme] || THEME_COLORS['default'];

        // [수정] pinImg -> markerContent 로 이름 변경 및 내용 수정
        const markerContent = document.createElement("div");
        // [수정] JS에서 src를 설정하는 대신, CSS가 배경 이미지를 처리하도록 클래스만 지정
        markerContent.className = 'marker-icon';
        markerContent.style.borderColor = borderColor;

        const marker = new google.maps.marker.AdvancedMarkerElement({
            map: map,
            position: { lat: shrine.lat, lng: shrine.lng },
            title: shrine.title,
            // [수정] content에 새로 만든 div 요소를 전달
            content: markerContent,
        });

        // 각 마커에 해당 신사의 테마 정보를 저장 (필터링에 사용)
        marker.themes = getThemesFromCategories(shrine.categories);

        marker.addListener("click", () => showInfoWindow(marker, shrine));
        allMarkers.push(marker);
    });
}

/**
 * 마커 클릭 시 정보창(InfoWindow)을 표시하는 함수
 */
function showInfoWindow(marker, shrine) {
    const directionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${shrine.lat},${shrine.lng}&travelmode=walking`;
    const copyText = shrine.address || shrine.title;

    const contentString = `
        <div class="infowindow-content">
            <img src="${shrine.thumbnail}" alt="${shrine.title}" loading="lazy">
            <h3>${shrine.title}</h3>
            <p>🏷️ ${shrine.categories.join(', ')}</p>
            <div class="info-btn-group">
                <a href="${directionsUrl}" target="_blank" class="info-btn dir-btn">📍 길찾기</a>
                <a href="${shrine.link}" target="_blank" class="info-btn blog-btn">블로그</a>
                <button onclick="copyToClipboard('${copyText}')" class="info-btn copy-btn" title="주소 복사">📋</button>
            </div>
        </div>
    `;
    infoWindow.setContent(contentString);
    infoWindow.open(map, marker);
}

/**
 * 필터 버튼의 카운트를 업데이트하는 함수
 */
function updateFilterButtonCounts(shrines) {
    const counts = { all: shrines.length };
    // 모든 테마 키를 0으로 초기화
    Object.values(CATEGORY_THEME_MAP).forEach(theme => counts[theme] = 0);

    shrines.forEach(shrine => {
        const themes = getThemesFromCategories(shrine.categories);
        // 중복 카운트를 방지하기 위해 Set 사용
        new Set(themes).forEach(theme => {
            if (counts.hasOwnProperty(theme)) {
                counts[theme]++;
            }
        });
    });

    document.querySelectorAll('.theme-button').forEach(btn => {
        const theme = btn.dataset.theme;
        const count = counts[theme] || 0;
        const originalText = btn.textContent.split('(')[0].trim();
        btn.textContent = `${originalText} (${count})`;
    });
}

/**
 * 테마에 따라 지도 마커를 필터링하는 함수
 */
function filterMapMarkers(selectedTheme) {
    allMarkers.forEach(marker => {
        const isVisible = (selectedTheme === 'all' || marker.themes.includes(selectedTheme));
        marker.map = isVisible ? map : null;
    });
}

/**
 * 필터 버튼에 클릭 이벤트를 설정하는 함수
 */
function setupFilterButtons() {
    const buttons = document.querySelectorAll('.theme-button');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            filterMapMarkers(btn.dataset.theme);
        });
    });
}

/**
 * 최신 신사 탐방기 목록을 렌더링하는 함수
 */
function renderRecentShrines(shrines) {
    const listContainer = document.getElementById('shrine-list');
    if (!listContainer) return;
    listContainer.innerHTML = shrines.map(shrine => {
        const categoryTag = shrine.categories?.[0] ? `• <span>🏷️ ${shrine.categories[0]}</span>` : '';
        return `
            <div class="shrine-card">
                <a href="${shrine.link}" target="_blank" class="card-thumb-link">
                    <img src="${shrine.thumbnail}" alt="${shrine.title}" class="card-thumb" loading="lazy">
                </a>
                <div class="card-content">
                    <h3 class="card-title"><a href="${shrine.link}" target="_blank">${shrine.title}</a></h3>
                    <div class="card-meta"><span>📅 ${shrine.published}</span>${categoryTag}</div>
                    <p class="card-summary">${shrine.summary}</p>
                    <a href="${shrine.link}" target="_blank" class="card-btn">더 보기 →</a>
                </div>
            </div>
        `;
    }).join('');
}


// --- 유틸리티 함수들 ---

/**
 * 신사의 한글 카테고리 배열을 영어 테마 배열로 변환하는 함수
 * @param {string[]} categories - 예: ['사랑', '일본신사']
 * @returns {string[]} - 예: ['love']
 */
function getThemesFromCategories(categories = []) {
    return categories.map(cat => CATEGORY_THEME_MAP[cat]).filter(Boolean); // map 후 undefined 값 제거
}

/**
 * 신사의 대표 테마를 찾아 반환하는 함수 (마커 테두리 색상 결정용)
 */
function findMainTheme(categories = []) {
    for (const cat of categories) {
        const theme = CATEGORY_THEME_MAP[cat];
        if (theme) return theme;
    }
    return 'default';
}

/**
 * 주소를 클립보드에 복사하는 함수
 */
window.copyToClipboard = function(text) {
    navigator.clipboard.writeText(text).then(() => {
        alert("📋 주소가 복사되었습니다!\n" + text);
    }).catch(err => {
        console.error('클립보드 복사 실패:', err);
        alert('주소 복사에 실패했습니다.');
    });
};

/**
 * 지도에 '내 위치 찾기' 버튼을 추가하는 함수
 */
function addLocationButton() {
    const locationButton = document.createElement("button");
    locationButton.innerHTML = "🎯 내 위치";
    locationButton.className = "location-button"; // CSS로 스타일 관리
    map.controls[google.maps.ControlPosition.RIGHT_BOTTOM].push(locationButton);

    locationButton.addEventListener("click", () => {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                (position) => {
                    const pos = { lat: position.coords.latitude, lng: position.coords.longitude };
                    new google.maps.marker.AdvancedMarkerElement({ map, position, title: "내 위치" });
                    map.setCenter(pos);
                    map.setZoom(14);
                },
                () => alert("위치 정보를 가져올 수 없습니다.")
            );
        } else {
            alert("브라우저가 위치 정보를 지원하지 않습니다.");
        }
    });
}

// --- 오미쿠지 로직 (이하 수정 없음) ---
const omikujiResults = [
    { title: "대길 (大吉)", desc: "금전운이 폭발하는 날입니다!💰<br>지금 당장 복권이라도 사야 할 기세!", theme: "wealth", btnText: "💰 재물운 신사 지도 보기", color: "#FBC02D" },
    { title: "중길 (中吉)", desc: "마음이 설레는 인연이 다가옵니다.💘<br>사랑을 쟁취할 준비 되셨나요?", theme: "love", btnText: "💘 연애운 신사 지도 보기", color: "#E91E63" },
    { title: "소길 (小吉)", desc: "건강이 최고입니다.🌿<br>몸과 마음을 힐링하는 시간이 필요해요.", theme: "health", btnText: "🌿 건강기원 신사 지도 보기", color: "#2E7D32" },
    { title: "길 (吉)", desc: "노력한 만큼 성과가 나오는 날!📚<br>학업이나 승진에 좋은 기운이 있어요.", theme: "study", btnText: "🎓 학업/성공 신사 지도 보기", color: "#1565C0" },
    { title: "흉 (凶)", desc: "조금 조심해야 할 시기입니다.🚧<br>신사에서 액운을 씻어내고 보호받으세요!", theme: "safety", btnText: "🛡️ 액막이/안전 신사 지도 보기", color: "#455A64" }
];

document.addEventListener('DOMContentLoaded', () => {
    const modal = document.getElementById('omikuji-modal');
    if (!modal) return; // 모달이 없으면 실행 중지
    const openBtn = document.getElementById('omikuji-btn');
    const closeBtn = document.querySelector('.close-modal');
    const drawBtn = document.getElementById('draw-btn');
    const step1 = document.getElementById('omikuji-step1');
    const step2 = document.getElementById('omikuji-step2');
    const boxImg = document.getElementById('shaking-box');

    openBtn.addEventListener('click', () => {
        modal.style.display = 'flex';
        step1.style.display = 'block';
        step2.style.display = 'none';
        boxImg.classList.remove('shake'); 
    });

    closeBtn.addEventListener('click', () => modal.style.display = 'none');
    window.addEventListener('click', (e) => { if (e.target === modal) modal.style.display = 'none'; });

    drawBtn.addEventListener('click', () => {
        boxImg.classList.add('shake');
        
        setTimeout(() => {
            boxImg.classList.remove('shake');
            
            if (typeof confetti === 'function') {
                confetti({ particleCount: 150, spread: 70, origin: { y: 0.6 }, colors: ['#FBC02D', '#E91E63', '#ffffff'] });
            }

            const randomResult = omikujiResults[Math.floor(Math.random() * omikujiResults.length)];
            
            document.getElementById('result-title').textContent = randomResult.title;
            document.getElementById('result-title').style.color = randomResult.color;
            document.getElementById('result-desc').innerHTML = randomResult.desc;
            
            const goMapBtn = document.getElementById('go-map-btn');
            goMapBtn.textContent = randomResult.btnText;
            goMapBtn.style.backgroundColor = randomResult.color;
            
            goMapBtn.onclick = () => {
                document.querySelectorAll('.theme-button').forEach(b => {
                    b.classList.remove('active');
                    if(b.dataset.theme === randomResult.theme) {
                        b.classList.add('active');
                    }
                });
                filterMapMarkers(randomResult.theme);
                modal.style.display = 'none';
                
                document.getElementById("map").scrollIntoView({ behavior: "smooth", block: "center" });
            };

            step1.style.display = 'none';
            step2.style.display = 'block';
            
        }, 1000);
    });
});