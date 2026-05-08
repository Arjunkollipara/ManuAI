const API_BASE = window.location.origin;
const DEFAULT_TIMEOUT = 12000;
const AGENT_TIMEOUT = 60000;

const state = {
  currentAgent: 'maintenance',
  charts: {
    risk: null,
    sensor: null,
  },
};

const els = {};
const revealObserver = typeof IntersectionObserver !== 'undefined'
  ? new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          revealObserver.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12 })
  : null;

const sectionObserver = typeof IntersectionObserver !== 'undefined'
  ? new IntersectionObserver(entries => {
      const visible = entries.filter(entry => entry.isIntersecting);
      if (!visible.length) return;
      visible.sort((a, b) => b.intersectionRatio - a.intersectionRatio);
      const id = visible[0].target.id;
      if (!id) return;
      document.querySelectorAll('.topnav-link').forEach(link => {
        link.classList.toggle('is-active', link.getAttribute('href') === `#${id}`);
      });
    }, { threshold: [0.25, 0.5, 0.75], rootMargin: '-15% 0px -55% 0px' })
  : null;

function $(id) {
  return els[id] || (els[id] = document.getElementById(id));
}

function registerReveal(node) {
  if (!node) return;
  node.classList.add('reveal');
  if (revealObserver) {
    revealObserver.observe(node);
  } else {
    node.classList.add('is-visible');
  }
}

function apiRequest(endpoint, options = {}, timeout = DEFAULT_TIMEOUT) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);

  return fetch(`${API_BASE}${endpoint}`, {
    ...options,
    signal: controller.signal,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  })
    .then(response => {
      clearTimeout(timer);
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }
      return response.json();
    })
    .catch(error => {
      clearTimeout(timer);
      console.error(endpoint, error);
      return null;
    });
}

function apiGet(endpoint, timeout) {
  return apiRequest(endpoint, {}, timeout);
}

function apiPost(endpoint, body, timeout) {
  return apiRequest(
    endpoint,
    {
      method: 'POST',
      body: JSON.stringify(body),
    },
    timeout
  );
}

function formatTime(value) {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  return date.toLocaleString();
}

function formatAgo(value) {
  if (!value) return '-';
  const diff = Date.now() - new Date(value).getTime();
  if (Number.isNaN(diff)) return '-';
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function formatPercent(value) {
  return `${((Number(value) || 0) * 100).toFixed(1)}%`;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString();
}

function clampSeverity(value) {
  const severity = String(value || 'low').toLowerCase();
  if (['low', 'medium', 'high', 'critical'].includes(severity)) return severity;
  return 'low';
}

function destroyChart(chart) {
  if (chart && typeof chart.destroy === 'function') {
    chart.destroy();
  }
}

function setText(id, value) {
  const node = $(id);
  if (node) node.textContent = value;
}

function scrollToId(selector) {
  const node = document.querySelector(selector);
  if (node) {
    node.scrollIntoView({ behavior: 'smooth', block: 'start' });
    history.replaceState(null, '', selector);
    setActiveNav(selector);
  }
}

function setActiveNav(hash) {
  document.querySelectorAll('.topnav-link').forEach(link => {
    link.classList.toggle('is-active', link.getAttribute('href') === hash);
  });
}

function animateCount(node, target) {
  if (!node) return;
  const start = performance.now();
  const duration = 900;
  const begin = 0;
  const finish = Number(target) || 0;

  function tick(now) {
    const progress = Math.min((now - start) / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    const value = Math.round(begin + (finish - begin) * eased);
    node.textContent = value.toLocaleString();
    if (progress < 1) requestAnimationFrame(tick);
  }

  requestAnimationFrame(tick);
}

function setHealthIndicator(online, label = '') {
  const dot = $('apiHealthDot');
  const text = $('apiHealthText');
  if (dot) {
    dot.classList.toggle('online', !!online);
    dot.classList.toggle('offline', !online);
  }
  if (text) {
    text.textContent = label || (online ? 'API online' : 'API offline');
  }
}

function renderAlertFeed(alerts = []) {
  const container = $('alertFeed');
  if (!container) return;

  container.innerHTML = '';

  if (!alerts.length) {
    const empty = document.createElement('div');
    empty.className = 'search-card';
    empty.textContent = 'No active alerts right now.';
    registerReveal(empty);
    container.appendChild(empty);
    return;
  }

  alerts.forEach(alert => {
    const card = document.createElement('article');
    card.className = 'alert-card';
    registerReveal(card);

    const top = document.createElement('div');
    top.className = 'alert-card__top';

    const severity = document.createElement('span');
    severity.className = `severity ${clampSeverity(alert.severity)}`;
    severity.textContent = String(alert.severity || 'LOW');

    const time = document.createElement('span');
    time.className = 'alert-card__meta';
    time.textContent = formatAgo(alert.created_at);

    top.appendChild(severity);
    top.appendChild(time);

    const machine = document.createElement('div');
    machine.className = 'alert-card__machine';
    machine.textContent = alert.machine_id || 'UNKNOWN';

    const message = document.createElement('div');
    message.className = 'alert-card__message';
    message.textContent = alert.message || 'No message provided.';

    card.appendChild(top);
    card.appendChild(machine);
    card.appendChild(message);
    container.appendChild(card);
  });
}

function renderPredictionHistory(rows = []) {
  const container = $('predictionHistory');
  if (!container) return;

  container.innerHTML = '';

  if (!rows.length) {
    const empty = document.createElement('div');
    empty.className = 'history-item';
    empty.textContent = 'No prediction history yet.';
    registerReveal(empty);
    container.appendChild(empty);
    return;
  }

  rows.slice(0, 5).forEach(row => {
    const item = document.createElement('div');
    item.className = 'history-item';
    registerReveal(item);

    const left = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = `#${row.id || '-'}`;
    const meta = document.createElement('span');
    meta.textContent = `${String(row.risk_level || 'LOW')} | ${formatAgo(row.created_at)}`;
    left.appendChild(title);
    left.appendChild(meta);

    const right = document.createElement('div');
    right.textContent = formatPercent(row.failure_probability || 0);

    item.appendChild(left);
    item.appendChild(right);
    container.appendChild(item);
  });
}

function renderPredictionResult(result) {
  const container = $('predictionResult');
  if (!container) return;

  container.innerHTML = '';

  if (!result) {
    container.className = 'result-empty';
    container.textContent = 'Prediction failed or timed out.';
    registerReveal(container);
    return;
  }

  container.className = 'result-card';

  const top = document.createElement('div');
  top.className = 'result-top';
  registerReveal(container);

  const badge = document.createElement('span');
  badge.className = `severity ${clampSeverity(result.risk_level)}`;
  badge.textContent = String(result.risk_level || 'LOW');

  const score = document.createElement('strong');
  score.className = 'result-score';
  score.textContent = formatPercent(result.failure_probability || 0);

  top.appendChild(badge);
  top.appendChild(score);

  const summary = document.createElement('div');
  summary.className = 'prediction-summary';
  summary.textContent = result.explanation || 'No explanation returned.';

  const factors = document.createElement('div');
  factors.className = 'factor-list';

  const features = Array.isArray(result.top_contributing_features)
    ? result.top_contributing_features
    : [];

  if (!features.length) {
    const empty = document.createElement('div');
    empty.className = 'factor-item';
    empty.textContent = 'No factor data returned.';
    factors.appendChild(empty);
  } else {
    features.slice(0, 5).forEach(feature => {
      const item = document.createElement('div');
      item.className = 'factor-item';

      const left = document.createElement('span');
      left.textContent = feature.feature || feature.name || feature.label || 'Factor';

      const right = document.createElement('strong');
      right.textContent =
        feature.value !== undefined
          ? String(feature.value)
          : feature.importance !== undefined
          ? String(feature.importance)
          : feature.weight !== undefined
          ? String(feature.weight)
          : '-';

      item.appendChild(left);
      item.appendChild(right);
      factors.appendChild(item);
    });
  }

  container.appendChild(top);
  container.appendChild(summary);
  container.appendChild(factors);
}

function renderCharts(predictions = [], sensorData = []) {
  if (typeof Chart === 'undefined') return;

  const riskCanvas = $('riskChart');
  const sensorCanvas = $('sensorChart');

  if (riskCanvas && predictions.length) {
    const counts = {
      LOW: 0,
      MEDIUM: 0,
      HIGH: 0,
      CRITICAL: 0,
    };

    predictions.forEach(item => {
      const key = String(item.risk_level || 'LOW').toUpperCase();
      if (counts[key] !== undefined) counts[key] += 1;
    });

    destroyChart(state.charts.risk);
    state.charts.risk = new Chart(riskCanvas, {
      type: 'doughnut',
      data: {
        labels: Object.keys(counts),
        datasets: [
          {
            data: Object.values(counts),
            backgroundColor: ['#20d49a', '#00d4ff', '#f7b955', '#ff6b6b'],
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: '#edf2f7',
            },
          },
        },
      },
    });
  }

  if (sensorCanvas && sensorData.length) {
    destroyChart(state.charts.sensor);
    state.charts.sensor = new Chart(sensorCanvas, {
      type: 'line',
      data: {
        labels: sensorData.map((_, index) => `#${index + 1}`),
        datasets: [
          {
            label: 'Torque',
            data: sensorData.map(row => row.torque_nm || 0),
            borderColor: '#f7b955',
            tension: 0.35,
          },
          {
            label: 'Speed',
            data: sensorData.map(row => row.rotational_speed_rpm || 0),
            borderColor: '#00d4ff',
            tension: 0.35,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            labels: {
              color: '#edf2f7',
            },
          },
        },
        scales: {
          x: {
            ticks: { color: '#8aa0bc' },
            grid: { color: 'rgba(148, 163, 184, 0.08)' },
          },
          y: {
            ticks: { color: '#8aa0bc' },
            grid: { color: 'rgba(148, 163, 184, 0.08)' },
          },
        },
      },
    });
  }
}

async function loadDashboardData() {
  const [stats, alerts, predictions, sensorData] = await Promise.all([
    apiGet('/ingest/stats'),
    apiGet('/predict/alerts?limit=8'),
    apiGet('/predict/history?limit=50'),
    apiGet('/ingest/sensor-data?limit=20'),
  ]);

  const readings = Number(stats?.total_readings || 0);
  const alertCount = Number(stats?.total_alerts || 0);
  const failureRate = Number(stats?.failure_rate_percent || 0);

  animateCount($('heroReadings'), readings);
  animateCount($('heroAlerts'), alertCount);
  setText('heroRisk', `${failureRate.toFixed(1)}%`);

  animateCount($('statReadings'), readings);
  animateCount($('statAlerts'), alertCount);
  setText('statFailureRate', `${failureRate.toFixed(1)}%`);
  setText('statModel', 'Online');
  setText('statReadingsNote', stats?.last_ingested ? `Last ingest ${formatAgo(stats.last_ingested)}` : 'No ingested data yet');
  setText('statAlertsNote', `${Number(stats?.high_risk_count || 0)} high risk, ${Number(stats?.critical_risk_count || 0)} critical`);
  setText('statFailureNote', stats?.last_ingested ? `Last update ${formatTime(stats.last_ingested)}` : 'Waiting for data');
  setText('statModelNote', 'Predictor ready');

  renderAlertFeed(Array.isArray(alerts) ? alerts : []);
  renderPredictionHistory(Array.isArray(predictions) ? predictions : []);
  renderCharts(Array.isArray(predictions) ? predictions : [], Array.isArray(sensorData) ? sensorData : []);

  if (stats?.last_ingested) {
    setText('snapshotBackend', 'Healthy');
    setText('snapshotBackendCard', 'Healthy');
  }

  return { stats, alerts, predictions, sensorData };
}

async function loadAgentStatus() {
  const data = await apiGet('/agent/status');
  const ready = !!data?.credentials_configured;

  setText('agentSystemStatus', ready ? 'Credentials configured' : 'Credentials required');
  setText('agentStatus', data?.status || 'UNKNOWN');
  setText('snapshotAgent', ready ? 'Ready' : 'Needs setup');
  setText('snapshotAgentCard', ready ? 'Ready' : 'Needs setup');

  return data;
}

async function loadSystemStatus() {
  const [health, config, rag, agent] = await Promise.all([
    apiGet('/health'),
    apiGet('/system/config'),
    apiGet('/search/documents/health'),
    apiGet('/agent/status'),
  ]);

  const backendHealthy = health?.status === 'healthy';
  setHealthIndicator(backendHealthy, backendHealthy ? 'API online' : 'API offline');

  setText('snapshotBackend', backendHealthy ? 'Healthy' : 'Offline');
  setText('snapshotBackendCard', backendHealthy ? 'Healthy' : 'Offline');
  setText('snapshotModel', health?.model_loaded ? 'Online' : 'Unavailable');
  setText('snapshotModelCard', health?.model_loaded ? 'Online' : 'Unavailable');
  setText('snapshotRag', rag?.status || 'Unknown');
  setText('snapshotRagCard', rag?.status || 'Unknown');
  setText('snapshotAgent', agent?.status || 'Unknown');
  setText('snapshotAgentCard', agent?.status || 'Unknown');

  setText('svcBackend', health?.status || '-');
  setText('svcDatabase', health?.database || '-');
  setText('svcRag', rag?.status || '-');
  setText('svcAzureOpenAI', config?.azure_openai_configured ? 'Configured' : 'Missing');
  setText('svcAzureSearch', config?.azure_search_configured ? 'Configured' : 'Missing');

  const table = $('configTable');
  if (table) {
    table.innerHTML = '';
    const entries = [
      ['Environment', config?.environment || '-'],
      ['Azure OpenAI', config?.azure_openai_configured ? 'Configured' : 'Missing'],
      ['Azure Search', config?.azure_search_configured ? 'Configured' : 'Missing'],
      ['Health status', health?.status || '-'],
      ['Model loaded', health?.model_loaded ? 'Yes' : 'No'],
      ['Vector store', rag?.vector_store || '-'],
      ['Documents indexed', rag?.documents_indexed ?? '-'],
      ['Agents ready', agent?.credentials_configured ? 'Yes' : 'No'],
    ];

    entries.forEach(([label, value]) => {
      const row = document.createElement('tr');
      const left = document.createElement('td');
      left.textContent = label;
      const right = document.createElement('td');
      right.textContent = String(value);
      row.appendChild(left);
      row.appendChild(right);
      table.appendChild(row);
    });
  }
}

function renderChatMessage(role, content, agent = '', meta = '') {
  const container = $('chatMessages');
  if (!container) return null;

  const message = document.createElement('div');
  message.className = `chat-message ${role}`;
  registerReveal(message);

  const bubble = document.createElement('div');
  bubble.className = 'chat-bubble';

  if (agent) {
    const agentLabel = document.createElement('div');
    agentLabel.className = 'chat-agent';
    agentLabel.textContent = agent;
    bubble.appendChild(agentLabel);
  }

  const body = document.createElement('div');
  body.className = 'chat-content';
  body.textContent = content;
  bubble.appendChild(body);

  if (meta) {
    const time = document.createElement('div');
    time.className = 'chat-time';
    time.textContent = meta;
    bubble.appendChild(time);
  }

  message.appendChild(bubble);
  container.appendChild(message);
  container.scrollTop = container.scrollHeight;
  return message;
}

function showTyping() {
  const container = $('chatMessages');
  if (!container) return null;

  const wrapper = document.createElement('div');
  wrapper.id = 'typingIndicator';
  wrapper.className = 'chat-message agent';

  const bubble = document.createElement('div');
  bubble.className = 'typing';
  bubble.innerHTML = '<span></span><span></span><span></span>';

  wrapper.appendChild(bubble);
  container.appendChild(wrapper);
  container.scrollTop = container.scrollHeight;
  return wrapper;
}

function hideTyping() {
  const node = $('typingIndicator');
  if (node) node.remove();
}

async function sendAgentMessage(text) {
  const input = $('agentInput');
  const message = (text || input?.value || '').trim();
  if (!message) return;
  if (input) input.value = '';

  renderChatMessage('user', message, '', formatTime(new Date().toISOString()));
  showTyping();

  const started = performance.now();
  const response = await apiPost(
    '/agent/query',
    {
      question: message,
      context: {
        agent_preference: state.currentAgent,
      },
    },
    AGENT_TIMEOUT
  );
  const elapsed = Math.round(performance.now() - started);

  hideTyping();

  if (!response) {
    renderChatMessage('agent', 'The agent did not respond. Check backend health or credentials.', 'System', formatTime(new Date().toISOString()));
    return;
  }

  setText('agentUsed', response.agent_used || 'unknown');
  setText('agentLatency', `${elapsed} ms`);
  renderChatMessage(
    'agent',
    response.answer || 'No answer returned.',
    response.agent_used || 'Agent',
    formatTime(response.timestamp || new Date().toISOString())
  );
}

async function executeSearch(query) {
  const search = String(query || $('searchInput')?.value || '').trim();
  const container = $('searchResults');
  if (!search || !container) return;

  container.innerHTML = '';
  const loading = document.createElement('div');
  loading.className = 'search-card';
  loading.textContent = 'Searching...';
  registerReveal(loading);
  container.appendChild(loading);

  const data = await apiGet(`/search/documents?q=${encodeURIComponent(search)}&limit=5`);
  container.innerHTML = '';

  const results = Array.isArray(data?.results) ? data.results : [];
  if (!results.length) {
    const empty = document.createElement('div');
    empty.className = 'search-card';
    empty.textContent = 'No results found.';
    registerReveal(empty);
    container.appendChild(empty);
    return;
  }

  results.forEach(result => {
    const card = document.createElement('article');
    card.className = 'search-card';
    registerReveal(card);

    const source = document.createElement('div');
    source.className = 'search-card__source';
    source.textContent = result.source || 'document';

    const title = document.createElement('strong');
    title.textContent = result.title || result.chunk_id || 'Matched document';

    const excerpt = document.createElement('div');
    excerpt.className = 'search-card__excerpt';
    excerpt.textContent = result.content || '';

    card.appendChild(source);
    card.appendChild(title);
    card.appendChild(excerpt);
    container.appendChild(card);
  });
}

async function runPrediction() {
  const button = $('predictBtn');
  const result = $('predictionResult');
  if (button) {
    button.disabled = true;
    button.textContent = 'Analyzing...';
  }

  const payload = {
    sensor_data: {
      type: $('machineType')?.value || 'M',
      air_temp_k: Number($('airTemp')?.value || 305),
      process_temp_k: Number($('processTemp')?.value || 315),
      rotational_speed_rpm: Number($('rotSpeed')?.value || 1800),
      torque_nm: Number($('torque')?.value || 50),
      tool_wear_min: Number($('toolWear')?.value || 120),
    },
    save_to_db: true,
  };

  const response = await apiPost('/predict/failure', payload);

  if (button) {
    button.disabled = false;
    button.textContent = 'Analyze machine';
  }

  renderPredictionResult(response);

  if (response) {
    await loadDashboardData();
  }
}

function setupRangeLabels() {
  [
    ['airTemp', 'airTempVal', ' K'],
    ['processTemp', 'processTempVal', ' K'],
    ['rotSpeed', 'rotSpeedVal', ' RPM'],
    ['torque', 'torqueVal', ' Nm'],
    ['toolWear', 'toolWearVal', ' min'],
  ].forEach(([inputId, labelId, suffix]) => {
    const input = $(inputId);
    const label = $(labelId);
    if (!input || !label) return;

    const update = () => {
      label.textContent = `${input.value}${suffix}`;
    };

    input.addEventListener('input', update);
    update();
  });
}

function setupMachineTypes() {
  const buttons = document.querySelectorAll('#machineTypeGroup .segment');
  const hidden = $('machineType');
  buttons.forEach(button => {
    button.addEventListener('click', () => {
      buttons.forEach(btn => btn.classList.remove('is-active'));
      button.classList.add('is-active');
      if (hidden) hidden.value = button.dataset.value || 'M';
    });
  });
}

function setupAgentCards() {
  const cards = document.querySelectorAll('.agent-card');
  const map = {
    maintenance: 'Maintenance',
    analytics: 'Analytics',
    ml_insight: 'ML insight',
  };

  cards.forEach(card => {
    card.addEventListener('click', () => {
      cards.forEach(item => item.classList.remove('is-active'));
      card.classList.add('is-active');
      state.currentAgent = card.dataset.agent || 'maintenance';
      setText('currentAgentName', map[state.currentAgent] || 'Maintenance');
    });
  });
}

function setupChatPresets() {
  document.querySelectorAll('.preset-chip').forEach(chip => {
    chip.addEventListener('click', () => {
      const input = $('agentInput');
      if (input) {
        input.value = chip.textContent || '';
        input.focus();
      }
    });
  });
}

function setupNavigation() {
  document.querySelectorAll('[data-scroll]').forEach(button => {
    button.addEventListener('click', () => scrollToId(button.dataset.scroll));
  });

  const brand = document.querySelector('.brand');
  if (brand) {
    brand.addEventListener('click', e => {
      e.preventDefault();
      scrollToId('#overview');
    });
  }

  document.querySelectorAll('.topnav-link').forEach(link => {
    link.addEventListener('click', e => {
      e.preventDefault();
      const target = link.getAttribute('href');
      if (target && target.startsWith('#')) {
        setTimeout(() => scrollToId(target), 0);
      }
    });
  });

  document.querySelectorAll('section[id]').forEach(section => {
    if (sectionObserver) {
      sectionObserver.observe(section);
    }
  });
}

function setupButtons() {
  const predictForm = $('predictionForm');
  if (predictForm) {
    predictForm.addEventListener('submit', e => {
      e.preventDefault();
      runPrediction();
    });
  }

  const searchBtn = $('searchBtn');
  if (searchBtn) {
    searchBtn.addEventListener('click', () => executeSearch());
  }

  const searchInput = $('searchInput');
  if (searchInput) {
    searchInput.addEventListener('keydown', e => {
      if (e.key === 'Enter') {
        e.preventDefault();
        executeSearch();
      }
    });
  }

  const sendBtn = $('agentSendBtn');
  if (sendBtn) {
    sendBtn.addEventListener('click', () => sendAgentMessage());
  }

  const agentInput = $('agentInput');
  if (agentInput) {
    agentInput.addEventListener('keydown', e => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendAgentMessage();
      }
    });
  }

  const refreshBtn = $('refreshDashboardBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => refreshAll());
  }
}

async function refreshAll() {
  await Promise.all([
    loadDashboardData(),
    loadAgentStatus(),
    loadSystemStatus(),
  ]);
}

async function checkApiHealth() {
  const health = await apiGet('/health', 5000);
  if (health?.status === 'healthy') {
    setHealthIndicator(true, 'API online');
  } else {
    setHealthIndicator(false, 'API offline');
  }
}

function init() {
  setupNavigation();
  setupRangeLabels();
  setupMachineTypes();
  setupAgentCards();
  setupChatPresets();
  setupButtons();
  setText('currentAgentName', 'Maintenance');

  document.querySelectorAll('.panel, .glass-card, .kpi-card, .chart-panel, .status-card, .stack-card')
    .forEach(registerReveal);

  checkApiHealth();
  refreshAll();

  if (location.hash) {
    setTimeout(() => scrollToId(location.hash), 100);
  } else {
    setActiveNav('#overview');
  }

  setInterval(checkApiHealth, 30000);
  setInterval(refreshAll, 30000);
}

document.addEventListener('DOMContentLoaded', init);
