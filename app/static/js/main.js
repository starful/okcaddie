// main.js - JinjaMap Core Logic (English Version)

let shrinesData = [];
let map;
let markers = [];
let currentInfoWindow = null;

// [1] Initialize
document.addEventListener('DOMContentLoaded', () => {
    fetchShrines();
    initThemeFilters();
    initSearch(); // Initialize search input
    initOmikuji();
});

// [2] Fetch Data
async function fetchShrines() {
    try {
        const response = await fetch('/api/shrines');
        const data = await response.json();
        
        // Sort by Date (Newest first)
        shrinesData = data.shrines.sort((a, b) => 
            new Date(b.published) - new Date(a.published)
        );

        // Update Status Bar
        if (data.last_updated) {
            const dateEl = document.getElementById('last-updated-date');
            if(dateEl) dateEl.textContent = data.last_updated;
        }
        if (data.shrines) {
            const countEl = document.getElementById('total-shrines');
            if(countEl) countEl.textContent = data.shrines.length;
        }

        // Update Category Badges
        updateCategoryCounts();

        renderCards(shrinesData);
        initMap(); // Initialize map after data load
    } catch (error) {
        console.error('Error loading data:', error);
    }
}

// [NEW] Calculate & Update Badge Counts
function updateCategoryCounts() {
    // Initialize counts
    const counts = {
        all: shrinesData.length,
        wealth: 0,
        love: 0,
        health: 0,
        study: 0,
        safety: 0,
        success: 0,
        history: 0
    };

    // Count items
    shrinesData.forEach(shrine => {
        shrine.categories.forEach(cat => {
            const key = cat.toLowerCase(); // 'Wealth' -> 'wealth'
            if (counts.hasOwnProperty(key)) {
                counts[key]++;
            }
        });
    });

    // Update DOM elements
    for (const [key, value] of Object.entries(counts)) {
        const badge = document.getElementById(`count-${key}`);
        if (badge) {
            badge.textContent = value;
        }
    }
}

// [3] Render Cards
function renderCards(data) {
    const listContainer = document.getElementById('shrine-list');
    listContainer.innerHTML = '';

    if (data.length === 0) {
        listContainer.innerHTML = '<p style="text-align:center; width:100%; color:#666; margin-top:30px;">No shrines found matching your criteria.</p>';
        return;
    }

    data.forEach(shrine => {
        // Calculate 'NEW' badge (within 7 days)
        const pubDate = new Date(shrine.published);
        const now = new Date();
        const diffDays = Math.ceil((now - pubDate) / (1000 * 60 * 60 * 24));
        const isNew = diffDays <= 7;

        const card = document.createElement('div');
        card.className = 'shrine-card';
        card.innerHTML = `
            <a href="${shrine.link}" class="card-thumb-link">
                ${isNew ? '<span class="new-badge">NEW</span>' : ''}
                <img src="${shrine.thumbnail}" alt="${shrine.title}" class="card-thumb" loading="lazy">
            </a>
            <div class="card-content">
                <div class="card-meta">
                    <span>${shrine.categories.join(', ')}</span> • <span>${shrine.published}</span>
                </div>
                <h3 class="card-title">
                    <a href="${shrine.link}">${shrine.title}</a>
                </h3>
                <p class="card-summary">${shrine.summary}</p>
                <div class="card-footer">
                    <a href="${shrine.link}" class="card-btn">Read More &rarr;</a>
                </div>
            </div>
        `;
        listContainer.appendChild(card);
    });
}

// [4] Search & Filtering
function initSearch() {
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', (e) => {
            const keyword = e.target.value.toLowerCase();
            filterData(keyword, getCurrentTheme());
        });
    }
}

function initThemeFilters() {
    const buttons = document.querySelectorAll('.theme-button');
    buttons.forEach(btn => {
        btn.addEventListener('click', () => {
            buttons.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            const theme = btn.dataset.theme; 
            filterData('', theme);
        });
    });
}

function getCurrentTheme() {
    const activeBtn = document.querySelector('.theme-button.active');
    return activeBtn ? activeBtn.dataset.theme : 'all';
}

function filterData(keyword, theme) {
    let filtered = shrinesData;
    
    if (theme !== 'all') {
        filtered = filtered.filter(item => 
            item.categories.some(cat => cat.toLowerCase() === theme.toLowerCase())
        );
    }

    if (keyword) {
        filtered = filtered.filter(item => 
            item.title.toLowerCase().includes(keyword) ||
            item.address.toLowerCase().includes(keyword) ||
            (item.tags && item.tags.some(tag => tag.toLowerCase().includes(keyword)))
        );
    }

    renderCards(filtered);
    updateMapMarkers(filtered);
}

// [5] Google Maps
function initMap() {
    const mapEl = document.getElementById('map');
    if (!mapEl) return;

    const center = { lat: 35.6895, lng: 139.6917 };
    
    map = new google.maps.Map(mapEl, {
        zoom: 11,
        center: center,
        mapId: "DEMO_MAP_ID",
        disableDefaultUI: false,
        zoomControl: true,
        streetViewControl: false
    });

    updateMapMarkers(shrinesData);
}

// [6] Update Markers
async function updateMapMarkers(data) {
    markers.forEach(m => m.map = null);
    markers = [];

    const { AdvancedMarkerElement } = await google.maps.importLibrary("marker");

    data.forEach(shrine => {
        const markerIcon = document.createElement('div');
        markerIcon.className = 'marker-icon';
        if (shrine.thumbnail) {
            markerIcon.style.backgroundImage = `url(${shrine.thumbnail})`;
            markerIcon.style.backgroundSize = 'cover';
        }

        const marker = new AdvancedMarkerElement({
            map: map,
            position: { lat: parseFloat(shrine.lat), lng: parseFloat(shrine.lng) },
            title: shrine.title,
            content: markerIcon
        });

        marker.addListener('click', () => {
            if (currentInfoWindow) currentInfoWindow.close();

            const infoContent = `
                <div class="infowindow-content">
                    <img src="${shrine.thumbnail}" alt="${shrine.title}">
                    <h3>${shrine.title}</h3>
                    <p>📍 ${shrine.address}</p>
                    <div class="info-btn-group">
                        <a href="${shrine.link}" class="info-btn blog-btn">View Guide</a>
                        <a href="https://www.google.com/maps/dir/?api=1&destination=${shrine.lat},${shrine.lng}" target="_blank" class="info-btn dir-btn">Directions</a>
                    </div>
                </div>
            `;

            const infoWindow = new google.maps.InfoWindow({
                content: infoContent
            });

            infoWindow.open(map, marker);
            currentInfoWindow = infoWindow;
        });

        markers.push(marker);
    });
}

// [7] Omikuji (Fortune)
function initOmikuji() {
    const btn = document.getElementById('omikuji-btn');
    const modal = document.getElementById('omikuji-modal');
    const close = document.querySelector('.close-modal');
    const drawBtn = document.getElementById('draw-btn');
    const step1 = document.getElementById('omikuji-step1');
    const step2 = document.getElementById('omikuji-step2');

    if(!btn) return;

    btn.addEventListener('click', () => {
        modal.style.display = 'flex';
        step1.style.display = 'block';
        step2.style.display = 'none';
    });

    close.addEventListener('click', () => {
        modal.style.display = 'none';
    });

    drawBtn.addEventListener('click', () => {
        const box = document.getElementById('shaking-box');
        box.style.animation = 'shake 0.5s infinite';
        
        setTimeout(() => {
            box.style.animation = 'none';
            showResult();
        }, 1500);
    });

    function showResult() {
        const randomShrine = shrinesData[Math.floor(Math.random() * shrinesData.length)];
        const fortuneTypes = ['Great Blessing (Dai-kichi)', 'Blessing (Kichi)', 'Middle Blessing (Chu-kichi)', 'Small Blessing (Sho-kichi)'];
        const randomFortune = fortuneTypes[Math.floor(Math.random() * fortuneTypes.length)];

        step1.style.display = 'none';
        step2.style.display = 'block';

        document.getElementById('result-title').innerText = randomFortune;
        document.getElementById('result-desc').innerText = `Your lucky spot is:\n${randomShrine.title}`;
        
        const goBtn = document.getElementById('go-map-btn');
        goBtn.innerText = "Go to Shrine";
        goBtn.onclick = () => {
            window.location.href = randomShrine.link;
        };

        if (typeof confetti === 'function') {
            confetti({
                particleCount: 100,
                spread: 70,
                origin: { y: 0.6 }
            });
        }
    }
}

// Add CSS Animation
const style = document.createElement('style');
style.innerHTML = `
@keyframes shake {
  0% { transform: translate(1px, 1px) rotate(0deg); }
  10% { transform: translate(-1px, -2px) rotate(-1deg); }
  20% { transform: translate(-3px, 0px) rotate(1deg); }
  30% { transform: translate(3px, 2px) rotate(0deg); }
  40% { transform: translate(1px, -1px) rotate(1deg); }
  50% { transform: translate(-1px, 2px) rotate(-1deg); }
  60% { transform: translate(-3px, 1px) rotate(0deg); }
  70% { transform: translate(3px, 1px) rotate(-1deg); }
  80% { transform: translate(-1px, -1px) rotate(1deg); }
  90% { transform: translate(1px, 2px) rotate(0deg); }
  100% { transform: translate(1px, -2px) rotate(-1deg); }
}`;
document.head.appendChild(style);