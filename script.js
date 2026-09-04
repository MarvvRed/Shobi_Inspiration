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
        accords: [],
        notes: []
    }
};

const TOKEN_COLORS = {
    gender: 'token-gender',
    brands: 'token-brand',
    season: 'token-season',
    occasion: 'token-occasion',
    accords: 'token-accord',
    notes: 'token-accord'
};

function displayPerfumes(perfumes) {
    const container = document.getElementById('resultsContainer');
    const template = document.getElementById('perfume-card-template');
    const resultsCountEl = document.getElementById('results-count');

    container.innerHTML = '';

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

    perfumes.forEach(perfume => {
        const p = perfume.item ? perfume.item : perfume;
        const card = template.content.cloneNode(true);
        const isFavorite = state.favorites.includes(p.code);

        card.querySelector('[data-field="code"]').textContent = p.code;
        card.querySelector('[data-field="inspiredBy"]').textContent = p.inspiredBy;
        card.querySelector('[data-field="brand"]').textContent = p.brand;

        const shobiLink = `https://leparfum.com.gr/en/module/iqitsearch/searchiqit?s=${p.code}`;
        card.querySelector('[data-field="shobiLink"]').href = shobiLink;

        const favButton = card.querySelector('.favorite-btn');
        favButton.dataset.code = p.code;
        favButton.innerHTML = isFavorite ? '<i class="fa-solid fa-heart"></i>' : '<i class="fa-regular fa-heart"></i>';
        if (isFavorite) favButton.classList.add('is-favorite');

        const audienceIconsContainer = card.querySelector('[data-field="audience-icons"]');
        audienceIconsContainer.innerHTML = getAudienceIcons(p.genderAffinity);
        const mainNotesContainer = card.querySelector('[data-field="main-notes"]');
        mainNotesContainer.innerHTML = getMainNotesBadges(p.notes);

        card.querySelector('[data-action="filter-brand"]').dataset.brand = p.brand;
        container.appendChild(card);
    });

    container.querySelectorAll('.favorite-btn').forEach(btn =>
        btn.addEventListener('click', toggleFavorite)
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

function applyFiltersAndRender() {
    const filteredPerfumes = getFilteredPerfumes();
    displayBrandInfo();
    displayPerfumes(filteredPerfumes);
    updateAvailableFilterOptions();
    displayActiveFilterTokens();
}

function getFilteredPerfumes(overrideFilters = null) {
    let filtered = [...allPerfumes];
    const currentFilters = overrideFilters || state.activeFilters;

    if (state.selectedBrand && !overrideFilters) {
        filtered = filtered.filter(p => p.brand === state.selectedBrand);
    } else if (currentFilters.brands.length > 0) {
        filtered = filtered.filter(p => currentFilters.brands.includes(p.brand));
    } else if (state.showingFavorites && !overrideFilters) {
        filtered = filtered.filter(p => state.favorites.includes(p.code));
    }

    if (currentFilters.gender.length > 0) {
        filtered = filtered.filter(p => currentFilters.gender.some(filterGender => p.genderAffinity.includes(filterGender)));
    }

    if (currentFilters.season.length > 0) {
        filtered = filtered.filter(p => currentFilters.season.some(filterSeason => p.seasons.includes(filterSeason)));
    }

    if (currentFilters.occasion.length > 0) {
        filtered = filtered.filter(p => currentFilters.occasion.some(filterOccasion => p.occasions.includes(filterOccasion)));
    }

    if (currentFilters.accords.length > 0) {
        filtered = filtered.filter(p => currentFilters.accords.every(filterAccord => p.mainAccords.includes(filterAccord)));
    }

    if (currentFilters.notes.length > 0) {
        filtered = filtered.filter(p => {
            const perfumeNotes = getPerfumeNotes(p.notes);
            return currentFilters.notes.every(filterNote => perfumeNotes.includes(filterNote));
        });
    }

    if (state.searchQuery && !overrideFilters) {
        const query = state.searchQuery.toLowerCase();
        filtered = filtered.filter(p =>
            String(p.inspiredBy || '').toLowerCase().includes(query) ||
            String(p.brand || '').toLowerCase().includes(query) ||
            String(p.code || '').toLowerCase().includes(query)
        );
    }

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

function updateAvailableFilterOptions() {
    document.querySelectorAll('#filter-sidebar input[type="checkbox"]').forEach(checkbox => {
        let filterType;
        switch(checkbox.name) {
            case 'gender': filterType = 'gender'; break;
            case 'brand': filterType = 'brands'; break;
            case 'season': filterType = 'season'; break;
            case 'occasion': filterType = 'occasion'; break;
            case 'accord': filterType = 'accords'; break;
            default: return;
        }
        const value = checkbox.value;
        const label = checkbox.closest('label');

        if (checkbox.checked) {
            checkbox.disabled = false;
            if (label) label.classList.remove('disabled');
            return;
        }

        const simulatedFilters = JSON.parse(JSON.stringify(state.activeFilters));
        simulatedFilters[filterType].push(value);
        const simulationResult = getFilteredPerfumes(simulatedFilters);

        if (simulationResult.length > 0) {
            checkbox.disabled = false;
            if (label) label.classList.remove('disabled');
        } else {
            checkbox.disabled = true;
            if (label) label.classList.add('disabled');
        }
    });
}

function displayActiveFilterTokens() {
    const container = document.getElementById('active-filters-display');
    container.innerHTML = '';
    let hasTokens = false;

    if (state.selectedBrand) {
        hasTokens = true;
        const token = document.createElement('span');
        token.className = 'filter-token token-brand';
        token.innerHTML = `
            Brand: ${escapeHtml(state.selectedBrand)}
            <button data-filter-type="selectedBrand" data-filter-value="${escapeHtml(state.selectedBrand)}" title="Remove brand filter">&times;</button>
        `;
        container.appendChild(token);
    }

    for (const filterType in state.activeFilters) {
        state.activeFilters[filterType].forEach(value => {
            hasTokens = true;
            const token = document.createElement('span');
            const displayValue = value.charAt(0).toUpperCase() + value.slice(1);
            token.className = `filter-token ${TOKEN_COLORS[filterType] || 'token-default'}`;
            token.innerHTML = `
                ${displayValue}
                <button data-filter-type="${filterType}" data-filter-value="${value}" title="Remove filter">&times;</button>
            `;
            container.appendChild(token);
        });
    }

    container.style.display = hasTokens ? 'flex' : 'none';
    container.querySelectorAll('button').forEach(button => {
        button.addEventListener('click', handleRemoveToken);
    });
}

function handleRemoveToken(e) {
    const button = e.currentTarget;
    const filterType = button.dataset.filterType;
    const value = button.dataset.filterValue;

    if (filterType === 'selectedBrand') {
        state.selectedBrand = null;
        applyFiltersAndRender();
        return;
    }

    const index = state.activeFilters[filterType].indexOf(value);
    if (index > -1) {
        state.activeFilters[filterType].splice(index, 1);
    }

    let checkboxName;
    switch(filterType) {
        case 'brands': checkboxName = 'brand'; break;
        case 'accords': checkboxName = 'accord'; break;
        default: checkboxName = filterType;
    }
    const checkbox = document.querySelector(`#filter-sidebar input[name="${checkboxName}"][value="${value}"]`);
    if (checkbox) checkbox.checked = false;
    applyFiltersAndRender();
}

function displayBrandInfo() {
    const container = document.getElementById('brand-info-container');
    const contentEl = document.getElementById('brand-info-content');
    if (!container || !contentEl) return;

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
    state.selectedBrand = brandName;
    state.showingFavorites = false;
    state.activeFilters.brands = [];
    document.querySelectorAll('#brand-filters input[type="checkbox"]').forEach(cb => cb.checked = false);
    document.getElementById('favorites-btn')?.classList.remove('bg-red-800');
    applyFiltersAndRender();
}

function handleIconFilterClick(filterType, filterValue) {
    const stateKey = filterType === 'accord' ? 'accords' : filterType === 'note' ? 'notes' : filterType;

    if (filterType === 'note') {
        if (!state.activeFilters.notes.includes(filterValue)) {
            state.activeFilters.notes.push(filterValue);
        }
        applyFiltersAndRender();
        return;
    }

    const filtersContent = document.getElementById('filters-content');
    if (filtersContent.classList.contains('hidden') && window.innerWidth < 1024) {
        toggleMobileFilters();
    }

    const checkboxName = filterType === 'accord' ? 'accord' : filterType;
    const checkbox = document.querySelector(`#filter-sidebar input[name="${checkboxName}"][value="${filterValue}"]`);
    if (checkbox && !checkbox.checked) {
        checkbox.checked = true;
        checkbox.dispatchEvent(new Event('change', { bubbles: true }));
    }
}

function getAudienceIcons(audience) {
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
    if (!Array.isArray(accords) || accords.length === 0) return '';
    let iconsHtml = [];
    const addedIcons = new Set();
    const lowerCaseAccords = accords.map(a => a.toLowerCase());

    for (const key in SCENT_ICON_MAP) {
        if (!addedIcons.has(key) && lowerCaseAccords.some(accord => accord.includes(key))) {
            const iconData = SCENT_ICON_MAP[key];
            iconsHtml.push(`<span data-action="filter-icon" data-filter-type="accord" data-filter-value="${iconData.value}">${iconData.icon}</span>`);
            addedIcons.add(key);
        }
    }
    return iconsHtml.join(' ');
}

function escapeHtml(value) {
    return String(value)
        .replaceAll('&', '&amp;')
        .replaceAll('<', '&lt;')
        .replaceAll('>', '&gt;')
        .replaceAll('"', '&quot;')
        .replaceAll("'", '&#039;');
}

function getPerfumeNotes(notes) {
    if (!notes || typeof notes !== 'object') return [];
    return [...new Set(['top', 'heart', 'base'].flatMap(level =>
        Array.isArray(notes[level]) ? notes[level].filter(Boolean) : []
    ))];
}

function getMainNotesBadges(notes) {
    const mainNotes = getPerfumeNotes(notes);
    if (mainNotes.length === 0) {
        return '<span class="text-sm text-tertiary">No notes available</span>';
    }

    return mainNotes.map(note => {
        const value = escapeHtml(note);
        const label = escapeHtml(note);
        return `<button type="button" data-action="filter-icon" data-filter-type="note" data-filter-value="${value}" class="main-note-badge rounded-full px-3 py-1 text-xs font-medium transition focus-ring" title="Filter by ${label}">${label}</button>`;
    }).join('');
}

function toggleFavorite(event) {
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

    if (state.showingFavorites) applyFiltersAndRender();
}

function loadFavorites() {
    const savedFavorites = localStorage.getItem('shobi-favorites');
    if (savedFavorites) state.favorites = JSON.parse(savedFavorites);
    document.getElementById('favorites-count').textContent = state.favorites.length;
}

function toggleMobileFilters() {
    const filtersContent = document.getElementById('filters-content');
    const filtersIcon = document.getElementById('filters-toggle-icon');
    filtersContent.classList.toggle('hidden');
    filtersIcon.classList.toggle('rotate-180');
}

function resetAllFilters() {
    state.searchQuery = '';
    state.showingFavorites = false;
    state.selectedBrand = null;
    state.activeFilters = {
        gender: [],
        brands: [],
        season: [],
        occasion: [],
        accords: [],
        notes: []
    };
    document.getElementById('search-input').value = '';
    document.getElementById('favorites-btn')?.classList.remove('bg-red-800');
    document.querySelectorAll('#filter-sidebar input[type="checkbox"]').forEach(checkbox => {
        checkbox.checked = false;
        checkbox.disabled = false;
        checkbox.closest('label')?.classList.remove('disabled');
    });
    applyFiltersAndRender();
}

function populateFilters() {
    const genderContainer = document.getElementById('gender-filters');
    const brandContainer = document.getElementById('brand-filters');
    const seasonContainer = document.getElementById('season-filters');
    const occasionContainer = document.getElementById('occasion-filters');
    const accordContainer = document.getElementById('accord-filters');

    const buildCheckboxes = (container, name, options, loaderId) => {
        if (!container) return;
        const sortedOptions = Array.from(options).sort();

        if (sortedOptions.length === 0) {
            container.innerHTML = `<p class="text-sm text-tertiary">No data found.</p>`;
        } else {
            container.innerHTML = sortedOptions.map(option => {
                if (!option) return '';
                const capitalized = option.charAt(0).toUpperCase() + option.slice(1);
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
        document.getElementById(loaderId)?.remove();
    };

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

    buildCheckboxes(brandContainer, 'brand', allBrands.keys(), 'brand-loader');

    const allSeasons = new Set(allPerfumes.flatMap(p => p.seasons));
    buildCheckboxes(seasonContainer, 'season', allSeasons, 'season-loader');

    const allOccasions = new Set(allPerfumes.flatMap(p => p.occasions));
    buildCheckboxes(occasionContainer, 'occasion', allOccasions, 'occasion-loader');

    const allAccords = new Set(allPerfumes.flatMap(p => p.mainAccords));
    buildCheckboxes(accordContainer, 'accord', allAccords, 'accord-loader');

    document.querySelectorAll('#filter-sidebar input[type="checkbox"]').forEach(checkbox => {
        checkbox.addEventListener('change', handleCheckboxChange);
    });
}

function handleCheckboxChange(e) {
    let filterType;
    switch(e.target.name) {
        case 'gender': filterType = 'gender'; break;
        case 'brand': filterType = 'brands'; break;
        case 'season': filterType = 'season'; break;
        case 'occasion': filterType = 'occasion'; break;
        case 'accord': filterType = 'accords'; break;
        default: return;
    }

    const value = e.target.value;

    if (e.target.checked) {
        if (!state.activeFilters[filterType].includes(value)) {
            state.activeFilters[filterType].push(value);
        }
        if (filterType === 'brands') state.selectedBrand = null;
    } else {
        const index = state.activeFilters[filterType].indexOf(value);
        if (index > -1) state.activeFilters[filterType].splice(index, 1);
    }
    applyFiltersAndRender();
}

function setTheme(theme) {
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
    const savedTheme = localStorage.getItem('shobi-theme');
    if (savedTheme) setTheme(savedTheme);
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

async function init() {
    console.log("DEBUG: init() started.");
    try {
        const response = await fetch('database_complete.json');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);

        const rawData = await response.json();
        allBrands.clear();

        if (rawData.length > 0 && Array.isArray(rawData[0].perfumes)) {
            allPerfumes = rawData.flatMap(brandObject => {
                if (brandObject && Array.isArray(brandObject.perfumes)) {
                    const brandName = brandObject.brandInfo?.name || "Unknown Brand";
                    const brandInfo = brandObject.brandInfo || { name: brandName };
                    if (!allBrands.has(brandName)) allBrands.set(brandName, brandInfo);
                    return brandObject.perfumes.map(perfume => ({
                        ...perfume,
                        brand: brandName,
                        seasons: perfume.seasons || [],
                        occasions: perfume.occasions || []
                    }));
                }
                return [];
            });
        } else {
            allPerfumes = rawData.map(p => ({
                ...p,
                brand: p.brand || "Unknown Brand",
                seasons: p.seasons || [],
                occasions: p.occasions || []
            }));
            allPerfumes.forEach(p => {
                if(p.brand && !allBrands.has(p.brand)) {
                    const brandInfoEntry = rawData.find(entry => entry.brandInfo?.name === p.brand);
                    allBrands.set(p.brand, brandInfoEntry?.brandInfo || { name: p.brand });
                }
            });
        }

        allPerfumes = allPerfumes.filter(p => p && p.code && p.inspiredBy).map(p => ({
            ...p,
            genderAffinity: String(p.genderAffinity || '').toLowerCase(),
            mainAccords: (p.mainAccords || []).map(a => a.toLowerCase()),
            seasons: (p.seasons || []).map(s => String(s).toLowerCase()).filter(s => s),
            occasions: (p.occasions || []).map(o => String(o).toLowerCase()).filter(o => o),
            notes: p.notes || { top: [], heart: [], base: [] }
        }));

        console.log(`DEBUG: Total valid perfumes loaded: ${allPerfumes.length}`);
    } catch (error) {
        console.error("ERROR: Could not load or parse perfume data:", error);
        document.getElementById('results-count').textContent = `Error: Could not load data.`;
        return;
    }

    loadFavorites();
    populateFilters();
    applyFiltersAndRender();
}

document.addEventListener('DOMContentLoaded', () => {
    init();
    initTheme();

    document.getElementById('filters-toggle-btn').addEventListener('click', toggleMobileFilters);
    document.getElementById('reset-all-filters-btn-desktop').addEventListener('click', resetAllFilters);
    document.getElementById('reset-all-filters-btn-mobile').addEventListener('click', resetAllFilters);

    document.getElementById('search-input').addEventListener('input', e => {
        state.searchQuery = e.target.value;
        applyFiltersAndRender();
    });

    document.getElementById('sort-select').addEventListener('change', e => {
        state.sortBy = e.target.value;
        applyFiltersAndRender();
    });

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

    const clearBrandFilter = document.getElementById('clear-brand-filter');
    if (clearBrandFilter) {
        clearBrandFilter.addEventListener('click', () => {
            state.selectedBrand = null;
            applyFiltersAndRender();
        });
    }
});
