// map.js
let map;
let markers = []; // 마커들을 담을 배열

// 1. 카테고리 매핑 (한글 태그 -> 영어 코드)
const categoryMap = {
    "재물": "wealth", "금전": "wealth", "사업": "wealth", "로또": "wealth",
    "사랑": "love", "연애": "love", "인연": "love", "결혼": "love",
    "건강": "health", "치유": "health", "장수": "health",
    "학업": "study", "합격": "study", "시험": "study",
    "안전": "safety", "교통안전": "safety", "액운": "safety",
    "성공": "success", "승진": "success", "목표": "success",
    "휴식": "relax", "힐링": "relax", "여행": "relax",
    "역사": "history", "전통": "history", "관광": "history"
    // (가정, 예술은 삭제됨)
};

// 2. 구글 맵 초기화
async function initMap() {
    console.log("Google Maps initMap 시작됨!");

    const { Map } = await google.maps.importLibrary("maps");
    const { AdvancedMarkerElement, PinElement } = await google.maps.importLibrary("marker");

    // 기본 중심 좌표 (데이터가 로드되면 자동으로 경계가 조절됩니다)
    const initialCenter = { lat: 35.6895, lng: 139.6917 }; // 도쿄

    map = new Map(document.getElementById("map"), {
        zoom: 10,
        center: initialCenter,
        mapId: "2938bb3f7f034d78a2dbaf56",
        mapTypeControl: false,
        streetViewControl: false,
        gestureHandling: "cooperative" // 모바일 스크롤 개선
    });

    fetchBlogPosts(AdvancedMarkerElement, PinElement);
    setupFilterButtons();
}

// 3. 데이터 가져오기
async function fetchBlogPosts(AdvancedMarkerElement, PinElement) {
    const API_ENDPOINT = "/api/shrines";
    try {
        const response = await fetch(API_ENDPOINT);
        const posts = await response.json();
        
        if (posts.length === 0) {
            console.log("데이터가 없습니다.");
            return;
        }

        processBlogData(posts, AdvancedMarkerElement, PinElement);
    } catch (error) {
        console.error("API 호출 실패:", error);
    }
}

// 4. 데이터 처리 및 마커 생성 (Geocoding API 호출 제거됨)
function processBlogData(posts, AdvancedMarkerElement, PinElement) {
    const bounds = new google.maps.LatLngBounds(); // 모든 마커를 포함할 범위

    for (const post of posts) {
        // [중요] 백엔드에서 이미 변환된 좌표(lat, lng)가 있는 경우에만 마커 생성
        if (post.lat && post.lng) {
            
            // 카테고리 결정 로직
            let matchedTheme = 'history'; // 기본값
            if (post.categories && post.categories.length > 0) {
                for (let cat of post.categories) {
                    if (categoryMap[cat]) {
                        matchedTheme = categoryMap[cat];
                        break;
                    }
                }
            }

            // 마커 데이터 구성
            const shrineData = {
                name: post.title,
                lat: post.lat,
                lng: post.lng,
                theme: matchedTheme,
                link: post.link,
                address: post.address,
                thumbnail: post.thumbnail
            };

            createMarker(shrineData, AdvancedMarkerElement, PinElement);
            
            // 지도 범위 확장
            bounds.extend({ lat: post.lat, lng: post.lng });
        }
    }

    // 모든 마커가 보이도록 지도 중심/줌 자동 조절
    if (!bounds.isEmpty()) {
        map.fitBounds(bounds);
    }
}

// 5. 마커 생성 함수
function createMarker(shrine, AdvancedMarkerElement, PinElement) {
    // 테마별 색상
    const colors = {
        wealth: "#FFD700",  // 재물 (황금색)
        love: "#FF4081",    // 사랑 (핫핑크)
        health: "#4CAF50",  // 건강 (초록)
        study: "#2196F3",   // 학업 (파랑)
        safety: "#607D8B",  // 안전 (청회색)
        success: "#673AB7", // 성공 (보라)
        relax: "#00BCD4",   // 휴식 (하늘색)
        history: "#795548"  // 역사 (갈색)
    };
    
    const markerColor = colors[shrine.theme] || colors['history'];

    const pin = new PinElement({
        background: markerColor,
        borderColor: "#ffffff",
        glyphColor: "#ffffff"
    });

    const marker = new AdvancedMarkerElement({
        map: map,
        position: { lat: shrine.lat, lng: shrine.lng },
        title: shrine.name,
        content: pin.element
    });

    marker.category = shrine.theme; // 필터링용 속성 추가

    // 길찾기 URL 생성
    const directionsUrl = `https://www.google.com/maps/dir/?api=1&destination=${shrine.lat},${shrine.lng}`;

    // 인포윈도우 (팝업 내용) - [수정됨] 썸네일 경로 에러 처리 및 길찾기 버튼 추가
    const contentString = `
        <div class="infowindow-content">
            <!-- 이미지 (에러시 로고 표시) -->
            <img src="${shrine.thumbnail}" 
                 alt="${shrine.name}" 
                 onerror="this.src='assets/images/JinjaMapLogo_Horizontal.png'">
            
            <h3>${shrine.name}</h3>
            <p style="font-size:12px; color:#666; margin-bottom:5px;">${shrine.address}</p>
            
            <p style="margin-bottom:8px;">
                <span style="display:inline-block; padding:2px 6px; background:${markerColor}; color:#fff; border-radius:10px; font-size:11px;">
                    ${getKoreanThemeName(shrine.theme)}
                </span>
            </p>

            <div style="display:flex; gap:5px;">
                <a href="${shrine.link}" target="_blank" style="flex:1; text-align:center; padding:6px 0; background:#333; color:#fff; text-decoration:none; border-radius:4px; font-size:12px;">블로그 보기</a>
                <a href="${directionsUrl}" target="_blank" style="flex:1; text-align:center; padding:6px 0; background:#4285F4; color:#fff; text-decoration:none; border-radius:4px; font-size:12px;">🗺️ 길찾기</a>
            </div>
        </div>
    `;

    const infowindow = new google.maps.InfoWindow({
        content: contentString
    });

    marker.addListener("click", () => {
        // 다른 열린 창이 있다면 닫기 (선택사항)
        // currentInfoWindow?.close(); 
        infowindow.open(map, marker);
        // currentInfoWindow = infowindow;
    });

    markers.push(marker);
}

// 한글 테마명 변환
function getKoreanThemeName(theme) {
    const names = {
        wealth: "재물", love: "사랑", health: "건강",
        study: "학업", safety: "안전",
        success: "성공", relax: "휴식", history: "역사"
    };
    return names[theme] || "역사";
}

// 6. 필터 버튼 로직
function setupFilterButtons() {
    const buttons = document.querySelectorAll('.theme-button');
    buttons.forEach(button => {
        button.addEventListener('click', () => {
            // 버튼 활성화 스타일 처리
            buttons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            const selectedTheme = button.getAttribute('data-theme');
            
            // 마커 보이기/숨기기
            markers.forEach(marker => {
                if (selectedTheme === 'all' || marker.category === selectedTheme) {
                    marker.map = map; // 지도에 표시
                } else {
                    marker.map = null; // 지도에서 제거
                }
            });
        });
    });
}

window.initMap = initMap;