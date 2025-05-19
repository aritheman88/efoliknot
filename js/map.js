document.addEventListener('DOMContentLoaded', function() {
    // Initialize map centered at Israel
    const map = L.map('map').setView([31.7683, 35.2137], 8);
    
    // Add OpenStreetMap tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
        maxZoom: 19
    }).addTo(map);
    
    // Create marker cluster group with custom icons based on average price
    const markers = L.markerClusterGroup({
        disableClusteringAtZoom: 15,
        spiderfyOnMaxZoom: true,
        showCoverageOnHover: false,
        zoomToBoundsOnClick: true,
        // Add custom icon creation function
        iconCreateFunction: function(cluster) {
            // Calculate average price difference for all markers in this cluster
            const childMarkers = cluster.getAllChildMarkers();
            let totalPriceDiff = 0;
            let validMarkers = 0;

            // Debug - log cluster size and marker details
            console.log("Processing cluster with " + childMarkers.length + " markers");

            // Check each marker for average_price_diff data
            childMarkers.forEach(function(marker, index) {
                let priceDiff;
                if (marker.options && marker.options.priceDiff !== undefined) {
                    // Get price diff from options if available
                    priceDiff = parseFloat(marker.options.priceDiff);
                    console.log(`Marker ${index} - from options:`, priceDiff);
                } else if (marker.feature &&
                          marker.feature.properties &&
                          marker.feature.properties.average_price_diff !== undefined &&
                          marker.feature.properties.average_price_diff !== null) {
                    // Get price diff from feature properties
                    priceDiff = parseFloat(marker.feature.properties.average_price_diff);
                    console.log(`Marker ${index} - from properties:`, priceDiff);
                }

                if (!isNaN(priceDiff)) {
                    totalPriceDiff += priceDiff;
                    validMarkers++;
                }
            });

            // Calculate average
            const avgPriceDiff = validMarkers > 0 ? totalPriceDiff / validMarkers : 0;

            // Debug - log calculations
            console.log("Total price diff:", totalPriceDiff);
            console.log("Valid markers:", validMarkers);
            console.log("Average price diff:", avgPriceDiff.toFixed(2) + "%");

            // Determine icon color based on average price difference
            let className;

            if (avgPriceDiff <= -8) {
                className = 'marker-cluster-dark-green'; // Below -8% - dark green
            } else if (avgPriceDiff <= -3) {
                className = 'marker-cluster-light-green'; // -8% to -3% - light green
            } else if (avgPriceDiff <= 3) {
                className = 'marker-cluster-yellow'; // -3% to 3% - yellow
            } else if (avgPriceDiff <= 8) {
                className = 'marker-cluster-orange'; // 3% to 8% - orange
            } else {
                className = 'marker-cluster-red'; // Above 8% - red
            }

            // Debug - log selected class and criteria
            console.log("Average price diff:", avgPriceDiff, "Class selected:", className);
            console.log("Criteria check:", {
                "≤ -8%": avgPriceDiff <= -8,
                "≤ -3%": avgPriceDiff <= -3,
                "≤ 3%": avgPriceDiff <= 3,
                "≤ 8%": avgPriceDiff <= 8,
                "> 8%": avgPriceDiff > 8
            });

            return new L.DivIcon({
                html: '<div><span>' + cluster.getChildCount() + '</span></div>',
                className: 'marker-cluster ' + className,
                iconSize: new L.Point(40, 40)
            });
        }
    });

    // Chain logo mapping
    const chainLogos = {
        'רמי לוי': 'ramiLevi.png',
        'שופרסל': 'shufersal.png',
        'ויקטורי': 'victory.png',
        'יוחננוף': 'yohananof.png',
        'מחסני השוק': 'mahsaneiHashuk.png',
        'טיב טעם': 'tivTaam.png',
        'יינות ביתן': 'yenotBitan.png',
        'אושר עד': 'osherAd.png',
        'חצי חינם': 'haziHinam.png',
        'סטופ מרקט': 'stop.png',
        'Am-pm': 'ampm.png',
        'זול ובגדול': 'zol.png',
        'יודה': 'yuda.png',
        'כל בו חצי חינם': 'haziHinam.png',
        'מעיין 2000': 'maayan.png',
        'נתיב החסד': 'nativ.png',
        'קרפור': 'carrefour.png',
        'שפע ברכת השם': 'shefa.png',
        'שפע שוק': 'shefa.png',
        // Add more chains as needed
    };

    // Default image for unknown chains
    const defaultLogo = 'lobby99 water.png';

    // Store data references
    let storesData = [];
    let visibleMarkers = [];

    // Store filter values
    const filters = {
        chain: 'all',
        city: 'all',
        priceDiff: 20 // Changed initial value to 20 to show all stores
    };

    // DOM elements for filters
    const chainFilter = document.getElementById('chain-filter');
    const cityFilter = document.getElementById('city-filter');
    const priceDiffFilter = document.getElementById('price-diff-filter');
    const priceDiffOutput = document.getElementById('price-diff-output');
    const resetFiltersBtn = document.getElementById('reset-filters');
    const storeDetails = document.getElementById('store-details');

    // Load GeoJSON data
    fetch('data/stores.geojson')
        .then(response => response.json())
        .then(data => {
            storesData = data.features;
            initializeFilters(storesData);
            addMarkersToMap(storesData);
        })
        .catch(error => {
            console.error('Error loading GeoJSON data:', error);
            alert('שגיאה בטעינת נתוני המפה. אנא נסה שוב מאוחר יותר.');
        });

    // Initialize filter values
    function initializeFilters(data) {
        // Get unique chains
        const chains = [...new Set(data.map(store => store.properties.chainname).filter(Boolean))].sort();

        // Log all unique chain names to help identify missing logos
        console.log('Unique chain names in data:', chains);

        // Populate chain select
        chains.forEach(chain => {
            const option = document.createElement('option');
            option.value = chain;
            option.textContent = chain;
            chainFilter.appendChild(option);
        });

        // Get unique cities
        const cities = [...new Set(data.map(store => store.properties.city).filter(Boolean))].sort();

        // Populate city select
        cities.forEach(city => {
            const option = document.createElement('option');
            option.value = city;
            option.textContent = city;
            cityFilter.appendChild(option);
        });

        // Initialize range slider outputs
        updateRangeOutputs();
    }

    // Helper function to get chain logo
    function getChainLogo(chainname) {
        // Check if we have a specific logo for this chain
        if (chainname && chainLogos[chainname]) {
            return chainLogos[chainname];
        }

        // Try to find a partial match if direct match not found
        if (chainname) {
            for (const [key, value] of Object.entries(chainLogos)) {
                if (chainname.includes(key)) {
                    return value;
                }
            }
        }

        // Return default logo if no match found
        return defaultLogo;
    }

    // Create marker with popup for each store
    function createMarker(store) {
        const props = store.properties;

        // Format average_price_diff to 1 decimal place
        const formattedPriceDiff = props.average_price_diff !== null && props.average_price_diff !== undefined
            ? parseFloat(props.average_price_diff).toFixed(1)
            : 0;

        // Determine marker color based on price difference
        let markerColor = '#3498db'; // default blue
        if (formattedPriceDiff > 5) {
            markerColor = '#ff463c'; // Red (orange) for higher prices
        } else if (formattedPriceDiff < -5) {
            markerColor = '#2ecc71'; // green for lower prices
        } else {
            markerColor = '#f39c12'; // yellow for neutral
        }

        // Create custom icon
        const icon = L.divIcon({
            className: 'custom-marker',
            html: `<div style="background-color:${markerColor}; width:20px; height:20px; border-radius:50%; border:2px solid #fff;"></div>`,
            iconSize: [20, 20],
            iconAnchor: [10, 10]
        });

        // Create marker
        const marker = L.marker([store.geometry.coordinates[1], store.geometry.coordinates[0]], {
            icon: icon,
            riseOnHover: true,
            title: props.store_name,
            priceDiff: parseFloat(props.average_price_diff), // Add price difference directly to marker options
            properties: props
        });

        // Get chain logo path
        const logoPath = `img/${getChainLogo(props.chainname)}`;

        // Create popup content with formatted price difference
        // UPDATED: Added store_code to the popup link
        const popupContent = `
            <div class="popup-header">${props.store_name || 'חנות'}</div>
            <div class="popup-content">
                <p class="chain-name">
                    <img src="${logoPath}" alt="${props.chainname}" class="chain-logo-small">
                    ${props.chainname || ''} ${props.subchainname ? '- ' + props.subchainname : ''}
                </p>
                <p>${props.address || ''}, ${props.city || ''}</p>
                ${formattedPriceDiff ? `
                <p>הפרש מחירים ממוצע:
                    <span class="price-indicator ${formattedPriceDiff < 0 ? 'price-lower' : formattedPriceDiff > 0 ? 'price-higher' : 'price-neutral'}">
                        ${formattedPriceDiff > 0 ? '+' : ''}${formattedPriceDiff}%
                    </span>
                </p>` : ''}
                <a href="#" class="popup-link" data-store-id="${props.storeid || props.store_code}" data-store-code="${props.store_code}">הצג פרטים נוספים</a>
            </div>
        `;

        // Add popup to marker
        marker.bindPopup(popupContent);

        // Add click event to marker
        marker.on('click', () => {
            showStoreDetails(props);
        });

        return marker;
    }

    // Add markers to map
    function addMarkersToMap(data) {
        // Add debug to check the first store's properties
        if (data && data.length > 0) {
            console.log("First store properties:", data[0].properties);
            console.log("store_code exists:", data[0].properties.hasOwnProperty('store_code'));
        // Clear existing markers
        markers.clearLayers();
        visibleMarkers = [];
        }
        // Add new markers
        data.forEach(store => {
            if (matchesFilters(store)) {
                const marker = createMarker(store);
                markers.addLayer(marker);
                visibleMarkers.push({
                    storeId: store.properties.storeid || store.properties.store_code,
                    marker: marker
                });
            }
        });

        // Add marker cluster group to map
        map.addLayer(markers);

        // Fit map to markers bounds if there are any
        if (visibleMarkers.length > 0) {
            map.fitBounds(markers.getBounds(), { padding: [50, 50] });
        }
    }

    // Check if store matches current filters
    function matchesFilters(store) {
        const props = store.properties;

        // Chain filter
        if (filters.chain !== 'all' && props.chainname !== filters.chain) {
            return false;
        }

        // City filter
        if (filters.city !== 'all' && props.city !== filters.city) {
            return false;
        }

        // Price difference filter - changed to show stores with price difference LESS THAN the max value
        if (props.average_price_diff === undefined || props.average_price_diff === null || props.average_price_diff > filters.priceDiff) {
            return false;
        }

        return true;
    }

    // Show store details in sidebar
    function showStoreDetails(props) {
        // Format price difference to 1 decimal place
        const formattedPriceDiff = props.average_price_diff !== null && props.average_price_diff !== undefined
            ? parseFloat(props.average_price_diff).toFixed(1)
            : 0;

        let priceClass = '';
        let priceText = '';

        if (formattedPriceDiff < 0) {
            priceClass = 'price-lower';
            priceText = `${formattedPriceDiff}% (מחיר נמוך מהממוצע)`;
        } else if (formattedPriceDiff > 0) {
            priceClass = 'price-higher';
            priceText = `+${formattedPriceDiff}% (מחיר גבוה מהממוצע)`;
        } else {
            priceClass = 'price-neutral';
            priceText = `${formattedPriceDiff}% (דומה לממוצע)`;
        }

        // Get chain logo path
        const logoPath = `img/${getChainLogo(props.chainname)}`;

        const detailsHTML = `
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
                <span class="detail-label">מיקוד:</span>
                <span class="detail-value">${props.zipcode || 'לא זמין'}</span>
            </div>
            <div class="store-detail-item">
                <span class="detail-label">הפרש מחירים:</span>
                <span class="detail-value">
                    <span class="price-indicator ${priceClass}">${priceText}</span>
                </span>
            </div>
            <div class="store-detail-item">
                <span class="detail-label">קוד חנות:</span>
                <span class="detail-value">${props.store_code || 'לא זמין'}</span>
            </div>
            <div class="store-detail-item">
                <button class="btn" onclick="showStorePrices('${props.store_code}')">הצג טבלת מחירים</button>
            </div>
        `;

        storeDetails.innerHTML = detailsHTML;
    }

    // Update range slider output values
    function updateRangeOutputs() {
        priceDiffOutput.textContent = `${filters.priceDiff}%`;
    }

    // Event Listeners

    // Chain filter
    chainFilter.addEventListener('change', function() {
        filters.chain = this.value;
        addMarkersToMap(storesData);
    });

    // City filter
    cityFilter.addEventListener('change', function() {
        filters.city = this.value;
        addMarkersToMap(storesData);
    });

    // Price difference filter - now filters stores with price difference LESS THAN the max value
    priceDiffFilter.addEventListener('input', function() {
        filters.priceDiff = parseInt(this.value);
        updateRangeOutputs();
    });

    priceDiffFilter.addEventListener('change', function() {
        addMarkersToMap(storesData);
    });

    // Reset filters
    resetFiltersBtn.addEventListener('click', function() {
        // Reset filter values
        filters.chain = 'all';
        filters.city = 'all';
        filters.priceDiff = 20; // Reset to 20 to show all stores

        // Reset DOM elements
        chainFilter.value = 'all';
        cityFilter.value = 'all';
        priceDiffFilter.value = 20;

        // Update outputs
        updateRangeOutputs();

        // Update map
        addMarkersToMap(storesData);
    });

    // Handle popup link clicks
    document.addEventListener('click', function(e) {
        if (e.target && e.target.classList.contains('popup-link')) {
            e.preventDefault();
            const storeId = e.target.getAttribute('data-store-id');
            const storeCode = e.target.getAttribute('data-store-code');

            // Find the store and show details
            const store = storesData.find(s => {
                const id = s.properties.storeid || s.properties.store_code;
                return id.toString() === storeId;
            });

            if (store) {
                showStoreDetails(store.properties);
            }

            // Then show price table if store code is available
            if (storeCode) {
                showStorePrices(storeCode);
            }
        }
    });

    // Close modal when clicking the X or outside the modal
    const modal = document.getElementById('price-modal');
    const closeBtn = document.querySelector('.close-modal');

    if (closeBtn && modal) {
        closeBtn.addEventListener('click', function() {
            modal.style.display = 'none';
        });

        window.addEventListener('click', function(event) {
            if (event.target == modal) {
                modal.style.display = 'none';
            }
        });
    }

    // Function to fetch and display store price data

    window.showStorePrices = function(storeCode) {
        console.log('showStorePrices called with store code:', storeCode);
        
        // Get elements
        const modal = document.getElementById('price-modal');
        const modalTitle = document.getElementById('price-modal-title');
        const modalStoreInfo = document.getElementById('price-modal-store-info');
        const tableContainer = document.getElementById('price-table-container');
        const searchInput = document.getElementById('price-search');
        const sortButtons = document.querySelectorAll('.sort-btn');
        
        console.log('Modal element exists:', !!modal);
        console.log('Table container exists:', !!tableContainer);
        
        if (!modal || !tableContainer) {
            console.error('Required modal elements not found in the DOM');
            return;

        }
        
        // Show loading state and display modal
        tableContainer.innerHTML = '<p class="text-center">טוען נתונים...</p>';
        modal.style.display = 'block';
        
        // Log the full URL we're fetching from
        const fetchUrl = `/data/store_files/${storeCode}.json`;
        console.log('Fetching from URL:', fetchUrl);
        
        // Fetch the store price data
        fetch(fetchUrl)
            .then(response => {
                console.log('Fetch response status:', response.status);
                if (!response.ok) {
                    throw new Error(`Network response was not ok: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Data received:', data);
                console.log('Number of prices:', data.prices ? data.prices.length : 0);
                
                // Update modal title and store info
                if (modalTitle) modalTitle.textContent = `טבלת מחירים - ${data.store_name}`;
                if (modalStoreInfo) modalStoreInfo.textContent = `${data.chainname}${data.subchainname ? ' - ' + data.subchainname : ''}, ${data.city}`;
                
                // Create table with the price data
                createPriceTable(data, tableContainer);
                
                // Setup search functionality
                if (searchInput && sortButtons) {
                    setupSearchAndSort(data, tableContainer, searchInput, sortButtons);
                }
            })
            .catch(error => {
                console.error('Error fetching store prices:', error);
                tableContainer.innerHTML = `
                    <div class="error-message">
                        <p>שגיאה בטעינת נתוני המחירים</p>
                        <p>אנא נסה שוב מאוחר יותר</p>
                        <p><small>פרטי השגיאה: ${error.message}</small></p>
                    </div>
                `;
            });
    };
    

    // Create the price table
    function createPriceTable(data, container, sortBy = 'name', sortDir = 'asc', searchTerm = '') {
        // Make a copy of the prices array for sorting and filtering
        let prices = [...data.prices];

        // Filter by search term if provided
        if (searchTerm) {
            const term = searchTerm.toLowerCase();
            prices = prices.filter(item =>
                (item.itemname && item.itemname.toLowerCase().includes(term)) ||
                (item.manufacturer && item.manufacturer.toLowerCase().includes(term)) ||
                (item.brand && item.brand.toLowerCase().includes(term)) ||
                (item.category && item.category.toLowerCase().includes(term))
            );
        }

        // Sort the data based on the selected sort option
        prices.sort((a, b) => {
            switch (sortBy) {
                case 'name':
                    return sortDir === 'asc'
                        ? (a.itemname || '').localeCompare(b.itemname || '')
                        : (b.itemname || '').localeCompare(a.itemname || '');
                case 'price':
                    const aPrice = a.price || 0;
                    const bPrice = b.price || 0;
                    return sortDir === 'asc' ? aPrice - bPrice : bPrice - aPrice;
                case 'diff':
                    const aDiff = a.price_diff_pct || 0;
                    const bDiff = b.price_diff_pct || 0;
                    return sortDir === 'asc' ? aDiff - bDiff : bDiff - aDiff;
                default:
                    return 0;
            }
        });

        // Create the table
        let tableHTML = `
            <table class="price-table">
                <thead>
                    <tr>
                        <th>שם המוצר</th>
                        <th>יצרן</th>
                        <th>מותג</th>
                        <th>קטגוריה</th>
                        <th>מחיר בחנות (₪)</th>
                        <th>מחיר ממוצע (₪)</th>
                        <th>הפרש (%)</th>
                    </tr>
                </thead>
                <tbody>
        `;

        // Add rows for each price item
        if (prices.length === 0) {
            tableHTML += `
                <tr>
                    <td colspan="7" class="text-center">לא נמצאו מוצרים</td>
                </tr>
            `;
        } else {
            prices.forEach(item => {
                // Determine price difference class
                let diffClass = 'price-neutral-cell';
                if (item.price_diff_pct < -3) {
                    diffClass = 'price-lower-cell';
                } else if (item.price_diff_pct > 3) {
                    diffClass = 'price-higher-cell';
                }

                // Format price and difference values
                const formattedPrice = item.price ? item.price.toFixed(2) : '-';
                const formattedAvgPrice = item.average_price ? item.average_price.toFixed(2) : '-';
                const formattedDiff = item.price_diff_pct ? item.price_diff_pct.toFixed(1) : '-';

                // Add the row
                tableHTML += `
                    <tr>
                        <td>${item.itemname || '-'}</td>
                        <td>${item.manufacturer || '-'}</td>
                        <td>${item.brand || '-'}</td>
                        <td>${item.category || '-'}</td>
                        <td>${formattedPrice}</td>
                        <td>${formattedAvgPrice}</td>
                        <td class="price-diff-cell ${diffClass}">${formattedDiff}</td>
                    </tr>
                `;
            });
        }

        tableHTML += `
                </tbody>
            </table>
        `;

        // Update the container with the table
        container.innerHTML = tableHTML;
    }

    // Setup search and sort functionality
    function setupSearchAndSort(data, container, searchInput, sortButtons) {
        let currentSortBy = 'name';
        let currentSortDir = 'asc';
        let currentSearchTerm = '';

        // Search input event
        searchInput.addEventListener('input', function() {
            currentSearchTerm = this.value;
            createPriceTable(data, container, currentSortBy, currentSortDir, currentSearchTerm);
        });

        // Sort buttons event
        sortButtons.forEach(button => {
            button.addEventListener('click', function() {
                const sortBy = this.getAttribute('data-sort');

                // Update sort direction if clicking the same button
                if (sortBy === currentSortBy) {
                    currentSortDir = currentSortDir === 'asc' ? 'desc' : 'asc';
                } else {
                    currentSortBy = sortBy;
                    currentSortDir = 'asc';
                }

                // Update active button
                sortButtons.forEach(btn => btn.classList.remove('active'));
                this.classList.add('active');

                // Update the table
                createPriceTable(data, container, currentSortBy, currentSortDir, currentSearchTerm);
            });
        });
    }
});

// For testing in browser console
function testPriceTable() {
    console.log('Testing price table with ram_064');
    showStorePrices('ram_064');
}