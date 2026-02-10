/* ============================================
   ScholarFinder — Main Script
   © 2026 Scott Antwi | Alpha Global Minds
   ============================================ */

(function () {
    'use strict';

    // ==========================================
    // DATA STORE
    // ==========================================
    const DATA = {
        scholarships: [],
        universities: [],
        opportunities: [],
        cost: [],
        visa: [],
        faq: [],
        testPrep: {},
        essays: {}
    };

    // Pagination state
    const PAGE_SIZE = 12;
    const pageState = {
        scholarships: PAGE_SIZE,
        universities: PAGE_SIZE,
        opportunities: PAGE_SIZE
    };

    // ==========================================
    // UTILITIES
    // ==========================================
    function debounce(fn, ms) {
        let timer;
        return function (...args) {
            clearTimeout(timer);
            timer = setTimeout(() => fn.apply(this, args), ms);
        };
    }

    function $(sel, ctx) { return (ctx || document).querySelector(sel); }
    function $$(sel, ctx) { return [...(ctx || document).querySelectorAll(sel)]; }

    function escapeHtml(str) {
        if (!str) return '';
        return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
    }

    function matchesSearch(text, query) {
        if (!query) return true;
        const lower = query.toLowerCase();
        return String(text).toLowerCase().includes(lower);
    }

    function arrayIncludes(arr, val) {
        if (!val) return true;
        if (Array.isArray(arr)) return arr.some(a => a.toLowerCase() === val.toLowerCase());
        return String(arr).toLowerCase() === val.toLowerCase();
    }

    function getRegion(country) {
        const regions = {
            'Europe': ['UK', 'Germany', 'France', 'Netherlands', 'Sweden', 'Norway', 'Finland', 'Denmark', 'Switzerland', 'Austria', 'Italy', 'Ireland', 'Poland', 'Czech Republic', 'Hungary', 'Romania', 'Russia', 'Spain'],
            'North America': ['USA', 'Canada'],
            'Asia': ['Japan', 'South Korea', 'China', 'India', 'Singapore', 'Hong Kong', 'Taiwan', 'Saudi Arabia', 'UAE', 'Qatar', 'Brunei', 'Turkey'],
            'Africa': ['Ghana', 'Nigeria', 'South Africa', 'Kenya', 'Ethiopia', 'Rwanda', 'Uganda', 'Tanzania', 'Egypt', 'Multiple (Africa)'],
            'Oceania': ['Australia', 'New Zealand'],
            'South America': ['Brazil', 'Chile', 'Mexico']
        };
        for (const [region, countries] of Object.entries(regions)) {
            if (countries.includes(country)) return region;
        }
        return 'Other';
    }

    // ==========================================
    // DATA LOADING
    // ==========================================
    async function fetchJSON(path) {
        try {
            const resp = await fetch(path);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            return await resp.json();
        } catch (e) {
            console.error(`Failed to load ${path}:`, e);
            return null;
        }
    }

    async function loadAllData() {
        const [scholarships, universities, opportunities, cost, visa, faq, testPrep, essays] = await Promise.all([
            fetchJSON('data/scholarships.json'),
            fetchJSON('data/universities.json'),
            fetchJSON('data/opportunities.json'),
            fetchJSON('data/cost_data.json'),
            fetchJSON('data/visa_data.json'),
            fetchJSON('data/faq_data.json'),
            fetchJSON('data/test_prep_data.json'),
            fetchJSON('data/essay_guides.json')
        ]);

        DATA.scholarships = scholarships || [];
        DATA.universities = universities || [];
        DATA.opportunities = opportunities || [];
        DATA.cost = cost || [];
        DATA.visa = visa || [];
        DATA.faq = faq || [];
        DATA.testPrep = testPrep || {};
        DATA.essays = essays || {};
    }

    // ==========================================
    // NAVIGATION
    // ==========================================
    function initNavigation() {
        const hamburger = $('#hamburger');
        const navMenu = $('#navMenu');
        const navbar = $('#navbar');

        // Create overlay
        const overlay = document.createElement('div');
        overlay.className = 'nav-overlay';
        document.body.appendChild(overlay);

        function toggleMenu() {
            hamburger.classList.toggle('active');
            navMenu.classList.toggle('open');
            overlay.classList.toggle('visible');
            document.body.style.overflow = navMenu.classList.contains('open') ? 'hidden' : '';
        }

        function closeMenu() {
            hamburger.classList.remove('active');
            navMenu.classList.remove('open');
            overlay.classList.remove('visible');
            document.body.style.overflow = '';
        }

        hamburger.addEventListener('click', toggleMenu);
        overlay.addEventListener('click', closeMenu);

        $$('.nav-link').forEach(link => {
            link.addEventListener('click', closeMenu);
        });

        // Navbar scroll effect
        let lastScroll = 0;
        window.addEventListener('scroll', () => {
            const scrollY = window.scrollY;
            navbar.classList.toggle('scrolled', scrollY > 50);

            // Update active nav link
            const sections = $$('.section');
            let current = '';
            sections.forEach(sec => {
                const top = sec.offsetTop - 100;
                if (scrollY >= top) current = sec.id;
            });
            $$('.nav-link').forEach(link => {
                link.classList.toggle('active', link.dataset.section === current);
            });

            lastScroll = scrollY;
        }, { passive: true });

        // Back to top
        const btn = $('#backToTop');
        window.addEventListener('scroll', () => {
            btn.classList.toggle('visible', window.scrollY > 600);
        }, { passive: true });
        btn.addEventListener('click', () => {
            window.scrollTo({ top: 0, behavior: 'smooth' });
        });
    }

    // ==========================================
    // HERO — Stat Counters
    // ==========================================
    function animateCounters() {
        const counters = $$('.stat-number');
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const el = entry.target;
                    const target = parseInt(el.dataset.target);
                    let current = 0;
                    const increment = Math.ceil(target / 60);
                    const timer = setInterval(() => {
                        current += increment;
                        if (current >= target) {
                            current = target;
                            clearInterval(timer);
                        }
                        el.textContent = current;
                    }, 25);
                    observer.unobserve(el);
                }
            });
        }, { threshold: 0.5 });

        counters.forEach(c => observer.observe(c));
    }

    // ==========================================
    // GLOBAL SEARCH
    // ==========================================
    function initGlobalSearch() {
        const input = $('#globalSearch');
        const clearBtn = $('#searchClear');

        const handleSearch = debounce((query) => {
            clearBtn.classList.toggle('visible', query.length > 0);
            if (!query) return;
            // Navigate to scholarships section and apply filter
            document.getElementById('scholarships').scrollIntoView({ behavior: 'smooth' });
            $('#scholarshipSearch').value = query;
            filterScholarships();
        }, 400);

        input.addEventListener('input', () => handleSearch(input.value.trim()));
        clearBtn.addEventListener('click', () => {
            input.value = '';
            clearBtn.classList.remove('visible');
        });
    }

    // ==========================================
    // SCHOLARSHIPS
    // ==========================================
    function populateScholarshipFilters() {
        const fields = new Set();
        const countries = new Set();
        DATA.scholarships.forEach(s => {
            (Array.isArray(s.field) ? s.field : [s.field]).forEach(f => fields.add(f));
            countries.add(s.country);
        });

        const fieldSel = $('#scholarshipField');
        [...fields].sort().forEach(f => {
            const opt = document.createElement('option');
            opt.value = f;
            opt.textContent = f.charAt(0).toUpperCase() + f.slice(1);
            fieldSel.appendChild(opt);
        });

        const regionSel = $('#scholarshipRegion');
        [...countries].sort().forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = c;
            regionSel.appendChild(opt);
        });
    }

    function filterScholarships() {
        const query = ($('#scholarshipSearch').value || '').trim();
        const level = $('#scholarshipLevel').value;
        const field = $('#scholarshipField').value;
        const region = $('#scholarshipRegion').value;

        const filtered = DATA.scholarships.filter(s => {
            const text = `${s.name} ${s.university} ${s.country} ${s.description} ${s.funding}`;
            if (!matchesSearch(text, query)) return false;
            if (level && !arrayIncludes(s.level, level)) return false;
            if (field && !arrayIncludes(s.field, field)) return false;
            if (region && s.country !== region) return false;
            return true;
        });

        pageState.scholarships = PAGE_SIZE;
        renderScholarships(filtered);
    }

    function renderScholarships(list) {
        const grid = $('#scholarshipGrid');
        const info = $('#scholarshipResultsInfo');
        const loadMore = $('#scholarshipLoadMore');
        const visible = list.slice(0, pageState.scholarships);

        info.textContent = `Showing ${Math.min(pageState.scholarships, list.length)} of ${list.length} scholarships`;

        if (list.length === 0) {
            grid.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🔍</div><div class="empty-state-text">No scholarships found. Try adjusting your filters.</div></div>`;
            loadMore.style.display = 'none';
            return;
        }

        grid.innerHTML = visible.map((s, i) => {
            const levels = (Array.isArray(s.level) ? s.level : [s.level]).map(l =>
                `<span class="card-badge badge-level">${escapeHtml(l)}</span>`
            ).join('');
            const fields = (Array.isArray(s.field) ? s.field : [s.field]).map(f =>
                `<span class="card-tag">${escapeHtml(f)}</span>`
            ).join('');

            return `<div class="card" style="animation-delay:${i * 0.05}s">
                <div class="card-header">
                    <h3 class="card-title">${escapeHtml(s.name)}</h3>
                    <span class="card-badge badge-funding">💰 Funded</span>
                </div>
                <div class="card-meta">
                    <span class="card-meta-item">🏫 ${escapeHtml(s.university)}</span>
                    <span class="card-meta-item">📍 ${escapeHtml(s.country)}</span>
                    ${levels}
                </div>
                <p class="card-description">${escapeHtml(s.description)}</p>
                <div class="card-tags">${fields}</div>
                <div class="card-meta" style="margin-bottom:12px">
                    <span class="card-meta-item">💵 ${escapeHtml(s.funding)}</span>
                </div>
                <div class="card-footer">
                    <span class="card-deadline">📅 ${escapeHtml(s.deadline)}</span>
                    <a href="${escapeHtml(s.link)}" target="_blank" rel="noopener" class="card-link">Apply →</a>
                </div>
            </div>`;
        }).join('');

        loadMore.style.display = pageState.scholarships < list.length ? 'block' : 'none';
        loadMore.onclick = () => {
            pageState.scholarships += PAGE_SIZE;
            renderScholarships(list);
        };
    }

    function initScholarships() {
        populateScholarshipFilters();
        filterScholarships();

        const debouncedFilter = debounce(filterScholarships, 300);
        $('#scholarshipSearch').addEventListener('input', debouncedFilter);
        $('#scholarshipLevel').addEventListener('change', filterScholarships);
        $('#scholarshipField').addEventListener('change', filterScholarships);
        $('#scholarshipRegion').addEventListener('change', filterScholarships);
    }

    // ==========================================
    // UNIVERSITIES
    // ==========================================
    function populateUniversityFilters() {
        const countries = new Set();
        const fields = new Set();
        DATA.universities.forEach(u => {
            countries.add(u.country);
            (Array.isArray(u.fields) ? u.fields : [u.fields]).forEach(f => fields.add(f));
        });

        const regionSel = $('#universityRegion');
        [...countries].sort().forEach(c => {
            const opt = document.createElement('option');
            opt.value = c;
            opt.textContent = c;
            regionSel.appendChild(opt);
        });

        const fieldSel = $('#universityField');
        [...fields].sort().forEach(f => {
            const opt = document.createElement('option');
            opt.value = f;
            opt.textContent = f.charAt(0).toUpperCase() + f.slice(1);
            fieldSel.appendChild(opt);
        });
    }

    function filterUniversities() {
        const query = ($('#universitySearch').value || '').trim();
        const region = $('#universityRegion').value;
        const tier = $('#universityTier').value;
        const tuition = $('#universityTuition').value;
        const field = $('#universityField').value;

        const filtered = DATA.universities.filter(u => {
            const text = `${u.name} ${u.country} ${u.notes} ${(u.fields || []).join(' ')}`;
            if (!matchesSearch(text, query)) return false;
            if (region && u.country !== region) return false;
            if (tier && u.ranking_tier !== tier) return false;
            if (tuition && u.tuition !== tuition) return false;
            if (field && !(u.fields || []).some(f => f.toLowerCase() === field.toLowerCase())) return false;
            return true;
        });

        pageState.universities = PAGE_SIZE;
        renderUniversities(filtered);
    }

    function renderUniversities(list) {
        const grid = $('#universityGrid');
        const info = $('#universityResultsInfo');
        const loadMore = $('#universityLoadMore');
        const visible = list.slice(0, pageState.universities);

        info.textContent = `Showing ${Math.min(pageState.universities, list.length)} of ${list.length} universities`;

        if (list.length === 0) {
            grid.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🏫</div><div class="empty-state-text">No universities found. Try adjusting your filters.</div></div>`;
            loadMore.style.display = 'none';
            return;
        }

        const tierLabels = { top10: '🏆 Top 10', top50: '⭐ Top 50', top100: '✨ Top 100', top200: '📊 Top 200', other: 'Ranked' };
        const tuitionColors = { free: 'badge-tuition-free', low: 'badge-tuition-low', medium: 'badge-tuition-medium', high: 'badge-tuition-high' };

        grid.innerHTML = visible.map((u, i) => {
            const fieldTags = (u.fields || []).map(f =>
                `<span class="card-tag">${escapeHtml(f)}</span>`
            ).join('');

            return `<div class="card" style="animation-delay:${i * 0.05}s">
                <div class="card-header">
                    <h3 class="card-title">${escapeHtml(u.name)}</h3>
                    <span class="card-badge badge-tier">${tierLabels[u.ranking_tier] || u.ranking_tier}</span>
                </div>
                <div class="card-meta">
                    <span class="card-meta-item">📍 ${escapeHtml(u.country)}</span>
                    <span class="card-badge ${tuitionColors[u.tuition] || ''}">💰 ${escapeHtml(u.tuition)} tuition</span>
                </div>
                <p class="card-description">${escapeHtml(u.notes)}</p>
                <div class="card-tags">${fieldTags}</div>
                <div class="card-footer">
                    <span></span>
                    <a href="${escapeHtml(u.website)}" target="_blank" rel="noopener" class="card-link">Visit Website →</a>
                </div>
            </div>`;
        }).join('');

        loadMore.style.display = pageState.universities < list.length ? 'block' : 'none';
        loadMore.onclick = () => {
            pageState.universities += PAGE_SIZE;
            renderUniversities(list);
        };
    }

    function initUniversities() {
        populateUniversityFilters();
        filterUniversities();

        const debouncedFilter = debounce(filterUniversities, 300);
        $('#universitySearch').addEventListener('input', debouncedFilter);
        $('#universityRegion').addEventListener('change', filterUniversities);
        $('#universityTier').addEventListener('change', filterUniversities);
        $('#universityTuition').addEventListener('change', filterUniversities);
        $('#universityField').addEventListener('change', filterUniversities);
    }

    // ==========================================
    // OPPORTUNITIES
    // ==========================================
    let currentOppType = '';

    function filterOpportunities() {
        const query = ($('#opportunitySearch').value || '').trim();

        const filtered = DATA.opportunities.filter(o => {
            if (currentOppType && o.type !== currentOppType) return false;
            const text = `${o.name} ${o.organization} ${o.country} ${o.description} ${o.field}`;
            if (!matchesSearch(text, query)) return false;
            return true;
        });

        pageState.opportunities = PAGE_SIZE;
        renderOpportunities(filtered);
    }

    function renderOpportunities(list) {
        const grid = $('#opportunityGrid');
        const info = $('#opportunityResultsInfo');
        const loadMore = $('#opportunityLoadMore');
        const visible = list.slice(0, pageState.opportunities);

        info.textContent = `Showing ${Math.min(pageState.opportunities, list.length)} of ${list.length} opportunities`;

        if (list.length === 0) {
            grid.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🚀</div><div class="empty-state-text">No opportunities found. Try a different filter.</div></div>`;
            loadMore.style.display = 'none';
            return;
        }

        const typeIcons = { internship: '💼', research: '🔬', competition: '🏆', fellowship: '🎖️', summer_school: '☀️', exchange: '🌐' };
        const typeLabels = { internship: 'Internship', research: 'Research', competition: 'Competition', fellowship: 'Fellowship', summer_school: 'Summer School', exchange: 'Exchange' };

        grid.innerHTML = visible.map((o, i) => `
            <div class="card" style="animation-delay:${i * 0.05}s">
                <div class="card-header">
                    <h3 class="card-title">${escapeHtml(o.name)}</h3>
                    <span class="card-badge badge-type">${typeIcons[o.type] || '📌'} ${typeLabels[o.type] || o.type}</span>
                </div>
                <div class="card-meta">
                    <span class="card-meta-item">🏢 ${escapeHtml(o.organization)}</span>
                    <span class="card-meta-item">📍 ${escapeHtml(o.country)}</span>
                    <span class="card-meta-item">📚 ${escapeHtml(o.field)}</span>
                </div>
                <p class="card-description">${escapeHtml(o.description)}</p>
                ${o.eligibility ? `<p class="card-description" style="font-size:0.83rem;color:var(--text-muted)"><strong style="color:var(--text-secondary)">Eligibility:</strong> ${escapeHtml(o.eligibility)}</p>` : ''}
                <div class="card-meta" style="margin-bottom:12px">
                    <span class="card-meta-item">💵 ${escapeHtml(o.funding)}</span>
                </div>
                <div class="card-footer">
                    <span class="card-deadline">📅 ${escapeHtml(o.deadline)}</span>
                    <a href="${escapeHtml(o.link)}" target="_blank" rel="noopener" class="card-link">Learn More →</a>
                </div>
            </div>
        `).join('');

        loadMore.style.display = pageState.opportunities < list.length ? 'block' : 'none';
        loadMore.onclick = () => {
            pageState.opportunities += PAGE_SIZE;
            renderOpportunities(list);
        };
    }

    function initOpportunities() {
        filterOpportunities();

        const debouncedFilter = debounce(filterOpportunities, 300);
        $('#opportunitySearch').addEventListener('input', debouncedFilter);

        $$('#opportunityTabs .tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                $$('#opportunityTabs .tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentOppType = btn.dataset.type;
                filterOpportunities();
            });
        });
    }

    // ==========================================
    // COST OF LIVING
    // ==========================================
    function renderCostCards(list) {
        const grid = $('#costGrid');
        const maxRent = Math.max(...DATA.cost.map(c => c.rent));

        if (list.length === 0) {
            grid.innerHTML = `<div class="empty-state"><div class="empty-state-icon">💰</div><div class="empty-state-text">No cities found.</div></div>`;
            return;
        }

        grid.innerHTML = list.map((c, i) => {
            const rentPct = (c.rent / maxRent * 100).toFixed(0);
            const foodPct = (c.food / maxRent * 100).toFixed(0);
            const transPct = (c.transport / maxRent * 100).toFixed(0);
            const netPct = (c.internet_phone / maxRent * 100).toFixed(0);
            const entPct = (c.entertainment / maxRent * 100).toFixed(0);

            return `<div class="card" style="animation-delay:${i * 0.05}s">
                <div class="card-header">
                    <h3 class="card-title">📍 ${escapeHtml(c.city)}</h3>
                    <span class="card-badge badge-level">${escapeHtml(c.country)}</span>
                </div>
                <div class="cost-card-bars">
                    <div class="cost-bar-item">
                        <div class="cost-bar-label"><span>🏠 Rent</span><span>$${c.rent}</span></div>
                        <div class="cost-bar-track"><div class="cost-bar-fill" style="width:${rentPct}%"></div></div>
                    </div>
                    <div class="cost-bar-item">
                        <div class="cost-bar-label"><span>🍔 Food</span><span>$${c.food}</span></div>
                        <div class="cost-bar-track"><div class="cost-bar-fill food" style="width:${foodPct}%"></div></div>
                    </div>
                    <div class="cost-bar-item">
                        <div class="cost-bar-label"><span>🚌 Transport</span><span>$${c.transport}</span></div>
                        <div class="cost-bar-track"><div class="cost-bar-fill transport" style="width:${transPct}%"></div></div>
                    </div>
                    <div class="cost-bar-item">
                        <div class="cost-bar-label"><span>📱 Internet/Phone</span><span>$${c.internet_phone}</span></div>
                        <div class="cost-bar-track"><div class="cost-bar-fill internet" style="width:${netPct}%"></div></div>
                    </div>
                    <div class="cost-bar-item">
                        <div class="cost-bar-label"><span>🎭 Entertainment</span><span>$${c.entertainment}</span></div>
                        <div class="cost-bar-track"><div class="cost-bar-fill entertainment" style="width:${entPct}%"></div></div>
                    </div>
                    <div class="cost-total">
                        <span>Total / month</span>
                        <span class="cost-total-amount">$${c.total}</span>
                    </div>
                </div>
                ${c.tips ? `<div class="cost-tip">💡 ${escapeHtml(c.tips)}</div>` : ''}
            </div>`;
        }).join('');
    }

    function initCost() {
        renderCostCards(DATA.cost);

        const search = $('#costSearch');
        search.addEventListener('input', debounce(() => {
            const q = search.value.trim();
            const filtered = DATA.cost.filter(c => {
                const text = `${c.city} ${c.country}`;
                return matchesSearch(text, q);
            });
            renderCostCards(filtered);
        }, 300));

        // Compare functionality
        const toggleBtn = $('#toggleCompare');
        const panel = $('#comparePanel');
        const sel1 = $('#compareCity1');
        const sel2 = $('#compareCity2');
        const results = $('#compareResults');

        DATA.cost.forEach(c => {
            const opt1 = document.createElement('option');
            opt1.value = c.city;
            opt1.textContent = `${c.city}, ${c.country}`;
            sel1.appendChild(opt1);

            const opt2 = opt1.cloneNode(true);
            sel2.appendChild(opt2);
        });

        toggleBtn.addEventListener('click', () => {
            const isVisible = panel.style.display !== 'none';
            panel.style.display = isVisible ? 'none' : 'block';
            toggleBtn.textContent = isVisible ? '📊 Compare Two Cities' : '✕ Close Compare';
        });

        function updateCompare() {
            const c1 = DATA.cost.find(c => c.city === sel1.value);
            const c2 = DATA.cost.find(c => c.city === sel2.value);
            if (!c1 || !c2) { results.innerHTML = ''; return; }

            const categories = [
                { label: '🏠 Rent', key: 'rent' },
                { label: '🍔 Food', key: 'food' },
                { label: '🚌 Transport', key: 'transport' },
                { label: '📱 Net/Phone', key: 'internet_phone' },
                { label: '🎭 Fun', key: 'entertainment' },
                { label: '💰 Total', key: 'total' }
            ];

            const maxVal = Math.max(c1.total, c2.total);

            results.innerHTML = `
                <div style="display:flex;justify-content:space-between;margin-bottom:12px;font-weight:600;">
                    <span></span>
                    <span style="color:var(--accent-blue);">${escapeHtml(c1.city)}</span>
                    <span style="color:var(--success);">${escapeHtml(c2.city)}</span>
                </div>
                ${categories.map(cat => {
                    const v1 = c1[cat.key];
                    const v2 = c2[cat.key];
                    const max = Math.max(v1, v2) || 1;
                    return `<div class="compare-bar-group">
                        <span class="compare-bar-label">${cat.label}</span>
                        <div class="compare-bar-wrapper">
                            <div class="compare-bar compare-bar-1" style="width:${(v1 / max * 100).toFixed(0)}%">$${v1}</div>
                        </div>
                        <div class="compare-bar-wrapper">
                            <div class="compare-bar compare-bar-2" style="width:${(v2 / max * 100).toFixed(0)}%">$${v2}</div>
                        </div>
                    </div>`;
                }).join('')}
                <div style="text-align:center;margin-top:16px;padding:12px;background:rgba(67,97,238,0.08);border-radius:8px;">
                    <span style="font-size:0.9rem;color:var(--text-secondary);">
                        ${c1.total < c2.total
                            ? `💡 <strong>${escapeHtml(c1.city)}</strong> is <strong style="color:var(--success);">$${c2.total - c1.total}/month cheaper</strong> than ${escapeHtml(c2.city)}`
                            : c1.total > c2.total
                                ? `💡 <strong>${escapeHtml(c2.city)}</strong> is <strong style="color:var(--success);">$${c1.total - c2.total}/month cheaper</strong> than ${escapeHtml(c1.city)}`
                                : `💡 Both cities cost the same!`
                        }
                    </span>
                </div>`;
        }

        sel1.addEventListener('change', updateCompare);
        sel2.addEventListener('change', updateCompare);
    }

    // ==========================================
    // VISA GUIDE
    // ==========================================
    function renderVisaCards(list) {
        const grid = $('#visaGrid');

        if (list.length === 0) {
            grid.innerHTML = `<div class="empty-state"><div class="empty-state-icon">🛂</div><div class="empty-state-text">No visa information found.</div></div>`;
            return;
        }

        grid.innerHTML = list.map((v, i) => `
            <div class="card visa-card" style="animation-delay:${i * 0.05}s">
                <div class="card-header">
                    <h3 class="card-title">🛂 ${escapeHtml(v.country)} — ${escapeHtml(v.visa_type)}</h3>
                </div>
                <div class="visa-info-grid">
                    <div class="visa-info-item">
                        <div class="visa-info-label">Processing Time</div>
                        <div class="visa-info-value">⏱️ ${escapeHtml(v.processing_time)}</div>
                    </div>
                    <div class="visa-info-item">
                        <div class="visa-info-label">Estimated Cost</div>
                        <div class="visa-info-value">💰 ${escapeHtml(v.cost_estimate)}</div>
                    </div>
                </div>
                <div class="visa-docs">
                    <div class="visa-docs-title">📋 Required Documents</div>
                    <ul class="visa-doc-list">
                        ${(v.documents || []).map(d => `<li>${escapeHtml(d)}</li>`).join('')}
                    </ul>
                </div>
                ${v.tips ? `<div class="cost-tip">💡 ${escapeHtml(v.tips)}</div>` : ''}
                <div class="card-footer" style="margin-top:16px">
                    <span></span>
                    <a href="${escapeHtml(v.embassy_link)}" target="_blank" rel="noopener" class="card-link">Embassy Info →</a>
                </div>
            </div>
        `).join('');
    }

    function initVisa() {
        renderVisaCards(DATA.visa);

        const search = $('#visaSearch');
        search.addEventListener('input', debounce(() => {
            const q = search.value.trim();
            const filtered = DATA.visa.filter(v =>
                matchesSearch(`${v.country} ${v.visa_type}`, q)
            );
            renderVisaCards(filtered);
        }, 300));
    }

    // ==========================================
    // TEST PREP
    // ==========================================
    function initTestPrep() {
        const grid = $('#testPrepGrid');
        const testIcons = { ielts: '🇬🇧', toefl: '🇺🇸', duolingo: '🦉', sat: '📝', gre: '🎓' };

        grid.innerHTML = Object.entries(DATA.testPrep).map(([key, test]) => {
            const formatRows = test.format ? Object.entries(test.format).map(([k, v]) =>
                `<div class="test-detail-row"><span>${escapeHtml(k)}</span><span>${escapeHtml(v)}</span></div>`
            ).join('') : '';

            const reqRows = test.common_requirements ? Object.entries(test.common_requirements).map(([k, v]) =>
                `<div class="test-detail-row"><span>${escapeHtml(k)}</span><span>${escapeHtml(v)}</span></div>`
            ).join('') : '';

            const resources = (test.free_prep_resources || []).map(r => {
                const urlMatch = r.match(/(https?:\/\/[^\s)]+)/);
                const text = r.replace(/(https?:\/\/[^\s)]+)/g, '').replace(/\s*—\s*$/, '').trim();
                return `<li>${escapeHtml(text)}${urlMatch ? ` — <a href="${escapeHtml(urlMatch[1])}" target="_blank" rel="noopener">${escapeHtml(urlMatch[1])}</a>` : ''}</li>`;
            }).join('');

            const tips = (test.tips || []).map(t => `<li>${escapeHtml(t)}</li>`).join('');

            return `<div class="card test-card" data-test="${key}">
                <div class="test-card-header" onclick="this.parentElement.classList.toggle('expanded')">
                    <div>
                        <h3 class="card-title">${testIcons[key] || '📝'} ${escapeHtml(key.toUpperCase())} — ${escapeHtml(test.full_name)}</h3>
                        <div class="card-meta" style="margin-top:8px">
                            <span class="card-meta-item">💰 ${escapeHtml(test.cost)}</span>
                            <span class="card-meta-item">📅 Valid: ${escapeHtml(test.validity)}</span>
                        </div>
                    </div>
                    <span class="test-card-toggle">+</span>
                </div>
                <div class="test-card-details">
                    ${test.types ? `<div class="test-detail-section"><div class="test-detail-title">Types</div><p style="font-size:0.85rem;color:var(--text-secondary)">${(test.types || []).map(escapeHtml).join(' • ')}</p></div>` : ''}
                    ${formatRows ? `<div class="test-detail-section"><div class="test-detail-title">Format</div><div class="test-detail-grid">${formatRows}</div></div>` : ''}
                    ${test.scoring ? `<div class="test-detail-section"><div class="test-detail-title">Scoring</div><p style="font-size:0.85rem;color:var(--text-secondary)">${escapeHtml(test.scoring)}</p></div>` : ''}
                    ${reqRows ? `<div class="test-detail-section"><div class="test-detail-title">Common Requirements</div><div class="test-detail-grid">${reqRows}</div></div>` : ''}
                    ${test.test_centers_ghana ? `<div class="test-detail-section"><div class="test-detail-title">Test Centers (Ghana)</div><p style="font-size:0.85rem;color:var(--text-secondary)">${escapeHtml(test.test_centers_ghana)}</p></div>` : ''}
                    ${resources ? `<div class="test-detail-section"><div class="test-detail-title">Free Prep Resources</div><ul class="test-resource-list">${resources}</ul></div>` : ''}
                    ${tips ? `<div class="test-detail-section"><div class="test-detail-title">Top Tips</div><ul class="test-tips-list">${tips}</ul></div>` : ''}
                </div>
            </div>`;
        }).join('');
    }

    // ==========================================
    // ESSAYS
    // ==========================================
    function initEssays() {
        const tabs = $('#essayTabs');
        const content = $('#essayContent');
        const keys = Object.keys(DATA.essays);

        if (keys.length === 0) return;

        tabs.innerHTML = keys.map((key, i) => {
            const guide = DATA.essays[key];
            return `<button class="tab-btn ${i === 0 ? 'active' : ''}" data-key="${key}">${escapeHtml(guide.title)}</button>`;
        }).join('');

        function showGuide(key) {
            const guide = DATA.essays[key];
            if (!guide) return;
            content.innerHTML = `<div class="essay-content-title">${escapeHtml(guide.title)}</div>${escapeHtml(guide.content)}`;
        }

        showGuide(keys[0]);

        $$('#essayTabs .tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                $$('#essayTabs .tab-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                showGuide(btn.dataset.key);
            });
        });
    }

    // ==========================================
    // FAQ
    // ==========================================
    function renderFAQ(list) {
        const accordion = $('#faqAccordion');

        if (list.length === 0) {
            accordion.innerHTML = `<div class="empty-state"><div class="empty-state-icon">❓</div><div class="empty-state-text">No matching questions found.</div></div>`;
            return;
        }

        accordion.innerHTML = list.map((faq, i) => `
            <div class="accordion-item">
                <button class="accordion-header" onclick="this.parentElement.classList.toggle('open');const b=this.nextElementSibling;b.style.maxHeight=b.style.maxHeight?null:b.scrollHeight+'px';">
                    <span>${escapeHtml(faq.question)}</span>
                    <span class="accordion-icon">+</span>
                </button>
                <div class="accordion-body">
                    <div class="accordion-body-inner">${escapeHtml(faq.answer)}</div>
                </div>
            </div>
        `).join('');
    }

    function initFAQ() {
        renderFAQ(DATA.faq);

        const search = $('#faqSearch');
        search.addEventListener('input', debounce(() => {
            const q = search.value.trim().toLowerCase();
            if (!q) { renderFAQ(DATA.faq); return; }
            const filtered = DATA.faq.filter(f => {
                const text = `${f.question} ${f.answer} ${(f.keywords || []).join(' ')}`;
                return text.toLowerCase().includes(q);
            });
            renderFAQ(filtered);
        }, 300));
    }

    // ==========================================
    // INTERSECTION OBSERVER FOR LAZY SECTIONS
    // ==========================================
    function initLazyLoad() {
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('section-visible');
                }
            });
        }, { threshold: 0.05, rootMargin: '50px' });

        $$('.section').forEach(sec => observer.observe(sec));
    }

    // ==========================================
    // INIT
    // ==========================================
    // ==========================================
    // TYPEWRITER EFFECT
    // ==========================================
    function initTypewriter() {
        const messages = [
            "🔍 Search 151+ scholarships across 46 countries",
            "🏫 Explore 86 top universities worldwide",
            "🌍 Find internships, research programs & competitions",
            "💰 Compare cost of living in 51+ cities",
            "🛂 Get visa guides for 26 countries",
            "📚 IELTS, TOEFL, SAT, GRE prep resources",
            "📝 Essay templates & writing guides",
            "🤖 Join our Telegram bot for personalized picks",
            "🎓 Built by Scott Antwi — Alpha Global Minds",
        ];
        const el = document.getElementById('typewriterText');
        if (!el) return;

        let msgIndex = 0;
        let charIndex = 0;
        let deleting = false;
        const typeSpeed = 40;
        const deleteSpeed = 25;
        const pauseAfterType = 2000;
        const pauseAfterDelete = 400;

        function tick() {
            const currentMsg = messages[msgIndex];
            if (!deleting) {
                el.textContent = currentMsg.substring(0, charIndex + 1);
                charIndex++;
                if (charIndex === currentMsg.length) {
                    deleting = true;
                    setTimeout(tick, pauseAfterType);
                    return;
                }
                setTimeout(tick, typeSpeed);
            } else {
                el.textContent = currentMsg.substring(0, charIndex - 1);
                charIndex--;
                if (charIndex === 0) {
                    deleting = false;
                    msgIndex = (msgIndex + 1) % messages.length;
                    setTimeout(tick, pauseAfterDelete);
                    return;
                }
                setTimeout(tick, deleteSpeed);
            }
        }
        tick();
    }

    // ==========================================
    // FEATURE CARD NAVIGATION
    // ==========================================
    function initFeatureCards() {
        const featureCards = $$('.feature-card');
        const detailSections = $$('.detail-section');
        const featuresSection = $('#features');
        const heroSection = $('#hero');
        const backBtns = $$('.back-btn');

        function showSection(targetId) {
            // Hide hero, features, and all detail sections
            heroSection.style.display = 'none';
            featuresSection.style.display = 'none';
            detailSections.forEach(s => s.style.display = 'none');

            // Show the target section
            const target = document.getElementById(targetId);
            if (target) {
                target.style.display = '';
                window.scrollTo({ top: 0, behavior: 'instant' });
            }
        }

        function showHome() {
            detailSections.forEach(s => s.style.display = 'none');
            heroSection.style.display = '';
            featuresSection.style.display = '';
            window.scrollTo({ top: featuresSection.offsetTop - 80, behavior: 'smooth' });
        }

        featureCards.forEach(card => {
            function handleCardTap(e) {
                e.preventDefault();
                e.stopPropagation();
                const targetId = card.dataset.target;
                showSection(targetId);
                history.pushState({ section: targetId }, '', '#' + targetId);
            }
            card.addEventListener('click', handleCardTap);
            card.addEventListener('touchend', handleCardTap);
            card.style.cursor = 'pointer';
        });

        backBtns.forEach(btn => {
            function handleBack(e) {
                e.preventDefault();
                e.stopPropagation();
                showHome();
                history.pushState({ section: 'home' }, '', '#features');
            }
            btn.addEventListener('click', handleBack);
            btn.addEventListener('touchend', handleBack);
        });

        window.addEventListener('popstate', (e) => {
            if (e.state && e.state.section && e.state.section !== 'home') {
                showSection(e.state.section);
            } else {
                showHome();
            }
        });

        // Handle direct link to section (e.g. #scholarships)
        const hash = window.location.hash.replace('#', '');
        if (hash && document.getElementById(hash) && hash !== 'hero' && hash !== 'features') {
            setTimeout(() => showSection(hash), 100);
        }
    }

    async function init() {
        initNavigation();

        await loadAllData();

        // Hide loading overlay
        const overlay = $('#loadingOverlay');
        overlay.classList.add('hidden');
        setTimeout(() => overlay.remove(), 500);

        // Initialize all sections
        animateCounters();
        initTypewriter();
        initGlobalSearch();
        initFeatureCards();
        initScholarships();
        initUniversities();
        initOpportunities();
        initCost();
        initVisa();
        initTestPrep();
        initEssays();
        initFAQ();
        initLazyLoad();

        console.log('🎓 ScholarFinder loaded — © 2026 Scott Antwi | Alpha Global Minds');
    }

    // Start when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
})();

/* ==========================================
   CHAT WIDGET — Smart FAQ Assistant
   ========================================== */
(function() {
    const toggle = document.getElementById('chatToggle');
    const widget = document.getElementById('chatWidget');
    const minimize = document.getElementById('chatMinimize');
    const input = document.getElementById('chatInput');
    const sendBtn = document.getElementById('chatSend');
    const messages = document.getElementById('chatMessages');
    if (!toggle) return;

    let faqData = [];
    let scholarships = [];
    let chatOpen = false;
    let welcomed = false;

    // Load FAQ data
    fetch('data/faq_data.json').then(r => r.json()).then(d => faqData = d).catch(() => {});
    fetch('data/scholarships.json').then(r => r.json()).then(d => scholarships = d).catch(() => {});

    function addMsg(text, type) {
        const div = document.createElement('div');
        div.className = 'chat-msg ' + type;
        div.innerHTML = text;
        messages.appendChild(div);
        messages.scrollTop = messages.scrollHeight;
    }

    function welcome() {
        if (welcomed) return;
        welcomed = true;
        setTimeout(() => {
            addMsg("👋 Hi! I'm the ScholarFinder Assistant.", 'bot');
        }, 300);
        setTimeout(() => {
            addMsg("I can help you find scholarships, universities, visa info, test prep, and more. Just ask me anything!", 'bot');
        }, 800);
        setTimeout(() => {
            addMsg("Try asking:<br>• \"Scholarships in Germany\"<br>• \"What is IELTS?\"<br>• \"Cost of living in London\"<br>• \"Visa for USA\"", 'bot');
        }, 1500);
    }

    function findAnswer(query) {
        const q = query.toLowerCase().trim();

        // Check scholarships
        if (q.includes('scholarship') || q.includes('fund') || q.includes('grant')) {
            let country = null;
            const countries = ['usa', 'uk', 'germany', 'canada', 'japan', 'korea', 'australia', 'france', 'ghana', 'china', 'turkey', 'uae', 'saudi'];
            for (const c of countries) {
                if (q.includes(c)) { country = c; break; }
            }
            let results = scholarships;
            if (country) {
                results = scholarships.filter(s => s.country.toLowerCase().includes(country));
            }
            if (results.length > 0) {
                const top3 = results.slice(0, 3);
                let html = country ? `Found ${results.length} scholarship(s)` : `We have ${results.length} scholarships`;
                html += `. Here are some:<br><br>`;
                top3.forEach(s => {
                    html += `🎓 <strong>${s.name}</strong><br>📍 ${s.country} | 💰 ${s.funding}<br>📅 ${s.deadline}<br><br>`;
                });
                html += `<a href="#scholarships" style="color:#4361ee" onclick="document.getElementById('chatToggle').click()">See all →</a>`;
                return html;
            }
        }

        // Check cost of living
        if (q.includes('cost') || q.includes('living') || q.includes('expensive') || q.includes('cheap')) {
            return `💰 Check our <a href="#cost" style="color:#4361ee" onclick="document.getElementById('chatToggle').click()">Cost of Living</a> section! We cover 51 cities worldwide. You can search and compare cities side by side.`;
        }

        // Check visa
        if (q.includes('visa') || q.includes('passport') || q.includes('travel')) {
            return `🛂 Check our <a href="#visa" style="color:#4361ee" onclick="document.getElementById('chatToggle').click()">Visa Guide</a> section! We have guides for 26 countries with requirements, costs, and tips.`;
        }

        // Check tests
        if (q.includes('ielts') || q.includes('toefl') || q.includes('sat') || q.includes('gre') || q.includes('duolingo') || q.includes('test') || q.includes('exam')) {
            return `📚 Check our <a href="#testprep" style="color:#4361ee" onclick="document.getElementById('chatToggle').click()">Test Prep</a> section! We cover IELTS, TOEFL, SAT, GRE, and Duolingo with prep resources and tips.`;
        }

        // Check essay
        if (q.includes('essay') || q.includes('statement') || q.includes('sop') || q.includes('cv') || q.includes('resume') || q.includes('write')) {
            return `📝 Check our <a href="#essays" style="color:#4361ee" onclick="document.getElementById('chatToggle').click()">Essay Help</a> section! We have guides for personal statements, SOPs, CVs, and more.`;
        }

        // Check university
        if (q.includes('university') || q.includes('universities') || q.includes('school') || q.includes('college')) {
            return `🏫 Check our <a href="#universities" style="color:#4361ee" onclick="document.getElementById('chatToggle').click()">Universities</a> section! Browse 86 universities by region, field, and ranking.`;
        }

        // Check opportunities
        if (q.includes('internship') || q.includes('competition') || q.includes('fellowship') || q.includes('research') || q.includes('summer') || q.includes('exchange')) {
            return `🌍 Check our <a href="#opportunities" style="color:#4361ee" onclick="document.getElementById('chatToggle').click()">Opportunities</a> section! We have 62 internships, competitions, fellowships, and more.`;
        }

        // FAQ keyword matching
        if (faqData.length > 0) {
            let bestMatch = null;
            let bestScore = 0;
            const qWords = q.split(/\s+/);
            for (const faq of faqData) {
                const keywords = (faq.keywords || faq.question.toLowerCase().split(/\s+/));
                let score = 0;
                for (const w of qWords) {
                    if (w.length < 3) continue;
                    for (const k of keywords) {
                        if (k.includes(w) || w.includes(k)) score++;
                    }
                }
                if (score > bestScore) {
                    bestScore = score;
                    bestMatch = faq;
                }
            }
            if (bestMatch && bestScore >= 2) {
                return `${bestMatch.answer}`;
            }
        }

        // Greetings
        if (q.match(/^(hi|hello|hey|yo|sup|good morning|good afternoon)/)) {
            return `Hey there! 👋 How can I help you today? Ask me about scholarships, universities, visa requirements, test prep, or anything study-abroad related!`;
        }

        // Thanks
        if (q.match(/^(thanks|thank you|thx)/)) {
            return `You're welcome! 😊 Feel free to ask anything else. Good luck with your applications!`;
        }

        // Default
        return `I'm not sure about that, but try browsing our sections:<br><br>🎯 <a href="#scholarships" style="color:#4361ee">Scholarships</a><br>🏫 <a href="#universities" style="color:#4361ee">Universities</a><br>🌍 <a href="#opportunities" style="color:#4361ee">Opportunities</a><br>💰 <a href="#cost" style="color:#4361ee">Cost of Living</a><br>🛂 <a href="#visa" style="color:#4361ee">Visa Guide</a><br><br>Or join our <a href="https://t.me/ScholarFinder_bot" style="color:#4361ee" target="_blank">Telegram bot</a> for personalized help!`;
    }

    function sendMessage() {
        const text = input.value.trim();
        if (!text) return;
        addMsg(text, 'user');
        input.value = '';
        // Typing delay
        setTimeout(() => {
            const answer = findAnswer(text);
            addMsg(answer, 'bot');
        }, 500 + Math.random() * 500);
    }

    toggle.addEventListener('click', () => {
        chatOpen = !chatOpen;
        widget.classList.toggle('open', chatOpen);
        if (chatOpen) {
            welcome();
            setTimeout(() => input.focus(), 400);
        }
    });

    minimize.addEventListener('click', () => {
        chatOpen = false;
        widget.classList.remove('open');
    });

    sendBtn.addEventListener('click', sendMessage);
    input.addEventListener('keydown', (e) => {
        if (e.key === 'Enter') sendMessage();
    });
})();
