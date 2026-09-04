// DEBUG: Script started.
console.log("DEBUG: script.js (Tailwind v12 - CORRECT Dynamic Filter Logic) loaded.");

let allPerfumes = [];
let allBrands = new Map();
const state = {
    searchQuery: '',
    sortBy: 'brand',
    favorites: [],
    showingFavorites: false,
    selectedBrand: null,
    activeFilters: {
        gender: [],
        brands: [],
        season: [],
        occasion: [],
        accords: []
    }
};

// KONSTANTER til Boost Guide
const LIGHT_ACCORDS = ['fresh', 'aquatic', 'citrus', 'aromatic', 'floral'];
const HEAVY_ACCORDS = ['gourmand', 'oriental', 'amber', 'spicy', 'leather', 'woody'];

// Mapping for token farver
const TOKEN_COLORS = {
    gender: 'token-gender',
    brands: 'token-brand',
    season: 'token-season',
    occasion: 'token-occasion',
    accords: 'token-accord'
};

// --- KERNELOGIK: DATAVISNING ---

function displayPerfumes(perfumes) {
    const container = document.getElementById('resultsContainer');
    const template = document.getElementById('perfume-card-template');
    const resultsCountEl = document.getElementById('results-count');

    container.innerHTML = ''; // Nulstil container

    // Opdater tæller
    let countText = `Showing ${perfumes.length}`;
    if (state.selectedBrand) {
        countText += ` result(s) for "${state.selectedBrand}"`;
    } else if (state.showingFavorites) {
        countText += ` favorite(s)`;
    } else {
        countText += ` of ${allPerfumes.length} results`;
    }
    resultsCountEl.textContent = countText + ".";

    if (perfumes.length === 0) {
        container.innerHTML = `<p class="text-secondary col-span-full">No perfumes matched your selection.</p>`;
        return;
    }

    // Klon skabelon for hver parfume
    perfumes.forEach(perfume => {
        const p = perfume.item ? perfume.item : perfume;
        const card = template.content.cloneNode(true);
        const isFavorite = state.favorites.includes(p.code);

        // Udfyld data
        card.querySelector('[data-field="code"]').textContent = p.code;
        card.querySelector('[data-field="inspiredBy"]').textContent = p.inspiredBy;
        card.querySelector('[data-field="brand"]').textContent = p.brand;
        card.querySelector('[data-field="description"]').textContent = p.description || '';

        const shobiLink = `https://leparfum.com.gr/en/module/iqitsearch/searchiqit?s=${p.code}`;
        card.querySelector('[data-field="shobiLink"]').href = shobiLink;

        // Håndter favoritknap
        const favButton = card.querySelector('.favorite-btn');
        favButton.dataset.code = p.code;
        favButton.innerHTML = isFavorite ? '<i class="fa-solid fa-heart"></i>' : '<i class="fa-regular fa-heart"></i>';
        if (isFavorite) favButton.classList.add('is-favorite');

        // Ikoner
        const audienceIconsContainer = card.querySelector('[data-field="audience-icons"]');
        audienceIconsContainer.innerHTML = getAudienceIcons(p.genderAffinity);
        const typeIconsContainer = card.querySelector('[data-field="type-icons"]');
        typeIconsContainer.innerHTML = getTypeIcons(p.mainAccords);

        // Sæt data-attributter til klik-handlere
        card.querySelector('[data-action="show-details"]').dataset.code = p.code;
        card.querySelector('[data-action="filter-brand"]').dataset.brand = p.brand;

        container.appendChild(card);
    });

    // Gen-tilføj event listeners
    container.querySelectorAll('.favorite-btn').forEach(btn =>
        btn.addEventListener('click', toggleFavorite)
    );
    container.querySelectorAll('[data-action="show-details"]').forEach(el =>
        el.addEventListener('click', (e) => showPerfumeModal(e.currentTarget.dataset.code))
    );
    container.querySelectorAll('[data-action="filter-brand"]').forEach(btn =>
        btn.addEventListener('click', (e) => handleBrandFilterClick(e.currentTarget.dataset.brand))
    );
    container.querySelectorAll('[data-action="filter-icon"]').forEach(btn =>
        btn.addEventListener('click', (e) => {
            const el = e.currentTarget;
            handleIconFilterClick(el.dataset.filterType, el.dataset.filterValue);
        })
    );
}

/**
 * Anvender HELE filterkæden OG opdaterer UI bagefter.
 */
function applyFiltersAndRender() {
    // Kør selve filtreringen
    const filteredPerfumes = getFilteredPerfumes();

    // --- UI Opdateringer ---
    displayBrandInfo(); // Vis/skjul brand info boks
    displayPerfumes(filteredPerfumes); // Vis de filtrerede resultater
    updateAvailableFilterOptions(); // NYT: Kør den nye, korrekte logik for at deaktivere/aktivere
    displayActiveFilterTokens(); // Vis filter tokens
}

/**
 * NYT: Funktion der KUN udfører filtreringen baseret på state.
 * Returnerer den filtrerede liste.
 * @param {Object} [overrideFilters=null] - Et midlertidigt filter-sæt til simulering.
 */
function getFilteredPerfumes(overrideFilters = null) {
    let filtered = [...allPerfumes];
    const currentFilters = overrideFilters || state.activeFilters; // Brug override hvis det gives

    // --- Filterkæde ---
    // 1. Brand (enkelt klik ELLER tjekbokse) eller Favoritter
     // Prioriter selectedBrand hvis det er sat
     if (state.selectedBrand && !overrideFilters) { // Kun hvis vi ikke simulerer
         filtered = filtered.filter(p => p.brand === state.selectedBrand);
     } else if (currentFilters.brands.length > 0) {
         filtered = filtered.filter(p => currentFilters.brands.includes(p.brand));
     } else if (state.showingFavorites && !overrideFilters) { // Kun hvis vi ikke simulerer
         filtered = filtered.filter(p => state.favorites.includes(p.code));
     }


    // 2. Gender (OR logic)
    if (currentFilters.gender.length > 0) {
        filtered = filtered.filter(p => {
            return currentFilters.gender.some(filterGender => p.genderAffinity.includes(filterGender));
        });
    }

    // 3. Season (OR logic)
    if (currentFilters.season.length > 0) {
        filtered = filtered.filter(p => {
            return currentFilters.season.some(filterSeason => p.seasons.includes(filterSeason));
        });
    }

    // 4. Occasion (OR logic)
    if (currentFilters.occasion.length > 0) {
        filtered = filtered.filter(p => {
            return currentFilters.occasion.some(filterOccasion => p.occasions.includes(filterOccasion));
        });
    }

    // 5. Accords (AND logic)
    if (currentFilters.accords.length > 0) {
        filtered = filtered.filter(p => {
            return currentFilters.accords.every(filterAccord => p.mainAccords.includes(filterAccord));
        });
    }

    // 6. Søgning (kun hvis vi ikke simulerer)
    if (state.searchQuery && !overrideFilters) {
        const query = state.searchQuery.toLowerCase();
        filtered = filtered.filter(p =>
            String(p.inspiredBy || '').toLowerCase().includes(query) ||
            String(p.brand || '').toLowerCase().includes(query) ||
            String(p.code || '').toLowerCase().includes(query)
        );
    }

    // 7. Sort visible results. "Best seller" uses the available scent score
    // as the current ranking signal because the dataset has no sales counter.
    if (!overrideFilters) {
        const byName = (a, b) => String(a.inspiredBy || '').localeCompare(String(b.inspiredBy || ''), 'en', { sensitivity: 'base' });
        const byBrand = (a, b) => String(a.brand || '').localeCompare(String(b.brand || ''), 'en', { sensitivity: 'base' }) || byName(a, b);
        if (state.sortBy === 'name') {
            filtered.sort(byName);
        } else if (state.sortBy === 'best-seller') {
            filtered.sort((a, b) => {
                const scoreA = Number(a.userRatings?.scent) || 0;
                const scoreB = Number(b.userRatings?.scent) || 0;
                return scoreB - scoreA || byBrand(a, b);
            });
        } else {
            filtered.sort(byBrand);
        }
    }

    return filtered;
}


// --- NY LOGIK: DYNAMISKE FILTRE & TOKENS ---

/**
 * (OMSKREVET) Opdaterer filter-checkboxes (aktiver/deaktiver) KORREKT.
 */
function updateAvailableFilterOptions() {
    // Gennemgå alle checkboxes
    document.querySelectorAll('#filter-sidebar input[type="checkbox"]').forEach(checkbox => {
        let filterType;
        switch(checkbox.name) {
            case 'gender': filterType = 'gender'; break;
            case 'brand': filterType = 'brands'; break; // Matcher state key
            case 'season': filterType = 'season'; break;
            case 'occasion': filterType = 'occasion'; break;
            case 'accord': filterType = 'accords'; break; // Matcher state key
            default: return;
        }
        const value = checkbox.value;
        const label = checkbox.closest('label');

        // Spring over, hvis checkboxen allerede ER markeret (den skal altid være aktiv)
        if (checkbox.checked) {
            checkbox.disabled = false;
            if (label) label.classList.remove('disabled');
            return;
        }

        // SIMULER: Hvad sker der, hvis vi TILFØJER dette filter?
        // Klon nuværende aktive filtre
        const simulatedFilters = JSON.parse(JSON.stringify(state.activeFilters));
        // Tilføj den aktuelle checkbox' værdi midlertidigt
        simulatedFilters[filterType].push(value);

        // Kør en simulering med de midlertidige filtre
        const simulationResult = getFilteredPerfumes(simulatedFilters);

        // Opdater checkboxens tilstand baseret på simuleringen
        if (simulationResult.length > 0) {
            checkbox.disabled = false;
            if (label) label.classList.remove('disabled');
        } else {
            checkbox.disabled = true;
            if (label) label.classList.add('disabled');
        }
    });
}


/**
 * Viser de aktive filtre som tokens over resultatlisten. (Uændret)
 */
function displayActiveFilterTokens() {
    const container = document.getElementById('active-filters-display');
    container.innerHTML = ''; // Nulstil
    let hasTokens = false;

    // Gennemgå alle aktive filtre i state
    for (const filterType in state.activeFilters) {
        state.activeFilters[filterType].forEach(value => {
            hasTokens = true;
            const token = document.createElement('span');
            // Gør første bogstav stort
            const displayValue = value.charAt(0).toUpperCase() + value.slice(1);
            token.className = `filter-token ${TOKEN_COLORS[filterType] || 'token-default'}`; // Brug farvemapping
            token.innerHTML = `
                ${displayValue}
                <button data-filter-type="${filterType}" data-filter-value="${value}" title="Remove filter">&times;</button>
            `;
            container.appendChild(token);
        });
    }

    // Skjul container, hvis der ingen tokens er
    container.style.display = hasTokens ? 'flex' : 'none';

    // Tilføj event listeners til slette-knapperne
    container.querySelectorAll('button').forEach(button => {
        button.addEventListener('click', handleRemoveToken);
    });
}

/**
 * Fjerner et filter, når en token-sletteknap klikkes. (Uændret)
 */
function handleRemoveToken(e) {
    const button = e.currentTarget;
    const filterType = button.dataset.filterType; // f.eks. 'brands', 'season'
    const value = button.dataset.filterValue;

    // 1. Fjern fra state
    const index = state.activeFilters[filterType].indexOf(value);
    if (index > -1) {
        state.activeFilters[filterType].splice(index, 1);
    }

    // 2. Fjern flueben fra checkbox
    let checkboxName;
     switch(filterType) {
         case 'brands': checkboxName = 'brand'; break;
         case 'accords': checkboxName = 'accord'; break;
         default: checkboxName = filterType;
     }
    const checkbox = document.querySelector(`#filter-sidebar input[name="${checkboxName}"][value="${value}"]`);
    if (checkbox) {
        checkbox.checked = false;
    }

    // 3. Gen-render alt
    applyFiltersAndRender();
}


// --- ØVRIG KERNELOGIK (Stort set uændret) ---

function displayBrandInfo() {
    // ... (uændret)
    const container = document.getElementById('brand-info-container');
    const contentEl = document.getElementById('brand-info-content');

    if (!state.selectedBrand) {
        container.classList.add('hidden');
        return;
    }

    const brandInfo = allBrands.get(state.selectedBrand);
    if (!brandInfo) {
        container.classList.add('hidden');
        return;
    }

    contentEl.innerHTML = `
        <h2 class="text-2xl font-bold text-primary">${brandInfo.name}</h2>
        <p class="mt-2 text-secondary">${brandInfo.description || 'No information available for this brand.'}</p>
    `;
    container.classList.remove('hidden');
}

function handleBrandFilterClick(brandName) {
    // ... (uændret)
    state.selectedBrand = brandName;
    state.showingFavorites = false;

    // Nulstil brand-tjekbokse i state og UI
    state.activeFilters.brands = [];
    document.querySelectorAll('#brand-filters input[type="checkbox"]').forEach(cb => cb.checked = false);

    document.getElementById('favorites-btn').classList.remove('bg-red-800');

    applyFiltersAndRender();
    document.getElementById('brand-info-container').scrollIntoView({ behavior: 'smooth' });
}

function handleIconFilterClick(filterType, filterValue) {
    // ... (uændret)
    const stateKey = filterType === 'accord' ? 'accords' : filterType;

    const filtersContent = document.getElementById('filters-content');
    if (filtersContent.classList.contains('hidden') && window.innerWidth < 1024) { // Kun toggle på mobil
        toggleMobileFilters();
    }

    const checkboxName = filterType === 'accord' ? 'accord' : filterType;
    const checkbox = document.querySelector(`#filter-sidebar input[name="${checkboxName}"][value="${filterValue}"]`);


    if (checkbox && !checkbox.checked) {
        checkbox.checked = true; // Sæt fluebenet

        // Udløs 'change' eventet for at bruge den centrale handler
        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
    }
}


// --- IKON-HJÆLPERE (Uændret) ---

function getAudienceIcons(audience) {
    // ... (uændret)
     const a = String(audience || '').toLowerCase();
    if (!a) return '';
    let icons = [];

    const iconMap = {
        'masculine': { value: 'masculine', html: '<i class="fas fa-mars text-blue-600" title="Masculine"></i>' },
        'feminine': { value: 'feminine', html: '<i class="fas fa-venus text-red-600" title="Feminine"></i>' },
        'unisex': { value: 'unisex', html: '<i class="fas fa-venus-mars text-green-600" title="Unisex"></i>' }
    };

    if (a.includes('male') || a.includes('masculine') || a.includes('men')) icons.push(iconMap.masculine);
    if (a.includes('female') || a.includes('feminine') || a.includes('women')) icons.push(iconMap.feminine);
    if (a.includes('unisex')) icons.push(iconMap.unisex);

    return icons.map(icon =>
        `<span data-action="filter-icon" data-filter-type="gender" data-filter-value="${icon.value}">${icon.html}</span>`
    ).join(' ');
}

const SCENT_ICON_MAP = {
    // ... (uændret)
     'citrus': { icon: '<i class="fas fa-lemon text-yellow-500" title="Citrus"></i>', value: 'citrus' },
    'woody': { icon: '<i class="fas fa-tree text-amber-700" title="Woody"></i>', value: 'woody' },
    'floral': { icon: '<i class="fas fa-fan text-pink-400" title="Floral"></i>', value: 'floral' },
    'aromatic': { icon: '<i class="fas fa-seedling text-lime-600" title="Aromatic"></i>', value: 'aromatic' },
    'spicy': { icon: '<i class="fas fa-pepper-hot text-orange-600" title="Spicy"></i>', value: 'spicy' },
    'oriental': { icon: '<i class="fas fa-feather text-purple-500" title="Oriental/Amber"></i>', value: 'oriental' },
    'amber': { icon: '<i class="fas fa-feather text-purple-500" title="Oriental/Amber"></i>', value: 'amber' },
    'fresh': { icon: '<i class="fas fa-wind text-sky-500" title="Fresh"></i>', value: 'fresh' },
    'aquatic': { icon: '<i class="fas fa-water text-cyan-500" title="Aquatic"></i>', value: 'aquatic' },
    'leather': { icon: '<i class="fas fa-layer-group text-stone-600" title="Leather"></i>', value: 'leather' }
};

function getTypeIcons(accords) {
    // ... (uændret)
    if (!Array.isArray(accords) || accords.length === 0) return '';
    let iconsHtml = [];
    const addedIcons = new Set();
    const lowerCaseAccords = accords.map(a => a.toLowerCase());

    for (const key in SCENT_ICON_MAP) {
        if (!addedIcons.has(key) && lowerCaseAccords.some(accord => accord.includes(key))) {
            const iconData = SCENT_ICON_MAP[key];
            iconsHtml.push(
                `<span data-action="filter-icon" data-filter-type="accord" data-filter-value="${iconData.value}">${iconData.icon}</span>`
            );
            addedIcons.add(key);
        }
    }
    return iconsHtml.join(' ');
}


// --- KERNELOGIK: FAVORITTER (Uændret) ---

function toggleFavorite(event) {
    // ... (uændret)
     event.stopPropagation();
    const button = event.currentTarget;
    const code = button.dataset.code;
    const index = state.favorites.indexOf(code);

    if (index > -1) {
        state.favorites.splice(index, 1);
        button.innerHTML = '<i class="fa-regular fa-heart"></i>';
        button.classList.remove('is-favorite');
    } else {
        state.favorites.push(code);
        button.innerHTML = '<i class="fa-solid fa-heart"></i>';
        button.classList.add('is-favorite');
    }

    localStorage.setItem('shobi-favorites', JSON.stringify(state.favorites));
    document.getElementById('favorites-count').textContent = state.favorites.length;

    if (state.showingFavorites) {
        applyFiltersAndRender();
    }
}

function loadFavorites() {
    // ... (uændret)
    const savedFavorites = localStorage.getItem('shobi-favorites');
    if (savedFavorites) {
        state.favorites = JSON.parse(savedFavorites);
    }
    document.getElementById('favorites-count').textContent = state.favorites.length;
}

// --- KERNELOGIK: MODAL (Uændret) ---

const modal = document.getElementById('perfume-modal');
const modalContent = document.getElementById('modal-content');
const modalOverlay = document.getElementById('modal-overlay');
const modalCloseBtn = document.getElementById('modal-close-btn');

function getBoostGuideHtml(perfume) {
    // ... (uændret)
    const accords = perfume.mainAccords || [];
    const isHeavy = accords.some(accord => HEAVY_ACCORDS.includes(accord.toLowerCase()));

    let rec;
    let title;

    if (isHeavy) {
        title = "Heavy/Gourmand Scent";
        rec = { '30ml': '2ml', '50ml': '3-4ml', '100ml': '5ml' };
    } else {
        title = "Fresh/Light Scent";
        rec = { '30ml': '1ml', '50ml': '2ml', '100ml': '3ml' };
    }

    return `
        <div class="w-full">
            <p class="text-sm text-secondary mb-2">Recommendation for a <strong class="text-primary">${title}</strong>:</p>
            <div class="flex justify-around">
                <div>
                    <span class="text-lg font-bold text-primary">30ml</span>
                    <p class="text-sm text-accent font-medium">+ ${rec['30ml']}</p>
                </div>
                <div>
                    <span class="text-lg font-bold text-primary">50ml</span>
                    <p class="text-sm text-accent font-medium">+ ${rec['50ml']}</p>
                </div>
                <div>
                    <span class="text-lg font-bold text-primary">100ml</span>
                    <p class="text-sm text-accent font-medium">+ ${rec['100ml']}</p>
                </div>
            </div>
        </div>
    `;
}

function showPerfumeModal(code) {
    // ... (uændret)
    const perfume = allPerfumes.find(p => p.code === code);
    if (!perfume) return;

    document.getElementById('modal-inspiredBy').textContent = perfume.inspiredBy;
    document.getElementById('modal-brand').textContent = perfume.brand;
    document.getElementById('modal-code').textContent = perfume.code;
    document.getElementById('modal-description').textContent = perfume.description || 'No description available.';

    const notesContainer = document.getElementById('modal-notes');
    const topNotes = perfume.notes && Array.isArray(perfume.notes.top) && perfume.notes.top.length > 0
        ? perfume.notes.top.join(', ')
        : null;
    const heartNotes = perfume.notes && Array.isArray(perfume.notes.heart) && perfume.notes.heart.length > 0
        ? perfume.notes.heart.join(', ')
        : null;
    const baseNotes = perfume.notes && Array.isArray(perfume.notes.base) && perfume.notes.base.length > 0
        ? perfume.notes.base.join(', ')
        : null;

    const notesHtml = `
        ${topNotes ? `<p><strong class="text-primary">Top:</strong> ${topNotes}</p>` : ''}
        ${heartNotes ? `<p><strong class="text-primary">Heart:</strong> ${heartNotes}</p>` : ''}
        ${baseNotes ? `<p><strong class="text-primary">Base:</strong> ${baseNotes}</p>` : ''}
    `;
    notesContainer.innerHTML = (topNotes || heartNotes || baseNotes) ? notesHtml : '<p>No note details available.</p>';

    const boostGuideContainer = document.getElementById('modal-boost-guide');
    boostGuideContainer.innerHTML = getBoostGuideHtml(perfume);

    document.getElementById('modal-shobiLink').href = `https://leparfum.com.gr/en/module/iqitsearch/searchiqit?s=${perfume.code}`;

    modal.classList.remove('invisible');
    setTimeout(() => {
        modal.classList.remove('opacity-0');
        modalContent.classList.remove('opacity-0', '-translate-y-10');
    }, 10);
}

function hidePerfumeModal() {
    // ... (uændret)
    modal.classList.add('opacity-0');
    modalContent.classList.add('opacity-0', '-translate-y-10');
    setTimeout(() => {
        modal.classList.add('invisible');
    }, 300);
}


// --- FILTER-LOGIK (OPDATERET) ---

function toggleMobileFilters() {
    // ... (uændret)
    const filtersContent = document.getElementById('filters-content');
    const filtersIcon = document.getElementById('filters-toggle-icon');
    filtersContent.classList.toggle('hidden');
    filtersIcon.classList.toggle('rotate-180');
}

/**
 * Nulstiller alle filtre og opdaterer UI.
 */
function resetAllFilters() {
    // ... (uændret)
    state.searchQuery = '';
    state.showingFavorites = false;
    state.selectedBrand = null;
    state.activeFilters = {
        gender: [],
        brands: [],
        season: [],
        occasion: [],
        accords: []
    };
    document.getElementById('search-input').value = '';
    document.getElementById('favorites-btn').classList.remove('bg-red-800');
    document.querySelectorAll('#filter-sidebar input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = false;
         // Sikrer at alle labels bliver aktiveret igen
         checkbox.disabled = false;
         checkbox.closest('label')?.classList.remove('disabled'); // Sikkerhedscheck for label
    });
    applyFiltersAndRender(); // Kald efter UI er nulstillet
}


/**
 * Bygger filter-checkboxes dynamisk baseret på data.
 */
function populateFilters() {
    const genderContainer = document.getElementById('gender-filters');
    const brandContainer = document.getElementById('brand-filters');
    const seasonContainer = document.getElementById('season-filters');
    const occasionContainer = document.getElementById('occasion-filters');
    const accordContainer = document.getElementById('accord-filters');

    // Helper til at bygge checkboxes
    const buildCheckboxes = (container, name, options, loaderId) => {
        if (!container) return; // Sikkerhedstjek
        // Konverter options til Array for sort()
        const sortedOptions = Array.from(options).sort();

        if (sortedOptions.length === 0) {
             container.innerHTML = `<p class="text-sm text-tertiary">No data found.</p>`;
        } else {
             container.innerHTML = sortedOptions.map(option => {
                 // Check om option er valid (ikke tom streng)
                 if (!option) return '';
                 const capitalized = option.charAt(0).toUpperCase() + option.slice(1);
                 // Tilføj ikon for accords
                 const iconSpan = (name === 'accord') ?
                    `<span class="inline-block w-5 mr-1">${SCENT_ICON_MAP[option] ? SCENT_ICON_MAP[option].icon : ''}</span>`
                    : '';
                 return `
                     <label>
                         <input type="checkbox" name="${name}" value="${option}">
                         ${iconSpan} ${capitalized}
                     </label>
                 `;
             }).join('');
        }
        document.getElementById(loaderId)?.remove(); // Sikker fjernelse
    };

    // 1. Gender (Stadig hardkodet)
    const genders = [
        { label: 'Masculine', value: 'masculine' },
        { label: 'Feminine', value: 'feminine' },
        { label: 'Unisex', value: 'unisex' }
    ];
    genderContainer.innerHTML = genders.map(g => `
        <label>
            <input type="checkbox" name="gender" value="${g.value}">
            ${g.label}
        </label>
    `).join('');

    // 2. Brands (Dynamisk)
    buildCheckboxes(brandContainer, 'brand', allBrands.keys(), 'brand-loader');

    // 3. Seasons (Dynamisk fra p.seasons)
    const allSeasons = new Set(allPerfumes.flatMap(p => p.seasons));
    buildCheckboxes(seasonContainer, 'season', allSeasons, 'season-loader');

    // 4. Occasions (Dynamisk fra p.occasions)
    const allOccasions = new Set(allPerfumes.flatMap(p => p.occasions));
    buildCheckboxes(occasionContainer, 'occasion', allOccasions, 'occasion-loader');

    // 5. Accords (Dynamisk)
    const allAccords = new Set(allPerfumes.flatMap(p => p.mainAccords));
    buildCheckboxes(accordContainer, 'accord', allAccords, 'accord-loader');


    // 6. Tilføj Event Listeners til ALLE tjekbokse
    document.querySelectorAll('#filter-sidebar input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', handleCheckboxChange); // Brug central handler
    });
}


/**
 * Central handler for alle filter-checkbox ændringer.
 */
function handleCheckboxChange(e) {
    let filterType;
    switch(e.target.name) {
        case 'gender': filterType = 'gender'; break;
        case 'brand': filterType = 'brands'; break;
        case 'season': filterType = 'season'; break;
        case 'occasion': filterType = 'occasion'; break;
        case 'accord': filterType = 'accords'; break;
        default: return; // Ukendt filter
    }

    const value = e.target.value;

    if (e.target.checked) {
        if (!state.activeFilters[filterType].includes(value)) {
            state.activeFilters[filterType].push(value);
        }
        // Nulstil selectedBrand hvis et brand-tjekboks vælges
        if (filterType === 'brands') {
            state.selectedBrand = null;
        }
    } else {
        const index = state.activeFilters[filterType].indexOf(value);
        if (index > -1) state.activeFilters[filterType].splice(index, 1);
    }
    applyFiltersAndRender();
}


// --- TEMA-LOGIK (Uændret) ---

function setTheme(theme) {
    // ... (uændret)
    const htmlTag = document.getElementById('html-tag');
    if (theme === 'light') {
        htmlTag.removeAttribute('data-theme');
        localStorage.removeItem('shobi-theme');
    } else {
        htmlTag.setAttribute('data-theme', theme);
        localStorage.setItem('shobi-theme', theme);
    }
}

function initTheme() {
    // ... (uændret)
    const savedTheme = localStorage.getItem('shobi-theme');
    if (savedTheme) {
        setTheme(savedTheme);
    }
    const themeMenuBtn = document.getElementById('theme-menu-btn');
    const themeMenuDropdown = document.getElementById('theme-menu-dropdown');

    themeMenuBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        themeMenuDropdown.classList.toggle('hidden');
    });
    document.querySelectorAll('.theme-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const theme = e.currentTarget.dataset.theme;
            setTheme(theme);
            themeMenuDropdown.classList.add('hidden');
        });
    });
    window.addEventListener('click', () => {
        if (!themeMenuDropdown.classList.contains('hidden')) {
            themeMenuDropdown.classList.add('hidden');
        }
    });
}

// --- INITIALISERING (RETTET) ---

async function init() {
    console.log("DEBUG: init() started.");
    try {
        const response = await fetch('database_complete.json');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const rawData = await response.json();
        allBrands.clear();

        // Flad databasen UD FRA DEN OPRINDELIGE STRUKTUR
        if (rawData.length > 0 && Array.isArray(rawData[0].perfumes)) {
             allPerfumes = rawData.flatMap(brandObject => {
                 if (brandObject && Array.isArray(brandObject.perfumes)) {
                     const brandName = brandObject.brandInfo?.name || "Unknown Brand";
                     const brandInfo = brandObject.brandInfo || { name: brandName };
                     if (!allBrands.has(brandName)) {
                         allBrands.set(brandName, brandInfo);
                     }
                     // RETTET: Bevarer seasons og occasions arrays direkte
                     return brandObject.perfumes.map(perfume => ({
                         ...perfume,
                         brand: brandName,
                         // Sørg for at disse altid er arrays, selvom de mangler i JSON
                         seasons: perfume.seasons || [],
                         occasions: perfume.occasions || []
                     }));
                 }
                 return [];
             });
        } else {
             // Fallback for allerede flad struktur (just in case)
             allPerfumes = rawData.map(p => ({
                 ...p,
                 brand: p.brand || "Unknown Brand", // Sæt default brand hvis det mangler
                 seasons: p.seasons || [], // Sørg for array
                 occasions: p.occasions || [] // Sørg for array
             }));
             // Byg allBrands map fra flad struktur
             allPerfumes.forEach(p => {
                 if(p.brand && !allBrands.has(p.brand)) {
                     // Forsøg at finde brandInfo - ellers bare brug navnet
                     const brandInfoEntry = rawData.find(entry => entry.brandInfo?.name === p.brand);
                     allBrands.set(p.brand, brandInfoEntry?.brandInfo || { name: p.brand });
                 }
             });
        }


        // RETTET: Korrekt datarensning
        allPerfumes = allPerfumes.filter(p => p && p.code && p.inspiredBy).map(p => ({
            ...p,
            // brand er allerede sat ovenfor
            genderAffinity: String(p.genderAffinity || '').toLowerCase(), // Konverter til lowercase string
            mainAccords: (p.mainAccords || []).map(a => a.toLowerCase()),
            // RETTET: Gør seasons/occasions til lowercase strings INDE i arrayet
            seasons: (p.seasons || []).map(s => String(s).toLowerCase()).filter(s => s), // Fjern tomme strenge
            occasions: (p.occasions || []).map(o => String(o).toLowerCase()).filter(o => o), // Fjern tomme strenge
            notes: p.notes || { top: [], heart: [], base: [] }
            // Fjerner den forkerte bestSuitedFor logik
        }));

        console.log(`DEBUG: Total valid perfumes loaded: ${allPerfumes.length}`);
        // console.log("DEBUG: Sample cleaned perfume:", allPerfumes.find(p => p.seasons.length > 0 && p.occasions.length > 0));


    } catch (error) {
        console.error("ERROR: Could not load or parse perfume data:", error);
        document.getElementById('results-count').textContent = `Error: Could not load data.`;
        return;
    }

    loadFavorites();
    populateFilters(); // Skal nu virke korrekt
    applyFiltersAndRender(); // Startvisning
}

// --- EVENT LISTENERS (DOMContentLoade) (Uændret) ---

document.addEventListener('DOMContentLoaded', () => {
    init(); // Kører hoved-logik
    initTheme(); // Kører tema-logik

    // Mobil filter toggle
    document.getElementById('filters-toggle-btn').addEventListener('click', toggleMobileFilters);

    // Nulstil filter knapper (mobil + desktop)
    document.getElementById('reset-all-filters-btn-desktop').addEventListener('click', resetAllFilters);
    document.getElementById('reset-all-filters-btn-mobile').addEventListener('click', resetAllFilters);

    // Søgefelt-listener
    document.getElementById('search-input').addEventListener('input', e => {
        state.searchQuery = e.target.value;
        applyFiltersAndRender();
    });

    document.getElementById('sort-select').addEventListener('change', e => {
        state.sortBy = e.target.value;
        applyFiltersAndRender();
    });

    // Favoritknap-listener
    document.getElementById('favorites-btn').addEventListener('click', () => {
        state.showingFavorites = !state.showingFavorites;
        state.selectedBrand = null;

        const btn = document.getElementById('favorites-btn');
        if (state.showingFavorites) {
            btn.classList.add('bg-red-800');
        } else {
            btn.classList.remove('bg-red-800');
        }
        applyFiltersAndRender();
    });

    // Clear Brand Filter-knap
    document.getElementById('clear-brand-filter').addEventListener('click', () => {
        state.selectedBrand = null;
        applyFiltersAndRender();
    });

    // Modal Lyttere
    modalCloseBtn.addEventListener('click', hidePerfumeModal);
    modalOverlay.addEventListener('click', hidePerfumeModal);
    modalContent.addEventListener('click', (e) => e.stopPropagation());
});
