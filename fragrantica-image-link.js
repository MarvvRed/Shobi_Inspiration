(() => {
  const recentCodes = new Set();
  let recentOnly = false;

  const normalizeCode = value => String(value || '').trim().toUpperCase();
  const getCardCode = card => normalizeCode(
    card.querySelector('.favorite-btn')?.dataset.code ||
    card.dataset.validationCode ||
    card.querySelector('[data-field="code"]')?.textContent
  );

  const enhancePerfumeImages = () => {
    document.querySelectorAll('#resultsContainer .v2-test-card').forEach(card => {
      const imageWrap = card.querySelector('.v2-test-image-wrap');
      if (!imageWrap || imageWrap.dataset.fragranticaEnhanced === '1') return;

      const shobiLink = card.querySelector('[data-field="shobiLink"]');
      const title = card.querySelector('[data-field="inspiredBy"]')?.textContent?.trim() || 'perfume';
      const code = card.querySelector('.favorite-btn')?.dataset.code || card.querySelector('[data-field="code"]')?.textContent?.trim();

      let perfume = null;
      if (typeof allPerfumes !== 'undefined' && Array.isArray(allPerfumes)) {
        perfume = allPerfumes.find(p => code && String(p.code || '').trim() === code) ||
                  allPerfumes.find(p => String(p.inspiredBy || '').trim().toUpperCase() === title.toUpperCase());
      }

      const fragranticaId = String(perfume?.fragranticaId || perfume?.fragrantica_id || '').trim();
      const fragranticaUrl = perfume?.fragranticaUrl || perfume?.fragranticaLocalUrl || perfume?.fragranticaURL || perfume?.fragrantica_url ||
        (/^\d+$/.test(fragranticaId) ? `https://www.fragrantica.com/p/${fragranticaId}` : '');
      if (!fragranticaUrl) return;

      imageWrap.dataset.fragranticaEnhanced = '1';
      imageWrap.classList.add('fragrantica-image-link');
      imageWrap.setAttribute('role', 'link');
      imageWrap.setAttribute('tabindex', '0');
      imageWrap.setAttribute('aria-label', `View ${title} on Fragrantica`);
      imageWrap.setAttribute('title', 'View on Fragrantica');

      const badge = document.createElement('span');
      badge.className = 'fragrantica-image-badge';
      badge.innerHTML = '<i class="fas fa-arrow-up-right-from-square" aria-hidden="true"></i> Fragrantica';
      imageWrap.appendChild(badge);

      const openFragrantica = event => {
        event.preventDefault();
        event.stopPropagation();
        window.open(fragranticaUrl, '_blank', 'noopener,noreferrer');
      };
      imageWrap.addEventListener('click', openFragrantica);
      imageWrap.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') openFragrantica(event);
      });
    });
  };

  const enhanceRecentBadges = () => {
    if (!recentCodes.size) return;
    document.querySelectorAll('#resultsContainer .v2-test-card').forEach(card => {
      if (card.dataset.recentEnhanced === '1') return;
      const code = getCardCode(card);
      if (!recentCodes.has(code)) return;

      const body = card.firstElementChild;
      if (!body) return;

      const badge = document.createElement('span');
      badge.className = 'recent-addition-badge';
      badge.textContent = 'Nuovo';
      badge.title = 'Aggiunto di recente al catalogo Shobi';
      badge.setAttribute('aria-label', badge.title);
      body.insertBefore(badge, body.firstChild);
      card.dataset.recentEnhanced = '1';
    });
  };

  const syncRecentFilterUi = () => {
    const checkbox = document.getElementById('recent-additions-filter');
    if (checkbox) checkbox.checked = recentOnly;
  };

  const installRecentFilter = () => {
    if (!recentCodes.size || document.getElementById('recent-additions-filter')) return;
    const filtersContent = document.getElementById('filters-content');
    if (!filtersContent) return;

    const firstGroup = filtersContent.querySelector('.filter-group');
    if (!firstGroup) return;

    const group = document.createElement('div');
    group.className = 'filter-group mb-6 lg:px-6';
    group.innerHTML = `
      <h4 class="font-semibold text-primary mb-2">Catalogo</h4>
      <label class="recent-filter-label">
        <input id="recent-additions-filter" type="checkbox" name="recent-additions" value="recent">
        <span>Aggiunti di recente</span>
        <span class="recent-filter-count">${recentCodes.size}</span>
      </label>
    `;
    filtersContent.insertBefore(group, firstGroup);

    group.querySelector('#recent-additions-filter')?.addEventListener('change', event => {
      recentOnly = Boolean(event.currentTarget.checked);
      if (typeof applyFiltersAndRender === 'function') applyFiltersAndRender();
    });
  };

  const installRecentFiltering = () => {
    if (typeof getFilteredPerfumes !== 'function' || getFilteredPerfumes.__recentWrapped) return;
    const originalGetFilteredPerfumes = getFilteredPerfumes;
    const wrapped = function(overrideFilters = null) {
      const result = originalGetFilteredPerfumes.call(this, overrideFilters);
      if (overrideFilters || !recentOnly) return result;
      return result.filter(perfume => recentCodes.has(normalizeCode(perfume?.code)));
    };
    wrapped.__recentWrapped = true;
    getFilteredPerfumes = wrapped;

    if (typeof resetAllFilters === 'function' && !resetAllFilters.__recentWrapped) {
      const originalResetAllFilters = resetAllFilters;
      const resetWrapped = function(...args) {
        recentOnly = false;
        syncRecentFilterUi();
        return originalResetAllFilters.apply(this, args);
      };
      resetWrapped.__recentWrapped = true;
      resetAllFilters = resetWrapped;
    }
  };

  const style = document.createElement('style');
  style.textContent = `
    .v2-test-image-wrap.fragrantica-image-link { position:relative; cursor:pointer; transition:transform .18s ease, border-color .18s ease, box-shadow .18s ease; }
    .v2-test-image-wrap.fragrantica-image-link:hover { transform:translateY(-2px); border-color:#60a5fa; box-shadow:0 8px 20px rgba(37,99,235,.18); }
    .fragrantica-image-badge { position:absolute; left:6px; right:6px; bottom:6px; display:flex; align-items:center; justify-content:center; gap:4px; padding:5px 4px; border-radius:7px; background:rgba(15,23,42,.84); color:#fff; font-size:9px; font-weight:700; line-height:1; pointer-events:none; }
    .fragrantica-image-badge i { font-size:8px; }
    .recent-addition-badge { align-self:flex-start; display:inline-flex; align-items:center; margin:0 0 8px; padding:4px 9px; border-radius:999px; background:#eff6ff; border:1px solid #60a5fa; color:#1d4ed8; font-size:12px; font-weight:800; line-height:1; letter-spacing:.02em; text-transform:uppercase; }
    [data-theme="dark"] .recent-addition-badge { background:#172554; border-color:#3b82f6; color:#bfdbfe; }
    .recent-filter-label { display:flex; align-items:center; gap:.55rem; cursor:pointer; color:var(--text-secondary, inherit); }
    .recent-filter-count { margin-left:auto; display:inline-flex; min-width:1.55rem; height:1.35rem; align-items:center; justify-content:center; padding:0 .35rem; border-radius:999px; background:#eff6ff; color:#1d4ed8; font-size:.72rem; font-weight:800; }
    [data-theme="dark"] .recent-filter-count { background:#172554; color:#bfdbfe; }
  `;
  document.head.appendChild(style);

  const enhanceAll = () => {
    enhancePerfumeImages();
    enhanceRecentBadges();
  };

  const observer = new MutationObserver(enhanceAll);
  const start = async () => {
    const container = document.getElementById('resultsContainer');
    if (!container) return;

    try {
      const response = await fetch('database/catalog/recent-additions.json', { cache: 'no-store' });
      if (response.ok) {
        const data = await response.json();
        (Array.isArray(data.codes) ? data.codes : []).forEach(code => recentCodes.add(normalizeCode(code)));
      }
    } catch (error) {
      console.warn('Recent additions metadata is not available.', error);
    }

    installRecentFiltering();
    installRecentFilter();
    observer.observe(container, { childList:true, subtree:true });
    enhanceAll();
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();