document.addEventListener('DOMContentLoaded', function () {

    // ── Disclaimer ────────────────────────────────────────────────────────────
    const disclaimerModal = document.getElementById('disclaimer-modal');
    const acceptBtn = document.getElementById('accept-disclaimer');

    if (localStorage.getItem('disclaimerAccepted') === 'true') {
        disclaimerModal.style.display = 'none';
    } else {
        disclaimerModal.style.display = 'block';
        const mapEl = document.getElementById('map');
        if (mapEl) mapEl.style.pointerEvents = 'none';
    }

    acceptBtn.addEventListener('click', function () {
        localStorage.setItem('disclaimerAccepted', 'true');
        disclaimerModal.style.display = 'none';
        const mapEl = document.getElementById('map');
        if (mapEl) mapEl.style.pointerEvents = 'auto';
    });

    // ── Map init ──────────────────────────────────────────────────────────────
    const map = L.map('map').setView([31.7683, 35.2137], 8);
    window.map = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(map);

    // ── View mode: 'price' | 'logo' ───────────────────────────────────────────
    let viewMode = 'price';

    // ── Chain logos ───────────────────────────────────────────────────────────
    const chainLogos = {
        'רמי לוי': 'ramiLevi.png',
        'שופרסל': 'shufersal.png',
        'ויקטורי': 'victory.png',
        'יוחננוף': 'yohananof.png',
        'מחסני השוק': 'mahsaneiHashuk.png',
        'טיב טעם': 'tivTaam.png',
        'אושר עד': 'osherAd.png',
        'קרפור': 'carrefour.png'
    };
    const defaultLogo = 'lobby99 water.png';

    function getChainLogo(chainname) {
        if (chainname && chainLogos[chainname]) return chainLogos[chainname];
        if (chainname) {
            for (const [key, value] of Object.entries(chainLogos)) {
                if (chainname.includes(key)) return value;
            }
        }
        return defaultLogo;
    }

    // ── Price colour helpers ───────────────────────────────────────────────────
    function getPriceColor(priceDiff) {
        if (priceDiff <= -8) return '#006400';
        if (priceDiff <= -3) return '#32CD32';
        if (priceDiff <= 3)  return '#FFFF00';
        if (priceDiff <= 8)  return '#FF8C00';
        return '#FF0000';
    }

    function getPriceClass(priceDiff) {
        if (priceDiff <= -8) return 'price-dark-green';
        if (priceDiff <= -3) return 'price-light-green';
        if (priceDiff <= 3)  return 'price-neutral';
        if (priceDiff <= 8)  return 'price-orange';
        return 'price-higher';
    }

    function getPriceLabel(priceDiff) {
        const abs = Math.abs(priceDiff).toFixed(1);
        const sign = priceDiff < 0 ? '-' : priceDiff > 0 ? '+' : '';
        if (priceDiff <= -8) return `${sign}${abs}% (מחיר נמוך מאוד מהממוצע)`;
        if (priceDiff <= -3) return `${sign}${abs}% (מחיר נמוך מהממוצע)`;
        if (priceDiff <= 3)  return `${sign}${abs}% (דומה לממוצע)`;
        if (priceDiff <= 8)  return `+${abs}% (מחיר גבוה מהממוצע)`;
        return `+${abs}% (מחיר גבוה מאוד מהממוצע)`;
    }

    function getDiffClass(priceDiff) {
        if (priceDiff <= -8) return 'diff-dark-green';
        if (priceDiff <= -3) return 'diff-light-green';
        if (priceDiff <= 3)  return 'diff-neutral';
        if (priceDiff <= 8)  return 'diff-orange';
        return 'diff-red';
    }

    // ── Marker cluster group ──────────────────────────────────────────────────
    const markers = L.markerClusterGroup({
        disableClusteringAtZoom: 15,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        iconCreateFunction: function (cluster) {
            const childMarkers = cluster.getAllChildMarkers();
            let total = 0, count = 0;
            childMarkers.forEach(function (m) {
                const pd = m.options.priceDiff;
                if (pd !== undefined && !isNaN(pd)) { total += pd; count++; }
            });
            const avg = count > 0 ? total / count : 0;

            if (viewMode === 'logo') {
                return new L.DivIcon({
                    html: '<div><span>' + cluster.getChildCount() + '</span></div>',
                    className: 'marker-cluster marker-cluster-logo',
                    iconSize: new L.Point(40, 40)
                });
            }

            let cls;
            if (avg <= -8)      cls = 'marker-cluster-dark-green';
            else if (avg <= -3) cls = 'marker-cluster-light-green';
            else if (avg <= 3)  cls = 'marker-cluster-yellow';
            else if (avg <= 8)  cls = 'marker-cluster-orange';
            else                cls = 'marker-cluster-red';

            return new L.DivIcon({
                html: '<div><span>' + cluster.getChildCount() + '</span></div>',
                className: 'marker-cluster ' + cls,
                iconSize: new L.Point(40, 40)
            });
        }
    });
    window.markers = markers;

    // ── Geolocation ───────────────────────────────────────────────────────────
    window.centerMapOnUserLocation = function () {
        if (!('geolocation' in navigator)) { fitAll(); return; }
        navigator.geolocation.getCurrentPosition(
            function (pos) {
                map.setView([pos.coords.latitude, pos.coords.longitude], 12);
                const icon = L.divIcon({
                    className: 'user-location-marker',
                    html: '<div style="background:#4285F4;width:16px;height:16px;border-radius:50%;border:3px solid white;box-shadow:0 0 4px rgba(0,0,0,.3)"></div>',
                    iconSize: [16, 16], iconAnchor: [8, 8]
                });
                L.marker([pos.coords.latitude, pos.coords.longitude], { icon })
                    .addTo(map).bindPopup('המיקום שלך').openPopup();
            },
            function () { fitAll(); },
            { enableHighAccuracy: true, timeout: 5000, maximumAge: 0 }
        );
    };

    function fitAll() {
        if (markers.getLayers().length > 0)
            map.fitBounds(markers.getBounds(), { padding: [50, 50] });
    }

    // ── State ─────────────────────────────────────────────────────────────────
    let storesData = [];
    let activeChains = new Set();
    let activeSubchains = new Set();
    let priceDiffMax = 20;
    let tableBuilt = false;
    let sortCol = 'average_price_diff';
    let sortDir = 1;
    let tableSearchTerm = '';

    const storeDetails = document.getElementById('store-details');

    // ── Load GeoJSON ──────────────────────────────────────────────────────────
    fetch('data/stores.geojson')
        .then(r => r.json())
        .then(data => {
            storesData = data.features;
            buildFilters(storesData);
            addMarkersToMap(storesData);
        })
        .catch(err => {
            console.error('Error loading GeoJSON:', err);
            document.getElementById('kashi-table-container').innerHTML =
                '<p class="table-empty">שגיאה בטעינת נתוני המפה. אנא נסה שוב מאוחר יותר.</p>';
        });

    // ── Build chain / subchain filter UI ─────────────────────────────────────
    function buildFilters(data) {
        const chainMap = {};
        data.forEach(f => {
            const c = f.properties.chainname;
            const sc = f.properties.subchainname;
            if (!c) return;
            if (!chainMap[c]) chainMap[c] = new Set();
            if (sc) chainMap[c].add(sc);
        });

        activeChains = new Set(Object.keys(chainMap));
        Object.values(chainMap).forEach(scSet => scSet.forEach(sc => activeSubchains.add(sc)));

        const chainContainer = document.getElementById('chain-filters');

        // Select all / deselect all
        const chainToggle = document.createElement('div');
        chainToggle.className = 'select-all-row';
        chainToggle.innerHTML = `
            <button class="select-all-btn" id="chain-select-all">בחר הכל</button>
            <button class="select-all-btn" id="chain-deselect-all">נקה הכל</button>`;
        chainContainer.appendChild(chainToggle);

        document.getElementById('chain-select-all').addEventListener('click', () => {
            chainContainer.querySelectorAll('input[type=checkbox]').forEach(cb => {
                cb.checked = true;
                activeChains.add(cb.value);
            });
            rebuildSubchainOptions(chainMap);
            addMarkersToMap(storesData);
        });
        document.getElementById('chain-deselect-all').addEventListener('click', () => {
            chainContainer.querySelectorAll('input[type=checkbox]').forEach(cb => {
                cb.checked = false;
                activeChains.delete(cb.value);
            });
            rebuildSubchainOptions(chainMap);
            addMarkersToMap(storesData);
        });

        // Chain checkboxes
        Object.keys(chainMap).sort().forEach(chain => {
            const label = document.createElement('label');
            label.className = 'filter-checkbox';
            label.innerHTML = `
                <input type="checkbox" value="${chain}" checked>
                <img src="../img/${getChainLogo(chain)}" alt="${chain}" class="filter-logo">
                <span>${chain}</span>`;
            label.querySelector('input').addEventListener('change', function () {
                if (this.checked) activeChains.add(chain);
                else activeChains.delete(chain);
                rebuildSubchainOptions(chainMap);
                addMarkersToMap(storesData);
            });
            chainContainer.appendChild(label);
        });

        rebuildSubchainOptions(chainMap);
    }

    function rebuildSubchainOptions(chainMap) {
        const subchainContainer = document.getElementById('subchain-filters');
        subchainContainer.innerHTML = '';

        const relevantSubchains = new Set();
        activeChains.forEach(chain => {
            if (chainMap[chain]) chainMap[chain].forEach(sc => relevantSubchains.add(sc));
        });

        activeSubchains.forEach(sc => { if (!relevantSubchains.has(sc)) activeSubchains.delete(sc); });
        relevantSubchains.forEach(sc => activeSubchains.add(sc));

        if (relevantSubchains.size === 0) {
            subchainContainer.innerHTML = '<p class="no-subchains">אין תת-רשתות</p>';
            return;
        }

        [...relevantSubchains].sort().forEach(sc => {
            const label = document.createElement('label');
            label.className = 'filter-checkbox subchain-checkbox';
            label.innerHTML = `<input type="checkbox" value="${sc}" ${activeSubchains.has(sc) ? 'checked' : ''}><span>${sc}</span>`;
            label.querySelector('input').addEventListener('change', function () {
                if (this.checked) activeSubchains.add(sc);
                else activeSubchains.delete(sc);
                addMarkersToMap(storesData);
            });
            subchainContainer.appendChild(label);
        });
    }

    // ── Create a single marker ────────────────────────────────────────────────
    function createMarker(store) {
        const props = store.properties;
        const priceDiff = parseFloat(props.average_price_diff);
        const formattedDiff = priceDiff.toFixed(1);

        let icon;
        if (viewMode === 'logo') {
            const logoFile = getChainLogo(props.chainname);
            icon = L.divIcon({
                className: 'logo-marker',
                html: `<div class="logo-marker-inner"><img src="../img/${logoFile}" alt="${props.chainname}"></div>`,
                iconSize: [36, 36],
                iconAnchor: [18, 18]
            });
        } else {
            const color = getPriceColor(priceDiff);
            icon = L.divIcon({
                className: 'custom-marker',
                html: `<div style="background-color:${color};width:20px;height:20px;border-radius:50%;border:2px solid #fff;"></div>`,
                iconSize: [20, 20],
                iconAnchor: [10, 10]
            });
        }

        const logoPath = `../img/${getChainLogo(props.chainname)}`;
        const sign = priceDiff < 0 ? '' : priceDiff > 0 ? '+' : '';
        const priceClass = getPriceClass(priceDiff);

        const popupContent = `
            <div class="popup-header">${props.store_name || 'חנות'}</div>
            <div class="popup-content">
                <p class="chain-name">
                    <img src="${logoPath}" alt="${props.chainname}" class="chain-logo-small">
                    ${props.chainname || ''} ${props.subchainname ? '- ' + props.subchainname : ''}
                </p>
                <p>${props.address || ''}, ${props.city || ''}</p>
                <p>הפרש מחירים ממוצע (כשי):
                    <span class="price-indicator ${priceClass}">
                        <span class="number-wrapper">${sign}${Math.abs(formattedDiff)}%</span>
                    </span>
                </p>
                <p class="popup-note">* מחיר אפקטיבי לפי פריטי כשי (כולל מבצעים)</p>
            </div>`;

        const marker = L.marker(
            [store.geometry.coordinates[1], store.geometry.coordinates[0]],
            { icon, riseOnHover: true, title: props.store_name, priceDiff, properties: props }
        );

        marker.bindPopup(popupContent);
        marker.on('click', () => showStoreDetails(props));
        return marker;
    }

    // ── Add / refresh markers ─────────────────────────────────────────────────
    function addMarkersToMap(data) {
        markers.clearLayers();
        data.forEach(store => {
            if (matchesFilters(store)) markers.addLayer(createMarker(store));
        });
        map.addLayer(markers);
        if (markers.getLayers().length > 0)
            map.fitBounds(markers.getBounds(), { padding: [50, 50] });
    }

    function matchesFilters(store) {
        const props = store.properties;
        if (props.average_price_diff === undefined || props.average_price_diff === null) return false;
        if (parseFloat(props.average_price_diff) > priceDiffMax) return false;
        if (!activeChains.has(props.chainname)) return false;
        if (props.subchainname && !activeSubchains.has(props.subchainname)) return false;
        return true;
    }

    // ── Sidebar store detail panel ────────────────────────────────────────────
    function showStoreDetails(props) {
        const priceDiff = parseFloat(props.average_price_diff).toFixed(1);
        const pd = parseFloat(priceDiff);
        const priceClass = getPriceClass(pd);
        const priceText = getPriceLabel(pd);
        const logoPath = `../img/${getChainLogo(props.chainname)}`;

        const html = `
            <div class="store-logo-container">
                <img src="${logoPath}" alt="${props.chainname}" class="chain-logo">
            </div>
            <div class="store-detail-item">
                <span class="detail-label">שם החנות:</span>
                <span class="detail-value">${props.store_name || 'לא זמין'}</span>
            </div>
            <div class="store-detail-item">
                <span class="detail-label">רשת:</span>
                <span class="detail-value">${props.chainname || 'לא זמין'}</span>
            </div>
            ${props.subchainname ? `
            <div class="store-detail-item">
                <span class="detail-label">תת-רשת:</span>
                <span class="detail-value">${props.subchainname}</span>
            </div>` : ''}
            <div class="store-detail-item">
                <span class="detail-label">כתובת:</span>
                <span class="detail-value">${props.address || 'לא זמין'}, ${props.city || ''}</span>
            </div>
            <div class="store-detail-item">
                <span class="detail-label">הפרש מחירי כשי:</span>
                <span class="detail-value">
                    <span class="price-indicator ${priceClass}">
                        <span class="number-wrapper">${priceText}</span>
                    </span>
                </span>
            </div>
            <div class="store-detail-item">
                <span class="detail-label">מספר פריטי כשי שהושוו:</span>
                <span class="detail-value">${props.kashi_item_count != null ? Number(props.kashi_item_count).toLocaleString() : 'לא זמין'}</span>
            </div>
            <div class="store-detail-item">
                <span class="detail-note">* המחירים כוללים מבצעים פעילים</span>
            </div>`;

        if (storeDetails) storeDetails.innerHTML = html;
    }

    // ── Price range slider ────────────────────────────────────────────────────
    const priceDiffFilter = document.getElementById('price-diff-filter');
    const resetFiltersBtn = document.getElementById('reset-filters');
    let sliderTimeout;

    priceDiffFilter.addEventListener('input', function () {
        priceDiffMax = parseInt(this.value);
        clearTimeout(sliderTimeout);
        sliderTimeout = setTimeout(() => addMarkersToMap(storesData), 300);
    });
    priceDiffFilter.addEventListener('change', function () {
        priceDiffMax = parseInt(this.value);
        addMarkersToMap(storesData);
    });

    resetFiltersBtn.addEventListener('click', function () {
        priceDiffMax = 20;
        priceDiffFilter.value = 20;
        document.querySelectorAll('#chain-filters input[type=checkbox]').forEach(cb => {
            cb.checked = true;
            activeChains.add(cb.value);
        });
        document.querySelectorAll('#subchain-filters input[type=checkbox]').forEach(cb => {
            cb.checked = true;
            activeSubchains.add(cb.value);
        });
        addMarkersToMap(storesData);
    });

    // ── View toggle button (price / logo) ─────────────────────────────────────
    const toggleViewBtn = document.getElementById('toggle-view-btn');
    toggleViewBtn.addEventListener('click', function () {
        viewMode = viewMode === 'price' ? 'logo' : 'price';
        this.textContent = viewMode === 'price' ? 'הצג לוגו רשת' : 'הצג לפי מחיר';
        const legend = document.getElementById('map-legend');
        if (legend) legend.style.display = viewMode === 'price' ? 'block' : 'none';
        addMarkersToMap(storesData);
    });

    // ── Legend toggle ─────────────────────────────────────────────────────────
    const toggleLegendBtn = document.getElementById('toggle-legend');
    const legendContent = document.getElementById('legend-content');
    if (toggleLegendBtn && legendContent) {
        toggleLegendBtn.addEventListener('click', function () {
            const icon = this.querySelector('i');
            if (legendContent.style.display === 'none') {
                legendContent.style.display = 'block';
                icon.classList.replace('fa-chevron-up', 'fa-chevron-down');
                localStorage.setItem('legendVisible', 'true');
            } else {
                legendContent.style.display = 'none';
                icon.classList.replace('fa-chevron-down', 'fa-chevron-up');
                localStorage.setItem('legendVisible', 'false');
            }
        });
        if (localStorage.getItem('legendVisible') === 'false') {
            legendContent.style.display = 'none';
            toggleLegendBtn.querySelector('i').classList.replace('fa-chevron-down', 'fa-chevron-up');
        }
    }

    // ── Info popup ────────────────────────────────────────────────────────────
    const infoButton = document.querySelector('.info-icon');
    const infoPopup = document.getElementById('info-popup');
    const closeInfo = document.querySelector('.close-info');
    const popupOverlay = document.getElementById('popup-overlay');

    if (infoButton && infoPopup) {
        infoButton.addEventListener('click', function (e) {
            e.stopPropagation();
            infoPopup.style.display = 'block';
            if (popupOverlay) popupOverlay.style.display = 'block';
        });
        closeInfo.addEventListener('click', function () {
            infoPopup.style.display = 'none';
            if (popupOverlay) popupOverlay.style.display = 'none';
        });
        if (popupOverlay) popupOverlay.addEventListener('click', function () {
            infoPopup.style.display = 'none';
            popupOverlay.style.display = 'none';
        });
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && infoPopup.style.display === 'block') {
                infoPopup.style.display = 'none';
                if (popupOverlay) popupOverlay.style.display = 'none';
            }
        });
    }

    // ── Tab switching ─────────────────────────────────────────────────────────
    const tabMap = document.getElementById('tab-map');
    const tabTable = document.getElementById('tab-table');
    const viewMapEl = document.getElementById('view-map');
    const viewTableEl = document.getElementById('view-table');
    const mapLegend = document.getElementById('map-legend');

    function switchTab(tab) {
        if (tab === 'map') {
            viewMapEl.style.display = 'flex';
            viewTableEl.style.display = 'none';
            tabMap.classList.add('active');
            tabTable.classList.remove('active');
            if (mapLegend) mapLegend.style.display = viewMode === 'price' ? 'block' : 'none';
            setTimeout(() => { if (window.map) window.map.invalidateSize(); }, 50);
        } else {
            viewMapEl.style.display = 'none';
            viewTableEl.style.display = 'flex';
            tabMap.classList.remove('active');
            tabTable.classList.add('active');
            if (mapLegend) mapLegend.style.display = 'none';
            if (storesData.length > 0 && !tableBuilt) renderTable();
            else if (tableBuilt) renderTable();
        }
    }

    tabMap.addEventListener('click', () => switchTab('map'));
    tabTable.addEventListener('click', () => switchTab('table'));

    // ── Table search ──────────────────────────────────────────────────────────
    const tableSearch = document.getElementById('table-search');
    let searchTimeout;
    tableSearch.addEventListener('input', function () {
        tableSearchTerm = this.value;
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(renderTable, 200);
    });

    // ── Table render ──────────────────────────────────────────────────────────
    function renderTable() {
        tableBuilt = true;
        const container = document.getElementById('kashi-table-container');

        if (storesData.length === 0) {
            container.innerHTML = '<p class="table-empty">אין נתונים להצגה. הריצו את סקריפט הייצוא תחילה.</p>';
            return;
        }

        const term = tableSearchTerm.trim().toLowerCase();
        let filtered = storesData.filter(f => {
            if (!term) return true;
            const p = f.properties;
            return (p.store_name || '').toLowerCase().includes(term) ||
                   (p.chainname || '').toLowerCase().includes(term) ||
                   (p.subchainname || '').toLowerCase().includes(term) ||
                   (p.city || '').toLowerCase().includes(term);
        });

        filtered.sort((a, b) => {
            let av = a.properties[sortCol];
            let bv = b.properties[sortCol];
            if (av == null && bv == null) return 0;
            if (av == null) return 1;
            if (bv == null) return -1;
            if (typeof av === 'string') return sortDir * av.localeCompare(bv, 'he');
            return sortDir * (av - bv);
        });

        const cols = [
            { key: 'store_name',        label: 'שם החנות' },
            { key: 'chainname',         label: 'רשת' },
            { key: 'subchainname',      label: 'תת-רשת' },
            { key: 'city',              label: 'עיר' },
            { key: 'average_price_diff',label: 'הפרש מחיר כשי' },
            { key: 'kashi_item_count',  label: 'מספר פריטים' }
        ];

        let headerCells = cols.map(c => {
            let cls = '';
            if (c.key === sortCol) cls = sortDir === 1 ? 'sort-asc' : 'sort-desc';
            return `<th data-col="${c.key}" class="${cls}">${c.label}</th>`;
        }).join('');

        let rows = filtered.map(f => {
            const p = f.properties;
            const diff = p.average_price_diff != null ? parseFloat(p.average_price_diff) : null;
            const sign = diff != null ? (diff < 0 ? '' : diff > 0 ? '+' : '') : '';
            const diffStr = diff != null ? `${sign}${diff.toFixed(2)}%` : '—';
            const diffCls = diff != null ? getDiffClass(diff) : '';
            const itemCount = p.kashi_item_count != null ? Number(p.kashi_item_count).toLocaleString() : '—';

            return `<tr>
                <td>${p.store_name || '—'}</td>
                <td>${p.chainname || '—'}</td>
                <td>${p.subchainname || '—'}</td>
                <td>${p.city || '—'}</td>
                <td class="col-diff ${diffCls}">${diffStr}</td>
                <td style="text-align:center;">${itemCount}</td>
            </tr>`;
        }).join('');

        container.innerHTML = `
            <p class="table-count">${filtered.length.toLocaleString()} סניפים מוצגים</p>
            <table class="kashi-table">
                <thead><tr>${headerCells}</tr></thead>
                <tbody>${rows || '<tr><td colspan="6" class="table-empty">לא נמצאו תוצאות</td></tr>'}</tbody>
            </table>`;

        // Attach sort listeners
        container.querySelectorAll('th[data-col]').forEach(th => {
            th.addEventListener('click', function () {
                const col = this.dataset.col;
                if (sortCol === col) sortDir = -sortDir;
                else { sortCol = col; sortDir = 1; }
                renderTable();
            });
        });
    }

});
