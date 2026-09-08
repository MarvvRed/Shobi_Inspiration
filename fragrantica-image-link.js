(() => {
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

  const style = document.createElement('style');
  style.textContent = `
    .v2-test-image-wrap.fragrantica-image-link { position:relative; cursor:pointer; transition:transform .18s ease, border-color .18s ease, box-shadow .18s ease; }
    .v2-test-image-wrap.fragrantica-image-link:hover { transform:translateY(-2px); border-color:#60a5fa; box-shadow:0 8px 20px rgba(37,99,235,.18); }
    .fragrantica-image-badge { position:absolute; left:6px; right:6px; bottom:6px; display:flex; align-items:center; justify-content:center; gap:4px; padding:5px 4px; border-radius:7px; background:rgba(15,23,42,.84); color:#fff; font-size:9px; font-weight:700; line-height:1; pointer-events:none; }
    .fragrantica-image-badge i { font-size:8px; }
  `;
  document.head.appendChild(style);

  const observer = new MutationObserver(enhancePerfumeImages);
  const start = () => {
    const container = document.getElementById('resultsContainer');
    if (!container) return;
    observer.observe(container, { childList:true, subtree:true });
    enhancePerfumeImages();
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();