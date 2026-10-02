/* ═══════════════════════════════════════════════════════════════════
   EpiGuard Africa — SPA Core  (v2 — fixed data + animations)
   ═══════════════════════════════════════════════════════════════════ */

/* ══════════════════════════════════════════════════════════════════
   1. STARFIELD
   ══════════════════════════════════════════════════════════════════ */
class Starfield {
  constructor(id) {
    this.cv  = document.getElementById(id);
    this.ctx = this.cv.getContext('2d');
    this.stars = []; this.shooters = [];
    this._resize(); this._init();
    window.addEventListener('resize', () => { this._resize(); this._init(); });
    this._frame();
  }
  _resize() { this.W = this.cv.width = innerWidth; this.H = this.cv.height = innerHeight; }
  _init() {
    this.stars = Array.from({length:280}, () => ({
      x: Math.random()*this.W, y: Math.random()*this.H,
      r: Math.random()*1.6+0.15,
      ph: Math.random()*Math.PI*2, sp: Math.random()*.004+.001,
      dx: (Math.random()-.5)*.04,
    }));
  }
  _shooter() {
    const a = Math.PI/4 + (Math.random()-.5)*.7;
    this.shooters.push({ x:Math.random()*this.W*.8, y:Math.random()*this.H*.3,
      len:Math.random()*90+50, spd:Math.random()*9+5, angle:a, alpha:1 });
  }
  _frame() {
    const ctx = this.ctx;
    ctx.clearRect(0,0,this.W,this.H);
    // nebula
    const n1 = ctx.createRadialGradient(this.W*.15,this.H*.2,0,this.W*.15,this.H*.2,this.W*.38);
    n1.addColorStop(0,'rgba(108,99,255,.028)'); n1.addColorStop(1,'transparent');
    ctx.fillStyle = n1; ctx.fillRect(0,0,this.W,this.H);
    const n2 = ctx.createRadialGradient(this.W*.85,this.H*.78,0,this.W*.85,this.H*.78,this.W*.3);
    n2.addColorStop(0,'rgba(0,212,255,.022)'); n2.addColorStop(1,'transparent');
    ctx.fillStyle = n2; ctx.fillRect(0,0,this.W,this.H);
    // stars
    this.stars.forEach(s => {
      s.ph += s.sp; s.x += s.dx;
      if (s.x>this.W) s.x=0; if (s.x<0) s.x=this.W;
      const a = (Math.sin(s.ph)+1)/2*.72+.1;
      ctx.beginPath(); ctx.arc(s.x,s.y,s.r,0,Math.PI*2);
      ctx.fillStyle = `rgba(255,255,255,${a.toFixed(2)})`; ctx.fill();
      if (s.r>1.3 && a>.72) {
        ctx.beginPath();
        ctx.moveTo(s.x-s.r*3.5,s.y); ctx.lineTo(s.x+s.r*3.5,s.y);
        ctx.moveTo(s.x,s.y-s.r*3.5); ctx.lineTo(s.x,s.y+s.r*3.5);
        ctx.strokeStyle = `rgba(255,255,255,${(a*.28).toFixed(2)})`; ctx.lineWidth=.5; ctx.stroke();
      }
    });
    // shooting stars
    this.shooters = this.shooters.filter(s=>s.alpha>0);
    this.shooters.forEach(s => {
      s.x+=Math.cos(s.angle)*s.spd; s.y+=Math.sin(s.angle)*s.spd; s.alpha-=.018;
      const x0=s.x-Math.cos(s.angle)*s.len, y0=s.y-Math.sin(s.angle)*s.len;
      const g=ctx.createLinearGradient(x0,y0,s.x,s.y);
      g.addColorStop(0,'rgba(255,255,255,0)');
      g.addColorStop(.8,`rgba(200,230,255,${(s.alpha*.55).toFixed(2)})`);
      g.addColorStop(1,`rgba(255,255,255,${s.alpha.toFixed(2)})`);
      ctx.beginPath(); ctx.moveTo(x0,y0); ctx.lineTo(s.x,s.y);
      ctx.strokeStyle=g; ctx.lineWidth=1.7; ctx.stroke();
    });
    if (Math.random()<.004) this._shooter();
    requestAnimationFrame(()=>this._frame());
  }
}
new Starfield('stars');

/* ══════════════════════════════════════════════════════════════════
   2. CLOCK
   ══════════════════════════════════════════════════════════════════ */
function tick() {
  const t = new Date().toLocaleTimeString('en-GB');
  ['hero-clock','ov-clock','al-clock','sc-clock','mo-clock','ex-clock']
    .forEach(id => { const e=document.getElementById(id); if(e) e.textContent=t; });
}
setInterval(tick,1000); tick();

/* ══════════════════════════════════════════════════════════════════
   3. NAVIGATION
   ══════════════════════════════════════════════════════════════════ */
const SECS  = ['hero','overview','alerts','scenarios','models','explorer'];
let   CUR   = 'hero';
let   BUSY  = false;

function goto(id, noHist) {
  if (!SECS.includes(id) || id===CUR || BUSY) return;
  BUSY = true;

  const from = document.getElementById('sec-'+CUR);
  const to   = document.getElementById('sec-'+id);
  to.scrollTop = 0;

  from.classList.add('leaving');
  from.classList.remove('active');
  setTimeout(()=>{ to.classList.add('active'); },30);
  setTimeout(()=>{ from.classList.remove('leaving'); BUSY=false; _enter(id); },620);

  _nav(id); _dots(id); CUR=id;
  if (!noHist) history.pushState({s:id},'','#'+id);
}

function _nav(id) {
  document.getElementById('fnav').classList.toggle('gone', id==='hero');
  document.querySelectorAll('.fnav-btn').forEach(b=>b.classList.toggle('on',b.dataset.s===id));
}
function _dots(id) {
  document.querySelectorAll('.rdot').forEach(d=>d.classList.toggle('on',d.dataset.t===id));
}
window.addEventListener('popstate', e => goto(e.state?.s||'hero',true));
document.addEventListener('keydown', e => {
  if (e.key==='ArrowDown'||e.key==='ArrowRight') goto(SECS[Math.min(SECS.indexOf(CUR)+1,5)]);
  if (e.key==='ArrowUp'  ||e.key==='ArrowLeft')  goto(SECS[Math.max(SECS.indexOf(CUR)-1,0)]);
});
// init from hash
(function(){
  const h=location.hash.replace('#','');
  if (SECS.includes(h)&&h!=='hero'){ _nav(h); _dots(h); }
  else { _nav('hero'); _dots('hero'); }
})();

/* ══════════════════════════════════════════════════════════════════
   4. LAZY LOADING
   ══════════════════════════════════════════════════════════════════ */
const LOADED = new Set();
function _enter(s) {
  if (LOADED.has(s)) return;
  LOADED.add(s);
  ({overview:loadOverview,alerts:loadAlerts,scenarios:loadScenarios,
    models:loadModels,explorer:loadExplorer}[s]||_noop)();
}
function _noop(){}

// Pre-load overview after 900ms so it's ready when user clicks
setTimeout(()=>{ if(!LOADED.has('overview')){ LOADED.add('overview'); loadOverview(); } },900);

/* ══════════════════════════════════════════════════════════════════
   5. PLOTLY HELPERS
   ══════════════════════════════════════════════════════════════════ */
const BASE_LAYOUT = {
  paper_bgcolor:'rgba(0,0,0,0)', plot_bgcolor:'rgba(0,0,0,0)',
  font:{family:'Inter,sans-serif',color:'#8B95A7',size:11},
  margin:{t:16,r:22,b:44,l:52},
  xaxis:{gridcolor:'rgba(255,255,255,0.045)',zerolinecolor:'rgba(255,255,255,0.045)',
         tickfont:{color:'#8B95A7',size:10}},
  yaxis:{gridcolor:'rgba(255,255,255,0.045)',zerolinecolor:'rgba(255,255,255,0.045)',
         tickfont:{color:'#8B95A7',size:10}},
  hoverlabel:{bgcolor:'#111827',bordercolor:'rgba(108,99,255,.5)',
              font:{color:'#EEF2FF',family:'Inter,sans-serif'}},
  autosize:true, showlegend:false,
};
const PC = {responsive:true,displayModeBar:false};
const ALC = {Normal:'#6B7280',Watch:'#3B82F6',Warning:'#F59E0B',Emergency:'#EF4444'};

function prep(id) {
  const el = document.getElementById(id);
  if (!el) return null;
  Plotly.purge(el); el.innerHTML=''; return el;
}
function spin(id) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = '<div class="spin-box"><div class="spa-spin"></div></div>';
}
function noD(id,title,sub) {
  const el = document.getElementById(id);
  if (el) el.innerHTML = `<div class="no-d"><div class="no-d-icon">📊</div><div class="no-d-title">${title}</div><div class="no-d-sub">${sub||''}</div></div>`;
}
function lay(extra) { return Object.assign({},BASE_LAYOUT,extra); }

/* ══════════════════════════════════════════════════════════════════
   6. OVERVIEW
   ══════════════════════════════════════════════════════════════════ */
async function loadOverview() {
  try {
    const d = await _get('/api/overview');

    // KPIs
    _count('kv-det',  d.kpis.scenarios_detected);
    _count('kv-lead', d.kpis.avg_lead_time, 2);
    _count('kv-rate', d.kpis.detection_rate_pct, 1, '%');
    _count('kv-cities',d.kpis.cities_monitored);

    // Donut — alert level distribution
    const el1 = prep('ch-donut');
    if (el1) {
      Plotly.newPlot(el1,[{
        type:'pie', labels:d.donut.labels, values:d.donut.values, hole:.54,
        marker:{colors:d.donut.labels.map(l=>ALC[l])},
        textinfo:'label+percent', textposition:'outside',
        textfont:{color:'#EEF2FF',size:10},
        hovertemplate:'<b>%{label}</b><br>%{value} alerts (%{percent})<extra></extra>',
      }], lay({
        margin:{t:10,r:100,b:10,l:10}, height:240, showlegend:true,
        legend:{orientation:'v',x:1.02,y:.5,bgcolor:'rgba(0,0,0,0)',font:{color:'#8B95A7',size:10}},
        annotations:[{text:'<b>Alerts</b>',x:.5,y:.5,showarrow:false,
          font:{size:13,color:'#EEF2FF',family:'Oswald,sans-serif'}}],
      }), PC);
    }

    // Lead time horizontal bar
    const el2 = prep('ch-lead');
    if (el2) {
      const lt=d.lead_time;
      const cols=lt.values.map(v=>v<1?'#EF4444':v<3?'#F59E0B':'#10B981');
      Plotly.newPlot(el2,[{
        type:'bar', orientation:'h', x:lt.values, y:lt.labels,
        marker:{color:cols,opacity:.88},
        text:lt.values.map(v=>v.toFixed(1)+'w'), textposition:'outside',
        textfont:{color:'#EEF2FF',size:9},
        hovertemplate:'<b>%{y}</b><br>Lead Time: %{x:.2f} weeks<extra></extra>',
      }], lay({
        height:240, margin:{t:10,r:55,b:30,l:185},
        xaxis:{...BASE_LAYOUT.xaxis,title:{text:'Weeks',font:{size:11}},
               range:[0,Math.max(...lt.values)*1.4]},
        yaxis:{...BASE_LAYOUT.yaxis,automargin:true,tickfont:{size:9,color:'#8B95A7'}},
      }), PC);
    }

    // Precision bar
    const el3 = prep('ch-prec');
    if (el3) {
      const pr=d.precision;
      Plotly.newPlot(el3,[{
        type:'bar', x:pr.labels, y:pr.values,
        marker:{color:pr.labels.map(l=>ALC[l]),opacity:.88},
        text:pr.values.map(v=>v+'%'), textposition:'outside',
        textfont:{color:'#EEF2FF',size:11},
        hovertemplate:'<b>%{x}</b>: %{y}%<extra></extra>',
      }], lay({
        height:240, yaxis:{...BASE_LAYOUT.yaxis,title:{text:'Precision (%)'},range:[0,115]},
      }), PC);
    }

    // Bubble
    const el4 = prep('ch-bubble');
    if (el4) {
      const b=d.bubble;
      Plotly.newPlot(el4,[{
        type:'scatter', mode:'markers+text',
        x:b.x, y:b.y,
        text:b.labels.map(l=>l.split('/')[0].trim()),
        textposition:'top center', textfont:{size:9,color:'#8B95A7'},
        marker:{size:b.size.map(s=>Math.max(10,Math.min(44,Math.sqrt(s/28)))),
                color:b.alert_levels.map(l=>ALC[l]||'#6B7280'),opacity:.85,
                line:{color:'rgba(255,255,255,0.1)',width:1}},
        hovertemplate:'<b>%{text}</b><br>Rate: %{x}%<br>Lead: %{y:.2f}w<extra></extra>',
      }], lay({
        height:240,
        xaxis:{...BASE_LAYOUT.xaxis,title:{text:'Detection Rate (%)'},range:[0,110]},
        yaxis:{...BASE_LAYOUT.yaxis,title:{text:'Lead Time (weeks)'}},
      }), PC);
    }

  } catch(e) { console.error('loadOverview:',e); }
}

function _count(id, raw, dec=0, suf='') {
  const el=document.getElementById(id); if(!el) return;
  const target=parseFloat(raw)||0;
  let step=0, total=45;
  const go=()=>{ step++; el.textContent=(target*(step/total)).toFixed(dec)+suf;
    if(step<total) requestAnimationFrame(go); else el.textContent=target.toFixed(dec)+suf; };
  requestAnimationFrame(go);
}

/* ══════════════════════════════════════════════════════════════════
   7. ALERTS
   ══════════════════════════════════════════════════════════════════ */
let AL_PG = 1;
let AL_READY = false;

async function loadAlerts() {
  if (!AL_READY) {
    AL_READY = true;
    try {
      // Filters
      const f = await _get('/api/alerts/filters');
      // date_min / date_max (NOT date_range)
      const fromEl=document.getElementById('al-from');
      const toEl  =document.getElementById('al-to');
      if(fromEl) fromEl.value = f.date_min||'';
      if(toEl)   toEl.value   = f.date_max||'';

      // Populate city selects
      ['al-city','tl-city'].forEach(id=>{
        const el=document.getElementById(id); if(!el) return;
        f.cities.forEach(v=>el.add(new Option(v,v)));
      });
      // Populate disease selects
      ['al-dis','tl-dis'].forEach(id=>{
        const el=document.getElementById(id); if(!el) return;
        f.diseases.forEach(v=>el.add(new Option(v,v)));
      });
      // Heatmap disease select
      const hd=document.getElementById('hm-dis');
      if(hd) f.diseases.forEach(v=>hd.add(new Option(v,v)));

      // Default timeline to first city/disease
      const tc=document.getElementById('tl-city');
      const td=document.getElementById('tl-dis');
      if(tc && f.cities.length) tc.value = f.cities.includes('Abuja')?'Abuja':f.cities[0];
      if(td && f.diseases.length) td.value = f.diseases.includes('COVID-19')?'COVID-19':f.diseases[0];

      // Update topbar stats
      const el=document.getElementById('al-top-stats');
      if(el) el.innerHTML=`
        <div class="tstat"><strong>${(37477).toLocaleString()}</strong>&nbsp;Alerts</div>
        <div class="tsep"></div>
        <div class="tstat"><strong>${f.cities.length}</strong>&nbsp;Cities</div>
        <div class="tsep"></div>
        <div class="tstat"><strong>${f.diseases.length}</strong>&nbsp;Diseases</div>`;
    } catch(e){ console.error('alerts/filters:',e); }

    // Summary KPIs — API returns {total, Normal, Watch, Warning, Emergency}
    try {
      const s = await _get('/api/alerts/summary');
      setText('mk-em', (s.Emergency||0).toLocaleString());
      setText('mk-wa', (s.Warning||0).toLocaleString());
      setText('mk-wt', (s.Watch||0).toLocaleString());
      setText('mk-nm', (s.Normal||0).toLocaleString());
    } catch(e) { console.error('alerts/summary:',e); }
  }

  // Load all three sections in parallel
  fetchAlTable(1);
  loadTimeline();
  loadHeatmap();
}

async function refreshAlerts() { AL_PG=1; fetchAlTable(1); }

async function fetchAlTable(pg) {
  const city   = document.getElementById('al-city').value;
  const dis    = document.getElementById('al-dis').value;
  const from   = document.getElementById('al-from').value;
  const to     = document.getElementById('al-to').value;
  const levels = [...document.querySelectorAll('.al-lv:checked')].map(c=>c.value);
  const p = _qs([
    city?`city=${enc(city)}`:'', dis?`disease=${enc(dis)}`:'',
    from?`from=${from}`:'', to?`to=${to}`:'',
    ...levels.map(l=>`level=${l}`), `page=${pg}`,
  ]);

  const tb = document.getElementById('al-tbody');
  if(tb) tb.innerHTML='<tr><td colspan="9"><div class="spin-box"><div class="spa-spin"></div></div></td></tr>';
  try {
    // API returns { data:[...], total, page, pages }
    const d = await _get(`/api/alerts/table?${p}`);
    const rows = d.data||[];
    setText('al-showing', rows.length);
    setText('al-total', (d.total||0).toLocaleString());
    if(tb) tb.innerHTML = rows.length
      ? rows.map(r=>`<tr>
          <td>${r.CITY||'—'}</td>
          <td>${r.DISEASE||'—'}</td>
          <td>${r.WEEK_START||'—'}</td>
          <td style="color:${r.IF_FLAG?'#6C63FF':'#3D4B5C'}">${r.IF_FLAG||0}</td>
          <td style="color:${r.DBSCAN_FLAG?'#00D4FF':'#3D4B5C'}">${r.DBSCAN_FLAG||0}</td>
          <td style="color:${r.lstm_pred?'#F59E0B':'#3D4B5C'}">${r.lstm_pred||0}</td>
          <td><span style="font-family:'JetBrains Mono',monospace">${(r.lstm_prob||0).toFixed(3)}</span></td>
          <td><b style="font-family:'JetBrains Mono',monospace">${(r.fusion_score||0).toFixed(2)}</b></td>
          <td><span class="badge ${_bc(r.alert_level)}">${r.alert_level||'—'}</span></td>
        </tr>`).join('')
      : '<tr><td colspan="9" style="text-align:center;padding:28px;color:var(--t3)">No records found</td></tr>';
    pgRender('al-pg', pg, d.pages||1, fetchAlTable);
  } catch(e) {
    if(tb) tb.innerHTML='<tr><td colspan="9" style="text-align:center;color:var(--red);padding:20px">Error loading data</td></tr>';
  }
}

async function loadTimeline() {
  const city = document.getElementById('tl-city')?.value||'';
  const dis  = document.getElementById('tl-dis')?.value||'';
  if (!city||!dis) { noD('ch-timeline','Select a city and disease'); noD('ch-signals','Select a city and disease'); return; }

  ['ch-timeline','ch-signals'].forEach(spin);
  try {
    const d = await _get(`/api/alerts/timeline?city=${enc(city)}&disease=${enc(dis)}`);
    if (!d.weeks||!d.weeks.length){ noD('ch-timeline','No data for this selection'); return; }

    const fc = d.fusion_score.map(v=>v>=4?'#EF4444':v===3?'#F59E0B':v>=1?'#3B82F6':'#6B7280');
    const el = prep('ch-timeline');
    if(el) Plotly.newPlot(el,[
      {x:d.weeks,y:d.fusion_score,type:'scatter',mode:'lines+markers',name:'Fusion Score',
       line:{color:'#6C63FF',width:2.5},marker:{size:4,color:fc},
       fill:'tozeroy',fillcolor:'rgba(108,99,255,.07)'},
      {x:d.weeks,y:d.IF_FLAG.map(v=>v*.9),type:'bar',name:'IF',marker:{color:'rgba(108,99,255,.7)'},yaxis:'y2'},
      {x:d.weeks,y:d.DBSCAN_FLAG.map(v=>v*.9),type:'bar',name:'DBSCAN',marker:{color:'rgba(0,212,255,.7)'},yaxis:'y2'},
      {x:d.weeks,y:d.lstm_prob,type:'scatter',mode:'lines',name:'LSTM Prob',
       line:{color:'#F59E0B',width:1.5,dash:'dot'},yaxis:'y2'},
    ], lay({
      height:280,barmode:'group',showlegend:true,
      legend:{orientation:'h',y:-.18,bgcolor:'rgba(0,0,0,0)',font:{color:'#8B95A7',size:10}},
      xaxis:{...BASE_LAYOUT.xaxis,type:'date',tickformat:'%b %Y',tickangle:-30},
      yaxis:{...BASE_LAYOUT.yaxis,title:{text:'Fusion Score'},range:[0,6]},
      yaxis2:{overlaying:'y',side:'right',range:[0,2],showgrid:false,showticklabels:false},
      margin:{t:10,r:44,b:70,l:52},
    }), PC);

    // Signals chart
    const hasSignals = d.IF_FLAG.some(v=>v)||d.DBSCAN_FLAG.some(v=>v)||d.lstm_pred.some(v=>v);
    if (!hasSignals) { noD('ch-signals','No anomaly flags','All models normal for this selection'); return; }
    const el2 = prep('ch-signals');
    if(el2) Plotly.newPlot(el2,[
      {x:d.weeks,y:d.IF_FLAG,type:'bar',name:'Isolation Forest',marker:{color:'rgba(108,99,255,.8)'}},
      {x:d.weeks,y:d.DBSCAN_FLAG,type:'bar',name:'DBSCAN',marker:{color:'rgba(0,212,255,.8)'}},
      {x:d.weeks,y:d.lstm_pred,type:'bar',name:'LSTM',marker:{color:'rgba(245,158,11,.8)'}},
    ], lay({
      height:240,barmode:'group',showlegend:true,
      legend:{orientation:'h',y:-.22,bgcolor:'rgba(0,0,0,0)',font:{color:'#8B95A7',size:10}},
      xaxis:{...BASE_LAYOUT.xaxis,type:'date',tickformat:'%b %Y',tickangle:-30},
      yaxis:{...BASE_LAYOUT.yaxis,tickvals:[0,1],ticktext:['No','Yes'],range:[-.1,1.6]},
      margin:{t:10,r:22,b:72,l:52},
    }), PC);
  } catch(e){ noD('ch-timeline','Failed to load',e.message); }
}

async function loadHeatmap() {
  const dis = document.getElementById('hm-dis')?.value||'all';
  spin('ch-heatmap');
  try {
    const d = await _get(`/api/alerts/heatmap?disease=${enc(dis)}`);
    if (!d.cities||!d.cities.length){ noD('ch-heatmap','No heatmap data'); return; }
    const el = prep('ch-heatmap');
    if(el) Plotly.newPlot(el,[{
      type:'heatmap',x:d.months,y:d.cities,z:d.z,
      colorscale:[[0,'#111827'],[.33,'#1e3a5f'],[.66,'#92400e'],[1,'#7f1d1d']],
      zmin:0,zmax:3,showscale:false,
      hovertemplate:'<b>%{y}</b><br>%{x}<br>Alert Lvl: %{z}<extra></extra>',
    }], lay({
      height:240,
      margin:{t:10,r:10,b:52,l:120},
      xaxis:{...BASE_LAYOUT.xaxis,tickangle:-45,tickfont:{size:9}},
      yaxis:{...BASE_LAYOUT.yaxis,tickfont:{size:9},automargin:true},
    }), PC);
  } catch(e){ noD('ch-heatmap','Failed to load',e.message); }
}

/* ══════════════════════════════════════════════════════════════════
   8. SCENARIOS
   ══════════════════════════════════════════════════════════════════ */
let DD_EL = null;

async function loadScenarios() {
  const grid = document.getElementById('sc-grid');
  if (!grid) return;
  try {
    const d = await _get('/api/scenarios');
    const sc = d.scenarios||[];
    grid.innerHTML = sc.map((s,i)=>`
      <div class="sc-card${s.detected?' det':''}" style="animation-delay:${i*.04}s"
           onclick="openDD('${s.city}','${s.disease}',this)">
        <div style="font-size:20px;margin-bottom:8px">${s.emoji||'🦠'}</div>
        <div class="sc-card-title">${s.city}</div>
        <div class="sc-card-sub">${s.disease}</div>
        <div class="sc-card-stats">
          <div class="sc-stat"><span>Lead Time</span><span>${s.lead_time ? s.lead_time.toFixed(1)+' wks' : '—'}</span></div>
          <div class="sc-stat"><span>Alert Level</span><span>${s.max_alert_level||'—'}</span></div>
          <div class="sc-stat"><span>Detect Rate</span><span>${s.detection_rate!=null?s.detection_rate.toFixed(0)+'%':'—'}</span></div>
          <div class="sc-stat"><span>Records</span><span>${(s.n_records||0).toLocaleString()}</span></div>
        </div>
      </div>`).join('');
  } catch(e) {
    if(grid) grid.innerHTML='<div class="no-d" style="grid-column:1/-1"><div class="no-d-title">Failed to load scenarios</div></div>';
  }
}

async function openDD(city, disease, cardEl) {
  if(DD_EL) DD_EL.style.borderColor='';
  DD_EL = cardEl; cardEl.style.borderColor='rgba(108,99,255,.6)';

  const panel = document.getElementById('dd-panel');
  const title = document.getElementById('dd-title');
  const chart = document.getElementById('dd-chart');
  if(!panel||!title||!chart) return;
  title.textContent = `${city}  /  ${disease}`;
  chart.innerHTML = '<div class="spin-box" style="min-height:260px"><div class="spa-spin"></div></div>';
  panel.classList.add('show');
  panel.scrollIntoView({behavior:'smooth',block:'nearest'});

  try {
    const d = await _get(`/api/scenarios/timeline?city=${enc(city)}&disease=${enc(dis=disease)}`);
    if (!d.weeks||!d.weeks.length) { chart.innerHTML='<div class="no-d"><div class="no-d-title">No timeline data</div></div>'; return; }

    const shapes=[], annots=[];
    const x0=d.weeks[0], x1=d.weeks[d.weeks.length-1];

    // Early warning shade
    if(d.first_alert && d.outbreak_start) {
      shapes.push({type:'rect',x0:d.first_alert,x1:d.outbreak_start,y0:0,y1:5.8,
        fillcolor:'rgba(16,185,129,.07)',line:{width:0},layer:'below'});
      annots.push({x:d.first_alert,y:5.7,text:'⚡ First Alert',showarrow:false,
        font:{color:'#10B981',size:10},xanchor:'left',xshift:5});
    }
    // Outbreak region
    if(d.outbreak_start && d.outbreak_end) {
      shapes.push(
        {type:'rect',x0:d.outbreak_start,x1:d.outbreak_end,y0:0,y1:5.8,fillcolor:'rgba(239,68,68,.06)',line:{width:0},layer:'below'},
        {type:'line',x0:d.outbreak_start,x1:d.outbreak_start,y0:0,y1:5.8,line:{color:'#EF4444',dash:'dash',width:1.5}}
      );
      annots.push({x:d.outbreak_start,y:5.7,text:'🚨 Outbreak',showarrow:false,
        font:{color:'#EF4444',size:10},xanchor:'left',xshift:5});
    }
    // Threshold lines
    shapes.push(
      {type:'line',x0,x1,y0:3,y1:3,line:{color:'rgba(245,158,11,.35)',dash:'dot',width:1.5}},
      {type:'line',x0,x1,y0:1,y1:1,line:{color:'rgba(59,130,246,.35)',dash:'dot',width:1.5}}
    );

    chart.innerHTML='';
    const fc=d.fusion_score.map(v=>v>=4?'#EF4444':v===3?'#F59E0B':v>=1?'#3B82F6':'#6B7280');
    Plotly.newPlot(chart,[
      {x:d.weeks,y:d.fusion_score,type:'scatter',mode:'lines+markers',name:'Fusion Score',
       line:{color:'#6C63FF',width:2.5},marker:{size:5,color:fc},
       fill:'tozeroy',fillcolor:'rgba(108,99,255,.07)'},
      {x:d.weeks,y:d.IF_FLAG.map(v=>v*.9),type:'bar',name:'IF',marker:{color:'rgba(108,99,255,.7)'},yaxis:'y2'},
      {x:d.weeks,y:d.DBSCAN_FLAG.map(v=>v*.9),type:'bar',name:'DBSCAN',marker:{color:'rgba(0,212,255,.7)'},yaxis:'y2'},
      {x:d.weeks,y:d.lstm_prob,type:'scatter',mode:'lines',name:'LSTM Prob',
       line:{color:'#F59E0B',width:1.5,dash:'dot'},yaxis:'y2'},
    ], lay({
      height:300,barmode:'group',shapes,annotations:annots,showlegend:true,
      legend:{orientation:'h',y:-.2,bgcolor:'rgba(0,0,0,0)',font:{color:'#8B95A7',size:10}},
      xaxis:{...BASE_LAYOUT.xaxis,type:'date',tickformat:'%b %Y',tickangle:-30},
      yaxis:{...BASE_LAYOUT.yaxis,title:{text:'Fusion Score'},range:[0,6.5]},
      yaxis2:{overlaying:'y',side:'right',range:[0,2],showgrid:false,showticklabels:false},
      margin:{t:10,r:44,b:70,l:52},
    }), PC);
  } catch(e) {
    chart.innerHTML=`<div class="no-d"><div class="no-d-icon">⚠️</div><div class="no-d-title">Failed to load</div><div class="no-d-sub">${e.message}</div></div>`;
  }
}
var dis=''; // hoisted for openDD closure
function closeDD() {
  document.getElementById('dd-panel')?.classList.remove('show');
  if(DD_EL){ DD_EL.style.borderColor=''; DD_EL=null; }
}

/* ══════════════════════════════════════════════════════════════════
   9. MODELS
   ══════════════════════════════════════════════════════════════════ */
async function loadModels() {
  try {
    const [sum, fil] = await Promise.all([_get('/api/models/summary'), _get('/api/models/filters')]);

    // Actual structure: sum.models = { LSTM:{name,weight,metrics:{F1,PR_AUC},...}, IF:{...}, DBSCAN:{...} }
    const M = sum.models||{};
    const IF_m    = M.IF    || {};
    const DB_m    = M.DBSCAN|| {};
    const LS_m    = M.LSTM  || {};

    const cards = [
      { key:'IF',    name:'Isolation Forest', sub:'Unsupervised anomaly detection', icon:'🔮', color:'#6C63FF',
        metrics:[ ['F1 Score',  (IF_m.metrics?.F1||0).toFixed(3)],
                  ['Lead Time', (IF_m.metrics?.Avg_Lead_Days||35)+' days'],
                  ['Coverage',  IF_m.coverage||'All 12'] ] },
      { key:'DBSCAN',name:'DBSCAN Clustering',sub:'Density-based spatial clustering',icon:'🌀', color:'#00D4FF',
        metrics:[ ['ROC AUC',   (DB_m.metrics?.ROC_AUC||0).toFixed(3)],
                  ['Precision', ((DB_m.metrics?.Precision||0)*100).toFixed(1)+'%'],
                  ['FPR',       ((DB_m.metrics?.FPR||0)*100).toFixed(1)+'%'] ] },
      { key:'LSTM',  name:'LSTM Neural Net',  sub:'Deep learning sequence model',   icon:'🧠', color:'#F59E0B',
        metrics:[ ['F1 Score',  (LS_m.metrics?.F1||0.644).toFixed(3)],
                  ['PR AUC',    (LS_m.metrics?.PR_AUC||0.567).toFixed(3)],
                  ['Coverage',  LS_m.coverage||'10 / 12'] ] },
    ];

    const grid = document.getElementById('mc-grid');
    if(grid) grid.innerHTML = cards.map((c,i)=>`
      <div class="mc-card gin-${i}" style="border-top:2px solid ${c.color}22">
        <div style="font-size:28px;margin-bottom:6px">${c.icon}</div>
        <div class="mc-name" style="color:${c.color}">${c.name}</div>
        <div class="mc-sub">${c.sub}</div>
        <div class="mmet">
          ${c.metrics.map(([k,v])=>`
            <div class="mmet-r">
              <span class="mmet-k">${k}</span>
              <span class="mmet-v">${v}</span>
            </div>`).join('')}
        </div>
        <div style="margin-top:10px;padding-top:10px;border-top:1px solid rgba(255,255,255,.05);font-size:10.5px;color:var(--t3)">${c.key==='IF'?'Best early warning lead time':c.key==='DBSCAN'?'Best discriminative power (AUC)':'Best outbreak prediction'}</div>
      </div>`).join('');

    // Radar chart
    const cats=['F1 Score','Precision','Recall','AUC','Coverage'];
    const el1 = prep('ch-radar');
    if(el1) Plotly.newPlot(el1,[
      {type:'scatterpolar',r:[IF_m.metrics?.F1*100||12,12,10,70,100],theta:cats,fill:'toself',
       name:'IF',line:{color:'#6C63FF'},fillcolor:'rgba(108,99,255,.12)'},
      {type:'scatterpolar',r:[DB_m.metrics?.F1*100||20,DB_m.metrics?.Precision*100||49,DB_m.metrics?.Recall*100||46,DB_m.metrics?.ROC_AUC*100||92,100],theta:cats,fill:'toself',
       name:'DBSCAN',line:{color:'#00D4FF'},fillcolor:'rgba(0,212,255,.12)'},
      {type:'scatterpolar',r:[LS_m.metrics?.F1*100||64,60,62,LS_m.metrics?.PR_AUC*100||57,83],theta:cats,fill:'toself',
       name:'LSTM',line:{color:'#F59E0B'},fillcolor:'rgba(245,158,11,.12)'},
    ], lay({
      height:280,showlegend:true,
      polar:{bgcolor:'rgba(0,0,0,0)',
        radialaxis:{visible:true,range:[0,100],gridcolor:'rgba(255,255,255,.06)',tickfont:{size:9}},
        angularaxis:{gridcolor:'rgba(255,255,255,.06)',tickfont:{size:10,color:'#8B95A7'}}},
      legend:{orientation:'h',y:-.1,bgcolor:'rgba(0,0,0,0)',font:{color:'#8B95A7',size:10}},
      margin:{t:10,r:30,b:44,l:30},
    }), PC);

    // Fusion composition from API: sum.scenario_fusion = [{label,IF,DBSCAN,LSTM,total}]
    const sf = sum.scenario_fusion||[];
    const el2 = prep('ch-fusion');
    if(el2 && sf.length) Plotly.newPlot(el2,[
      {type:'bar',name:'IF',    x:sf.map(r=>r.label),y:sf.map(r=>r.IF),    marker:{color:'rgba(108,99,255,.8)'}},
      {type:'bar',name:'DBSCAN',x:sf.map(r=>r.label),y:sf.map(r=>r.DBSCAN),marker:{color:'rgba(0,212,255,.8)'}},
      {type:'bar',name:'LSTM',  x:sf.map(r=>r.label),y:sf.map(r=>r.LSTM),  marker:{color:'rgba(245,158,11,.8)'}},
    ], lay({
      height:280,barmode:'stack',showlegend:true,
      legend:{orientation:'h',y:-.18,bgcolor:'rgba(0,0,0,0)',font:{color:'#8B95A7',size:10}},
      xaxis:{...BASE_LAYOUT.xaxis,tickangle:-35,tickfont:{size:9}},
      yaxis:{...BASE_LAYOUT.yaxis,title:{text:'Fusion Score Contribution'}},
      margin:{t:10,r:22,b:70,l:55},
    }), PC);

    // Populate LSTM filters
    const lc=document.getElementById('lstm-city');
    const ld=document.getElementById('lstm-dis');
    if(lc) { lc.innerHTML=''; fil.cities.forEach(v=>lc.add(new Option(v,v))); }
    if(ld) { ld.innerHTML=''; fil.diseases.forEach(v=>ld.add(new Option(v,v))); }
    // Defaults
    if(lc && fil.cities.includes('Kinshasa')) lc.value='Kinshasa';
    if(ld && fil.diseases.includes('Ebola virus disease')) ld.value='Ebola virus disease';
    loadLSTM();

  } catch(e) { console.error('loadModels:',e); }
}

async function loadLSTM() {
  const city = document.getElementById('lstm-city')?.value||'';
  const dis  = document.getElementById('lstm-dis')?.value||'';
  if(!city||!dis){ noD('ch-lstm','Select city and disease'); return; }
  spin('ch-lstm');
  try {
    // API: { dates, lstm_prob, lstm_pred, y_true, outbreak_start, outbreak_end }
    const d = await _get(`/api/models/lstm-timeline?city=${enc(city)}&disease=${enc(dis)}`);
    if(!d.dates||!d.dates.length){ noD('ch-lstm','No LSTM data for this selection'); return; }

    const shapes=[],annots=[];
    const x0=d.dates[0], xN=d.dates[d.dates.length-1];
    if(d.outbreak_start){
      shapes.push({type:'line',x0:d.outbreak_start,x1:d.outbreak_start,y0:0,y1:1,line:{color:'#EF4444',dash:'dash',width:2}});
      annots.push({x:d.outbreak_start,y:1.06,text:'🚨 Outbreak',showarrow:false,font:{color:'#EF4444',size:10},xanchor:'left',xshift:5});
    }
    if(d.outbreak_end){
      shapes.push({type:'line',x0:d.outbreak_end,x1:d.outbreak_end,y0:0,y1:1,line:{color:'rgba(239,68,68,.4)',dash:'dot',width:1.5}});
    }
    shapes.push({type:'line',x0,x1:xN,y0:.5,y1:.5,line:{color:'rgba(255,255,255,.18)',dash:'dot',width:1.2}});
    annots.push({x:d.dates[Math.floor(d.dates.length/6)],y:.5,text:'Threshold 0.5',
      showarrow:false,font:{color:'rgba(255,255,255,.28)',size:9},yanchor:'bottom',yshift:4});

    const el = prep('ch-lstm');
    if(!el) return;
    Plotly.newPlot(el,[
      {x:d.dates,y:d.lstm_prob,type:'scatter',mode:'lines',name:'LSTM Probability',
       line:{color:'#F59E0B',width:2.5},fill:'tozeroy',fillcolor:'rgba(245,158,11,.06)'},
      {x:d.dates.filter((_,i)=>d.y_true[i]===1),y:d.lstm_prob.filter((_,i)=>d.y_true[i]===1),
       type:'scatter',mode:'markers',name:'True Outbreak',marker:{color:'#EF4444',size:7}},
      {x:d.dates.filter((_,i)=>d.lstm_pred[i]===1&&d.y_true[i]===0),
       y:d.lstm_prob.filter((_,i)=>d.lstm_pred[i]===1&&d.y_true[i]===0),
       type:'scatter',mode:'markers',name:'False Positive',marker:{color:'#F59E0B',size:6,symbol:'x'}},
    ], lay({
      height:300,shapes,annotations:annots,showlegend:true,
      legend:{orientation:'h',y:-.2,bgcolor:'rgba(0,0,0,0)',font:{color:'#8B95A7',size:10}},
      xaxis:{...BASE_LAYOUT.xaxis,type:'date',tickformat:'%b %Y',tickangle:-30},
      yaxis:{...BASE_LAYOUT.yaxis,title:{text:'LSTM Probability'},range:[-.05,1.15]},
      margin:{t:10,r:22,b:70,l:55},
    }), PC);
  } catch(e){ noD('ch-lstm','Failed to load LSTM timeline',e.message); }
}

/* ══════════════════════════════════════════════════════════════════
   10. EXPLORER
   ══════════════════════════════════════════════════════════════════ */
let EXP_READY=false;
async function loadExplorer() {
  if(!EXP_READY){
    EXP_READY=true;
    try {
      // API returns: { alerts_cities, alerts_diseases, lstm_cities, lstm_countries, patient_cities, patient_diseases, patient_seasons }
      const f = await _get('/api/data/filters');
      // Alerts tab dropdowns
      _fill('xa-city', f.alerts_cities||[]);
      _fill('xa-dis',  f.alerts_diseases||[]);
      // LSTM tab dropdowns
      _fill('xl-city', f.lstm_cities||[]);
      _fill('xl-dis',  f.alerts_diseases||[]);   // LSTM has same diseases
      // Signals tab dropdowns
      _fill('xs-city', f.alerts_cities||[]);
      _fill('xs-dis',  f.alerts_diseases||[]);
    } catch(e){ console.error('explorer/filters:',e); }
  }
  loadExpAlerts(1);
}

function _fill(id, arr) {
  const el=document.getElementById(id); if(!el) return;
  arr.forEach(v=>el.add(new Option(v,v)));
}

async function loadExpAlerts(pg) {
  const p=_qs([
    document.getElementById('xa-city')?.value  ? `city=${enc(document.getElementById('xa-city').value)}`:'',
    document.getElementById('xa-dis')?.value   ? `disease=${enc(document.getElementById('xa-dis').value)}`:'',
    document.getElementById('xa-score')?.value ? `score_min=${document.getElementById('xa-score').value}`:'',
    `page=${pg}`,
  ]);
  const tb=document.getElementById('xa-tbody');
  if(tb) tb.innerHTML='<tr><td colspan="10"><div class="spin-box"><div class="spa-spin"></div></div></td></tr>';
  try {
    // API returns { data:[...], total, page, pages }
    const d=await _get(`/api/data/alerts?${p}`);
    const rows=d.data||[];
    setText('xa-show', rows.length); setText('xa-tot', (d.total||0).toLocaleString());
    if(tb) tb.innerHTML=rows.length
      ? rows.map(r=>`<tr>
          <td>${r.CITY||'—'}</td><td>${r.DISEASE||'—'}</td>
          <td>${r.WEEK_START||'—'}</td>
          <td style="color:${r.IF_FLAG?'#6C63FF':'#3D4B5C'}">${r.IF_FLAG||0}</td>
          <td style="color:${r.DBSCAN_FLAG?'#00D4FF':'#3D4B5C'}">${r.DBSCAN_FLAG||0}</td>
          <td style="color:${r.lstm_pred?'#F59E0B':'#3D4B5C'}">${r.lstm_pred||0}</td>
          <td><span style="font-family:'JetBrains Mono',monospace">${(r.lstm_prob||0).toFixed(3)}</span></td>
          <td><b style="font-family:'JetBrains Mono',monospace">${(r.fusion_score||0).toFixed(2)}</b></td>
          <td><span class="badge ${_bc(r.alert_level)}">${r.alert_level||'—'}</span></td>
          <td>${r.total_visits||'—'}</td>
        </tr>`).join('')
      : '<tr><td colspan="10" style="text-align:center;padding:28px;color:var(--t3)">No records</td></tr>';
    pgRender('xa-pg', pg, d.pages||1, loadExpAlerts);
  } catch(e){ if(tb) tb.innerHTML='<tr><td colspan="10" style="text-align:center;color:var(--red)">Error</td></tr>'; }
}

async function loadExpLSTM(pg) {
  const p=_qs([
    document.getElementById('xl-city')?.value ? `city=${enc(document.getElementById('xl-city').value)}`:'',
    document.getElementById('xl-dis')?.value  ? `disease=${enc(document.getElementById('xl-dis').value)}`:'',
    `page=${pg}`,
  ]);
  const tb=document.getElementById('xl-tbody');
  if(tb) tb.innerHTML='<tr><td colspan="9"><div class="spin-box"><div class="spa-spin"></div></div></td></tr>';
  try {
    // API returns data with: COUNTRY, CITY, DISEASE, target_date, lstm_prob, lstm_pred, y_true
    const d=await _get(`/api/data/lstm?${p}`);
    const rows=d.data||[];
    if(tb) tb.innerHTML=rows.length
      ? rows.map(r=>`<tr>
          <td>${r.CITY||'—'}</td><td>${r.DISEASE||'—'}</td>
          <td>${r.target_date||'—'}</td>
          <td><span style="font-family:'JetBrains Mono',monospace">${(r.lstm_prob||0).toFixed(4)}</span></td>
          <td style="color:${r.lstm_pred?'#F59E0B':'#3D4B5C'}">${r.lstm_pred||0}</td>
          <td style="color:${r.y_true?'#EF4444':'#3D4B5C'}">${r.y_true||0}</td>
          <td>${r.COUNTRY||'—'}</td>
        </tr>`).join('')
      : '<tr><td colspan="9" style="text-align:center;padding:28px;color:var(--t3)">No records</td></tr>';
    pgRender('xl-pg', pg, d.pages||1, loadExpLSTM);
  } catch(e){ if(tb) tb.innerHTML='<tr><td colspan="9" style="text-align:center;color:var(--red)">Error</td></tr>'; }
}

async function loadExpSignals(pg) {
  const p=_qs([
    document.getElementById('xs-city')?.value ? `city=${enc(document.getElementById('xs-city').value)}`:'',
    document.getElementById('xs-dis')?.value  ? `disease=${enc(document.getElementById('xs-dis').value)}`:'',
    `page=${pg}`,
  ]);
  const tb=document.getElementById('xs-tbody');
  if(tb) tb.innerHTML='<tr><td colspan="8"><div class="spin-box"><div class="spa-spin"></div></div></td></tr>';
  try {
    // API returns: CITY, DISEASE, WEEK_START, IF_FLAG, DBSCAN_FLAG, lstm_prob, lstm_pred, true_outbreak, total_visits
    const d=await _get(`/api/data/signals?${p}`);
    const rows=d.data||[];
    if(tb) tb.innerHTML=rows.length
      ? rows.map(r=>`<tr>
          <td>${r.CITY||'—'}</td><td>${r.DISEASE||'—'}</td>
          <td>${r.WEEK_START||'—'}</td>
          <td style="color:${r.IF_FLAG?'#6C63FF':'#3D4B5C'}">${r.IF_FLAG||0}</td>
          <td style="color:${r.DBSCAN_FLAG?'#00D4FF':'#3D4B5C'}">${r.DBSCAN_FLAG||0}</td>
          <td><span style="font-family:'JetBrains Mono',monospace">${(r.lstm_prob||0).toFixed(3)}</span></td>
          <td style="color:${r.lstm_pred?'#F59E0B':'#3D4B5C'}">${r.lstm_pred||0}</td>
          <td style="color:${r.true_outbreak?'#EF4444':'#3D4B5C'}">${r.true_outbreak||0}</td>
        </tr>`).join('')
      : '<tr><td colspan="8" style="text-align:center;padding:28px;color:var(--t3)">No records</td></tr>';
    pgRender('xs-pg', pg, d.pages||1, loadExpSignals);
  } catch(e){ if(tb) tb.innerHTML='<tr><td colspan="8" style="text-align:center;color:var(--red)">Error</td></tr>'; }
}

/* ══════════════════════════════════════════════════════════════════
   11. SHARED HELPERS
   ══════════════════════════════════════════════════════════════════ */
async function _get(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`HTTP ${r.status} — ${url}`);
  const json = await r.json();
  if (json && json.hasOwnProperty('success') && json.hasOwnProperty('data')) {
    return json.data;
  }
  return json;
}
function enc(v){ return encodeURIComponent(v||''); }
function _qs(parts){ return parts.filter(Boolean).join('&'); }
function setText(id,val){ const e=document.getElementById(id); if(e) e.textContent=val; }
function _bc(lvl){ return {Normal:'b-n',Watch:'b-w',Warning:'b-wa',Emergency:'b-e'}[lvl]||'b-n'; }

// Pagination — uses named fn ref instead of .toString()
function pgRender(containerId, page, pages, fn) {
  const el = document.getElementById(containerId);
  if (!el||pages<=1){ if(el) el.innerHTML=''; return; }
  const s=Math.max(1,page-2), e=Math.min(pages,page+2);
  let h=`<span style="font-size:11px;color:var(--t3);margin-right:8px">Page ${page}/${pages}</span>`;
  h+=`<button class="pb"${page<=1?' disabled':''} onclick="pgClick(this,'${containerId}',${page-1})">&lsaquo;</button>`;
  for(let i=s;i<=e;i++) h+=`<button class="pb${i===page?' on':''}" onclick="pgClick(this,'${containerId}',${i})">${i}</button>`;
  h+=`<button class="pb"${page>=pages?' disabled':''} onclick="pgClick(this,'${containerId}',${page+1})">&rsaquo;</button>`;
  el.innerHTML=h;
}

// Map container IDs to load functions
const PG_FNS = {
  'al-pg': fetchAlTable,
  'xa-pg': loadExpAlerts,
  'xl-pg': loadExpLSTM,
  'xs-pg': loadExpSignals,
};
function pgClick(btn, cId, pg) { const fn=PG_FNS[cId]; if(fn) fn(pg); }

// Explorer tab switch
function switchExpTab(name, el) {
  document.querySelectorAll('.tab-pnl').forEach(p=>p.classList.remove('on'));
  document.querySelectorAll('.tab-b').forEach(b=>b.classList.remove('on'));
  document.getElementById('xpnl-'+name)?.classList.add('on');
  el.classList.add('on');
  if(name==='lstm'    && EXP_READY) loadExpLSTM(1);
  if(name==='signals' && EXP_READY) loadExpSignals(1);
}
