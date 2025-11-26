let map;
let allMarkers = [];
let infoWindow;
let allShrinesData = [];

// 1. 카테고리별 색상 정의 (우선순위 순서대로 배치하는 것이 좋음)
const categoryColors = {
    '재물': '#FBC02D', // Gold
    '연애': '#E91E63', // Pink
    '사랑': '#E91E63',
    '건강': '#2E7D32', // Green
    '학업': '#1565C0', // Blue
    '안전': '#455A64', // BlueGrey
    '성공': '#512DA8', // Purple
    '역사': '#EF6C00', // Orange
    '기타': '#D32F2F'  // Red (기본값)
};

// 2. [핵심] 신사에 가장 적합한 카테고리 색상을 찾는 함수
function findMainCategory(categories) {
    if (!categories || categories.length === 0) return '기타';

    // 정의된 색상 키(재물, 연애 등)를 순서대로 돌면서
    // 신사의 태그 목록에 해당 키워드가 포함되어 있는지 확인
    for (const colorKey of Object.keys(categoryColors)) {
        if (colorKey === '기타') continue; // 기타는 마지막에 처리

        // 신사 태그 중 하나라도 colorKey를 포함하면 당첨 (예: "역사 탐방" -> "역사")
        const match = categories.some(cat => cat.includes(colorKey));
        if (match) {
            return colorKey; // 찾았으면 바로 반환 (우선순위 적용)
        }
    }
    return '기타'; // 맞는게 없으면 빨강
}

function getMarkerIcon(categoryName) {
    // categoryName에 해당하는 색상 가져오기
    let color = categoryColors[categoryName] || categoryColors['기타'];

    return {
        path: "M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z",
        fillColor: color,
        fillOpacity: 1,
        scale: 1.7,       
        strokeColor: "#FFFFFF",
        strokeWeight: 1.5,
        anchor: new google.maps.Point(12, 22)
    };
}

async function initMap() {
    const tokyoCoords = { lat: 35.6895, lng: 139.6917 };
    map = new google.maps.Map(document.getElementById("map"), {
        zoom: 11,
        center: tokyoCoords,
        mapTypeControl: false,
        fullscreenControl: false,
        streetViewControl: false,
        styles: [
            { featureType: "poi", elementType: "labels", stylers: [{ visibility: "off" }] }
        ]
    });

    infoWindow = new google.maps.InfoWindow();

    try {
        const response = await fetch('/api/shrines');
        const jsonData = await response.json();
        allShrinesData = jsonData.shrines ? jsonData.shrines : jsonData;

        if (!Array.isArray(allShrinesData)) return;

        if (jsonData.last_updated) {
            const msgElement = document.getElementById('update-msg');
            if (msgElement) msgElement.textContent = `데이터 업데이트: ${jsonData.last_updated}`;
        }

        addMarkers(allShrinesData);
        renderTop5Shrines(allShrinesData);
        setupFilterButtons();

    } catch (error) {
        console.error("초기화 오류:", error);
    }
}

function addMarkers(shrines) {
    allMarkers.forEach(marker => marker.setMap(null));
    allMarkers = [];

    shrines.forEach((shrine) => {
        if (!shrine.lat || !shrine.lng) return;

        // [변경] 단순히 첫 번째 태그가 아니라, 색상 목록에 있는 '중요 태그'를 우선 추출
        const mainCategoryKey = findMainCategory(shrine.categories);

        const marker = new google.maps.Marker({
            position: { lat: shrine.lat, lng: shrine.lng },
            map: map,
            title: shrine.title,
            icon: getMarkerIcon(mainCategoryKey), // 찾아낸 카테고리 색상 적용
            animation: google.maps.Animation.DROP
        });

        marker.categories = shrine.categories || [];
        // 필터링을 위해 marker 객체에 '대표 카테고리' 정보도 심어둠 (선택사항)
        marker.mainCategoryKey = mainCategoryKey; 

        marker.addListener("click", () => {
            const contentString = `
                <div class="infowindow-content">
                    <img src="${shrine.thumbnail}" alt="${shrine.title}">
                    <h3>${shrine.title}</h3>
                    <p>🏷️ ${shrine.categories.join(', ')}</p>
                    <a href="${shrine.link}" target="_blank">자세히 보기 →</a>
                </div>
            `;
            infoWindow.setContent(contentString);
            infoWindow.open(map, marker);
        });

        allMarkers.push(marker);
    });
}

function renderTop5Shrines(shrines) {
    const listContainer = document.getElementById('shrine-list');
    if (!listContainer) return;

    listContainer.innerHTML = ''; 
    const sortedShrines = [...shrines].sort((a, b) => new Date(b.published) - new Date(a.published));
    const top5 = sortedShrines.slice(0, 5);

    top5.forEach(shrine => {
        const categoryTag = shrine.categories && shrine.categories.length > 0 
            ? ` • <span>🏷️ ${shrine.categories[0]}</span>` 
            : '';

        const cardHTML = `
            <div class="shrine-card">
                <a href="${shrine.link}" target="_blank" class="card-thumb-link">
                    <img src="${shrine.thumbnail}" alt="${shrine.title}" class="card-thumb" loading="lazy">
                </a>
                <div class="card-content">
                    <h3 class="card-title">
                        <a href="${shrine.link}" target="_blank">${shrine.title}</a>
                    </h3>
                    <div class="card-meta">
                        <span>📅 ${shrine.published}</span>
                        ${categoryTag}
                    </div>
                    <p class="card-summary">${shrine.summary}</p>
                    <a href="${shrine.link}" target="_blank" class="card-btn">더 보기 →</a>
                </div>
            </div>
        `;
        listContainer.insertAdjacentHTML('beforeend', cardHTML);
    });
}

function setupFilterButtons() {
    const buttons = document.querySelectorAll('.theme-button');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            const selectedTheme = btn.getAttribute('data-theme');
            filterMapMarkers(selectedTheme);
        });
    });
}

function filterMapMarkers(theme) {
    const themeMap = {
        'wealth': '재물', 'love': '연애', 'health': '건강',
        'study': '학업', 'safety': '안전', 'success': '성공', 'history': '역사'
    };

    const targetCategory = themeMap[theme];

    allMarkers.forEach(marker => {
        if (theme === 'all') {
            marker.setVisible(true);
        } else {
            // 태그 배열 안에 해당 키워드가 포함되어 있는지 확인
            const hasCategory = marker.categories.some(cat => cat.includes(targetCategory));
            marker.setVisible(hasCategory);
        }
    });
}