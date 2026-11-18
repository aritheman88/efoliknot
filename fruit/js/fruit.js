document.addEventListener('DOMContentLoaded', function () {

    // ── Disclaimer ────────────────────────────────────────────────────────────
    const disclaimerModal = document.getElementById('disclaimer-modal');
    const acceptBtn = document.getElementById('accept-disclaimer');
    if (localStorage.getItem('disclaimerAccepted') === 'true') {
        disclaimerModal.style.display = 'none';
    } else {
        disclaimerModal.style.display = 'block';
        document.getElementById('map').style.pointerEvents = 'none';
    }
    acceptBtn.addEventListener('click', function () {
        localStorage.setItem('disclaimerAccepted', 'true');
        disclaimerModal.style.display = 'none';
        document.getElementById('map').style.pointerEvents = 'auto';
    });

    // ── Map ───────────────────────────────────────────────────────────────────
    const map = L.map('map').setView([31.7683, 35.2137], 8);
    window.map = map;
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(map);
    const layer = L.featureGroup().addTo(map);

    const chainLogos = {
        'רמי לוי': 'ramiLevi.png', 'שופרסל': 'shufersal.png', 'ויקטורי': 'victory.png',
        'יוחננוף': 'yohananof.png', 'מחסני השוק': 'mahsaneiHashuk.png', 'טיב טעם': 'tivTaam.png',
        'אושר עד': 'osherAd.png', 'קרפור': 'carrefour.png'
    };
    const COLORS = ['#006400', '#32CD32', '#FFD700', '#FF8C00', '#FF0000'];
    const LEVEL_LABELS = ['זול מאוד', 'זול', 'בינוני', 'יקר', 'יקר מאוד'];

    // ── State ─────────────────────────────────────────────────────────────────
    let data = null;
    let fruit = null;
    let chainFilter = null;          // null = all chains
    let promoOnly = false;
    let breaks = [];
    let tableSearchTerm = '';
    let sortKey = 'eff', sortDir = 1;

    const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
    const fmt = v => '₪' + Number(v).toFixed(2);

    function quantile(sorted, q) {
        const pos = (sorted.length - 1) * q, lo = Math.floor(pos), hi = Math.ceil(pos);
        return sorted[lo] + (sorted[hi] - sorted[lo]) * (pos - lo);
    }

    function levelOf(v) {
        for (let i = 0; i < breaks.length; i++) if (v <= breaks[i]) return i;
        return breaks.length;
    }

    function fruitLabel(key) {
        const f = data.fruits.find(f => f.key === key);
        return f ? f.label : key;
    }

    // ── Fruit tabs ────────────────────────────────────────────────────────────
    function buildFruitTabs() {
        const wrap = document.getElementById('fruit-tabs');
        wrap.innerHTML = data.fruits.map((f, i) => {
            const best = (data.summary[f.key] || [])[0];
            const divider = f.group === 'season' && (i === 0 || data.fruits[i - 1].group !== 'season')
                ? '<span class="fruit-group-label">פירות העונה:</span>' : '';
            return `${divider}<button class="fruit-tab" role="tab" data-key="${f.key}">
                        <span class="fruit-name">${esc(f.label)}</span>
                        ${best ? `<span class="fruit-from">החל מ-${fmt(best.min)} לק"ג</span>` : ''}
                    </button>`;
        }).join('');
        wrap.querySelectorAll('.fruit-tab').forEach(b => b.addEventListener('click', () => selectFruit(b.dataset.key)));
    }

    function selectFruit(key) {
        fruit = key;
        document.querySelectorAll('.fruit-tab').forEach(b => {
            const on = b.dataset.key === key;
            b.classList.toggle('active', on);
            b.setAttribute('aria-selected', on);
        });
        const vals = data.stores.filter(s => s.p[key]).map(s => s.p[key][0]).sort((a, b) => a - b);
        breaks = [0.2, 0.4, 0.6, 0.8].map(q => quantile(vals, q));
        // collapse duplicate breaks (prices cluster on x.90)
        breaks = breaks.filter((b, i) => i === 0 || b > breaks[i - 1]);
        try { localStorage.setItem('fruitSelected', key); } catch (e) { /* ignore */ }
        renderPanel();
        renderLegend();
        renderMarkers();
        if (document.getElementById('view-table').style.display !== 'none') renderTable();
    }

    // ── Chain panel ───────────────────────────────────────────────────────────
    function renderPanel() {
        document.getElementById('chain-panel-title').textContent = `${fruitLabel(fruit)}: הזול ביותר בכל רשת`;
        const rows = data.summary[fruit] || [];
        const missing = data.chains.filter(c => !rows.some(r => r.chain === c));
        const overall = rows.length ? rows[0].min : null;
        let html = rows.map((r, i) => {
            const isBest = r.min === overall;
            const where = r.minStoresCount > 1
                ? `${esc(r.minStore)}, ${esc(r.minCity)} ועוד ${r.minStoresCount - 1} סניפים`
                : `${esc(r.minStore)}, ${esc(r.minCity)}`;
            return `<div class="chain-row${isBest ? ' best' : ''}${chainFilter === r.chain ? ' selected' : ''}" data-chain="${esc(r.chain)}" tabindex="0">
                <img class="chain-logo" src="../img/${chainLogos[r.chain] || 'lobby99 water.png'}" alt="">
                <div class="chain-main">
                    <div class="chain-line">
                        <span class="chain-name">${esc(r.chain)}</span>
                        ${isBest ? '<span class="best-tag">הכי זול</span>' : ''}
                        <span class="chain-min">${fmt(r.min)}</span>
                    </div>
                    <div class="chain-where">${where}${r.minPromo ? ` · <span class="promo-tag">${esc(r.minPromo)}</span>` : ''}</div>
                    <div class="chain-sub">חציון ברשת ${fmt(r.median)} · ${r.stores} סניפים${r.promoShare > 0 ? ` · ${Math.round(r.promoShare * 100)}% במבצע` : ''}</div>
                </div>
            </div>`;
        }).join('');
        if (missing.length) html += `<div class="chain-missing">אין מחיר לק"ג ל${fruitLabel(fruit)}: ${missing.map(esc).join(', ')}${fruit === 'strawberry' ? '. תחילת העונה, וחלק מהרשתות מוכרות תותים במארז בלי משקל מוצהר.' : ''}</div>`;
        const panel = document.getElementById('chain-panel');
        panel.innerHTML = html;
        panel.querySelectorAll('.chain-row').forEach(el => {
            const toggle = () => { chainFilter = chainFilter === el.dataset.chain ? null : el.dataset.chain; renderPanel(); renderMarkers(true); };
            el.addEventListener('click', toggle);
            el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); toggle(); } });
        });
        document.getElementById('show-all-chains').style.display = chainFilter ? 'block' : 'none';
    }

    // ── Legend ────────────────────────────────────────────────────────────────
    function renderLegend() {
        const b = breaks.map(v => v.toFixed(2));
        const items = [];
        for (let i = 0; i <= b.length; i++) {
            const range = i === 0 ? `עד ₪${b[0]}` : i === b.length ? `מעל ₪${b[i - 1]}` : `₪${b[i - 1]}–${b[i]}`;
            const li = Math.round(i * 4 / Math.max(1, b.length));
            items.push(`<div><span class="legend-color" style="background:${COLORS[li]}"></span> ${LEVEL_LABELS[li]} <span class="legend-range">${range}</span></div>`);
        }
        document.getElementById('legend-content').innerHTML = items.join('');
    }

    function colorFor(v) {
        const lvl = levelOf(v);
        return COLORS[Math.round(lvl * 4 / Math.max(1, breaks.length))];
    }

    // ── Markers ───────────────────────────────────────────────────────────────
    function visibleStores() {
        return data.stores.filter(s => s.p[fruit]
            && (!chainFilter || s.chain === chainFilter)
            && (!promoOnly || s.p[fruit][3]));
    }

    function popupHtml(s) {
        const [eff, reg, item, promo] = s.p[fruit];
        const others = data.fruits.filter(f => f.key !== fruit && s.p[f.key])
            .map(f => `<div class="popup-other">${esc(f.label)}: ${fmt(s.p[f.key][0])}</div>`).join('');
        return `<div class="store-popup">
            <div class="popup-head"><img src="../img/${chainLogos[s.chain] || 'lobby99 water.png'}" alt=""> <b>${esc(s.chain)}</b> · ${esc(s.name)}</div>
            <div class="popup-addr">${esc(s.addr || '')}${s.addr ? ', ' : ''}${esc(s.city)}</div>
            <div class="popup-price">${esc(fruitLabel(fruit))}: <b>${fmt(eff)}</b> לק"ג</div>
            ${promo ? `<div class="popup-promo">${esc(promo)} (מחיר רגיל ${fmt(reg)})</div>` : ''}
            <div class="popup-note">${esc(item)}</div>
            ${others ? `<div class="popup-others"><div class="popup-others-title">פירות נוספים בסניף:</div>${others}</div>` : ''}
        </div>`;
    }

    function renderMarkers(fit) {
        layer.clearLayers();
        const list = visibleStores().sort((a, b) => b.p[fruit][0] - a.p[fruit][0]); // cheap on top
        list.forEach(s => {
            const eff = s.p[fruit][0];
            L.circleMarker([s.lat, s.lon], {
                radius: s.p[fruit][3] ? 8 : 6,
                color: s.p[fruit][3] ? '#002d7f' : '#555',
                weight: s.p[fruit][3] ? 2 : 1,
                fillColor: colorFor(eff), fillOpacity: 0.9
            }).bindPopup(() => popupHtml(s), { maxWidth: 280 })
              .bindTooltip(`${s.chain} ${s.name}: ${fmt(eff)}`, { direction: 'top' })
              .addTo(layer);
        });
        if (fit && list.length) map.fitBounds(layer.getBounds(), { padding: [40, 40], maxZoom: 13 });
    }
    window.fitAll = function () {
        if (layer.getLayers().length) map.fitBounds(layer.getBounds(), { padding: [40, 40] });
    };

    // ── Table ─────────────────────────────────────────────────────────────────
    function renderTable() {
        const term = tableSearchTerm.trim();
        let rows = data.stores.filter(s => s.p[fruit]).map(s => ({
            chain: s.chain, name: s.name, city: s.city, item: s.p[fruit][2],
            reg: s.p[fruit][1], eff: s.p[fruit][0], promo: s.p[fruit][3]
        }));
        if (term) rows = rows.filter(r => [r.chain, r.name, r.city, r.item].some(x => (x || '').includes(term)));
        rows.sort((a, b) => {
            const x = a[sortKey], y = b[sortKey];
            return (typeof x === 'number' ? x - y : String(x).localeCompare(String(y), 'he')) * sortDir;
        });
        const cols = [['chain', 'רשת'], ['name', 'סניף'], ['city', 'עיר'], ['item', 'פריט'], ['reg', 'מחיר רגיל לק"ג'], ['eff', 'מחיר אפקטיבי לק"ג'], ['promo', 'מבצע']];
        const head = cols.map(([k, l]) => `<th data-k="${k}" class="${k === sortKey ? (sortDir > 0 ? 'sort-asc' : 'sort-desc') : ''}">${l}</th>`).join('');
        const body = rows.length ? rows.map(r => `<tr>
                <td>${esc(r.chain)}</td><td>${esc(r.name)}</td><td>${esc(r.city)}</td><td>${esc(r.item)}</td>
                <td class="num">${fmt(r.reg)}</td>
                <td class="num"><span class="eff-dot" style="background:${colorFor(r.eff)}"></span><b>${fmt(r.eff)}</b></td>
                <td>${esc(r.promo)}</td></tr>`).join('')
            : `<tr><td colspan="7" class="table-empty">לא נמצאו סניפים</td></tr>`;
        const c = document.getElementById('fruit-table-container');
        c.innerHTML = `<div class="table-count">${rows.length} סניפים · ${esc(fruitLabel(fruit))}</div>
            <table class="fruit-table"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table>`;
        c.querySelectorAll('th').forEach(th => th.addEventListener('click', () => {
            if (sortKey === th.dataset.k) sortDir = -sortDir; else { sortKey = th.dataset.k; sortDir = 1; }
            renderTable();
        }));
    }

    // ── Controls ──────────────────────────────────────────────────────────────
    document.getElementById('promo-only').addEventListener('change', function () {
        promoOnly = this.checked; renderMarkers();
    });
    document.getElementById('show-all-chains').addEventListener('click', function () {
        chainFilter = null; renderPanel(); renderMarkers(true);
    });

    const tabMap = document.getElementById('tab-map'), tabTable = document.getElementById('tab-table');
    const viewMap = document.getElementById('view-map'), viewTable = document.getElementById('view-table');
    const legend = document.getElementById('map-legend');
    tabMap.addEventListener('click', () => {
        viewMap.style.display = 'flex'; viewTable.style.display = 'none';
        tabMap.classList.add('active'); tabTable.classList.remove('active');
        legend.style.display = 'block';
        setTimeout(() => map.invalidateSize(), 50);
    });
    tabTable.addEventListener('click', () => {
        viewMap.style.display = 'none'; viewTable.style.display = 'flex';
        tabMap.classList.remove('active'); tabTable.classList.add('active');
        legend.style.display = 'none';
        renderTable();
    });
    let searchTimeout;
    document.getElementById('table-search').addEventListener('input', function () {
        tableSearchTerm = this.value;
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(renderTable, 200);
    });

    // Legend toggle
    const toggleLegendBtn = document.getElementById('toggle-legend');
    const legendContent = document.getElementById('legend-content');
    toggleLegendBtn.addEventListener('click', function () {
        const icon = this.querySelector('i');
        const hide = legendContent.style.display !== 'none';
        legendContent.style.display = hide ? 'none' : 'block';
        icon.classList.replace(hide ? 'fa-chevron-down' : 'fa-chevron-up', hide ? 'fa-chevron-up' : 'fa-chevron-down');
    });

    // Info popup
    const infoButton = document.querySelector('.info-icon');
    const infoPopup = document.getElementById('info-popup');
    const popupOverlay = document.getElementById('popup-overlay');
    const closePopup = () => { infoPopup.style.display = 'none'; popupOverlay.style.display = 'none'; };
    infoButton.addEventListener('click', e => { e.stopPropagation(); infoPopup.style.display = 'block'; popupOverlay.style.display = 'block'; });
    document.querySelector('.close-info').addEventListener('click', closePopup);
    popupOverlay.addEventListener('click', closePopup);
    document.addEventListener('keydown', e => { if (e.key === 'Escape') closePopup(); });

    // ── Load ──────────────────────────────────────────────────────────────────
    fetch('data/fruit_prices.json')
        .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
        .then(json => {
            data = json;
            const [y, m, d] = data.date.split('-');
            document.getElementById('data-date').textContent = `${d}.${m}.${y}`;
            buildFruitTabs();
            let saved = null;
            try { saved = localStorage.getItem('fruitSelected'); } catch (e) { /* ignore */ }
            selectFruit(data.fruits.some(f => f.key === saved) ? saved : data.fruits[0].key);
            setTimeout(() => { map.invalidateSize(); window.fitAll(); }, 100);
        })
        .catch(err => {
            document.getElementById('chain-panel').innerHTML = `<p class="table-empty">שגיאה בטעינת הנתונים (${esc(err.message)})</p>`;
        });
});
