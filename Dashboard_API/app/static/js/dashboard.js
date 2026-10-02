/* dashboard.js — Shared utilities: clock, count-up, mobile sidebar, entrance animations */

// ── Global Fetch Interceptor to Unpack Standardized API Envelope ────
(function() {
  const originalFetch = window.fetch;
  window.fetch = async function(...args) {
    let url = args[0];
    if (typeof url === 'string' && url.includes('/api/')) {
      const pid = localStorage.getItem('selectedDataSource');
      if (pid && pid !== 'historical') {
        const sep = url.includes('?') ? '&' : '?';
        // Prevent double injection if it's already there
        if (!url.includes('prediction_id=')) {
          url = url + sep + 'prediction_id=' + encodeURIComponent(pid);
          args[0] = url;
        }
      }
    }
    
    const res = await originalFetch(...args);
    url = args[0]; // re-assign for the rest of the interceptor
    if (typeof url === 'string' && url.includes('/api/')) {
      const contentType = res.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        const clone = res.clone();
        try {
          const json = await clone.json();
          if (json && json.hasOwnProperty('success') && json.hasOwnProperty('data')) {
            // Return a native Response instance containing the unpacked data as body
            return new Response(JSON.stringify(json.data), {
              status: res.status,
              statusText: res.statusText,
              headers: res.headers
            });
          }
        } catch(e) {
          // fallback to original if parsing fails
        }
      }
    }
    return res;
  };
})();

// ── Live sidebar clock ─────────────────────────────────────────────
function updateSidebarClock() {
  const el = document.getElementById('sidebar-clock');
  if (!el) return;
  const now = new Date();
  const hh  = String(now.getHours()).padStart(2,'0');
  const mm  = String(now.getMinutes()).padStart(2,'0');
  const ss  = String(now.getSeconds()).padStart(2,'0');
  el.textContent = `${hh}:${mm}:${ss}`;
}
setInterval(updateSidebarClock, 1000);
updateSidebarClock();

// ── Topbar timestamp ───────────────────────────────────────────────
function updateTopbar() {
  const el = document.getElementById('last-updated');
  if (!el) return;
  const now = new Date();
  el.textContent = now.toLocaleString('en-GB', {
    day:'2-digit', month:'short', year:'numeric',
    hour:'2-digit', minute:'2-digit',
  });
}
updateTopbar();

// ── Count-up animation ─────────────────────────────────────────────
function animateCounter(el) {
  const target   = parseFloat(el.dataset.target || 0);
  const decimals = parseInt(el.dataset.decimals  || 0);
  const suffix   = el.dataset.suffix || '';
  const prefix   = el.dataset.prefix || '';
  const duration = 1600;
  const start    = performance.now();
  function step(ts) {
    const elapsed  = ts - start;
    const progress = Math.min(elapsed / duration, 1);
    // Ease out expo
    const ease = progress === 1 ? 1 : 1 - Math.pow(2, -10 * progress);
    el.textContent = prefix + (target * ease).toFixed(decimals) + suffix;
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

function runCounters() {
  document.querySelectorAll('.kpi-count').forEach(el => {
    const obs = new IntersectionObserver(entries => {
      entries.forEach(e => { if (e.isIntersecting) { animateCounter(el); obs.disconnect(); }});
    }, { threshold: 0.1 });
    obs.observe(el);
  });
}
document.addEventListener('DOMContentLoaded', runCounters);

// ── Card entrance stagger ──────────────────────────────────────────
function staggerCards() {
  document.querySelectorAll('.card, .kpi-card, .mini-kpi, .scenario-card, .model-card').forEach((el, i) => {
    el.style.animationDelay = `${i * 0.04}s`;
  });
}
document.addEventListener('DOMContentLoaded', staggerCards);

// ── Mobile sidebar ─────────────────────────────────────────────────
(function() {
  const toggle = document.getElementById('sidebar-toggle');
  if (!toggle) return;
  function checkWidth() {
    toggle.style.display = window.innerWidth <= 900 ? 'flex' : 'none';
  }
  window.addEventListener('resize', checkWidth);
  checkWidth();
})();

// ── Plotly default config/layout helpers (global) ─────────────────
window.PLOT_LAYOUT = {
  paper_bgcolor: 'rgba(0,0,0,0)',
  plot_bgcolor:  'rgba(0,0,0,0)',
  font: { family: 'Inter, sans-serif', color: '#8B95A7', size: 11 },
  margin: { t: 24, r: 24, b: 44, l: 52 },
  legend: { bgcolor: 'rgba(0,0,0,0)', font: { color: '#8B95A7', size: 11 } },
  xaxis: {
    gridcolor: 'rgba(255,255,255,0.045)',
    zerolinecolor: 'rgba(255,255,255,0.045)',
    tickfont: { size: 10 },
    linecolor: 'rgba(255,255,255,0.06)',
  },
  yaxis: {
    gridcolor: 'rgba(255,255,255,0.045)',
    zerolinecolor: 'rgba(255,255,255,0.045)',
    tickfont: { size: 10 },
    linecolor: 'rgba(255,255,255,0.06)',
  },
  hoverlabel: {
    bgcolor: '#0D1117',
    bordercolor: '#6C63FF',
    font: { family: 'Inter', color: '#EEF2FF', size: 12 },
  },
  transition: { duration: 400, easing: 'cubic-in-out' },
};

// Lighter config for heavy charts (disables WebGL overhead on large datasets)
window.PLOT_CONFIG        = { displayModeBar: false, responsive: true };
window.PLOT_CONFIG_STATIC = { displayModeBar: false, responsive: true, staticPlot: false };

// ── Shared "no-data" renderer — CSS animated icon ──────────────────
window.showNoData = function(containerId, title, subtitle) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = `
    <div class="no-data-state">
      <div class="nodata-anim">
        <span></span><span></span><span></span><span></span><span></span>
      </div>
      <div class="no-data-title">${title || 'No Data Available'}</div>
      <div class="no-data-sub">${subtitle || 'Try selecting a different city or disease combination.'}</div>
    </div>`;
};

// ── showError helper — CSS animated error icon ──────────────────────
window.showError = function(containerId, msg) {
  const el = document.getElementById(containerId);
  if (!el) return;
  el.innerHTML = `
    <div class="no-data-state">
      <div class="error-anim"></div>
      <div class="no-data-title">Failed to Load</div>
      <div class="no-data-sub">${msg || 'Please try refreshing the page.'}</div>
    </div>`;
};
