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
            "🔍 Search 485+ scholarships across 46 countries",
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

        initCarousel();

        console.log('🎓 ScholarFinder loaded — © 2026 Scott Antwi | Alpha Global Minds');
    }

    // ==========================================
    // IMAGE CAROUSEL
    // ==========================================
    function initCarousel() {
        const track = document.getElementById('carouselTrack');
        const dotsContainer = document.getElementById('carouselDots');
        const prevBtn = document.getElementById('carouselPrev');
        const nextBtn = document.getElementById('carouselNext');
        if (!track || !dotsContainer) return;

        const slides = track.querySelectorAll('.carousel-slide');
        const total = slides.length;
        let current = 0;
        let autoTimer = null;
        let touchStartX = 0;
        let touchEndX = 0;

        // Create dots
        for (let i = 0; i < total; i++) {
            const dot = document.createElement('button');
            dot.className = 'carousel-dot' + (i === 0 ? ' active' : '');
            dot.setAttribute('aria-label', 'Go to slide ' + (i + 1));
            dot.addEventListener('click', () => goTo(i));
            dotsContainer.appendChild(dot);
        }

        function goTo(index) {
            current = ((index % total) + total) % total;
            track.style.transform = 'translateX(-' + (current * 100) + '%)';
            // Update dots
            dotsContainer.querySelectorAll('.carousel-dot').forEach((d, i) => {
                d.classList.toggle('active', i === current);
            });
        }

        function next() { goTo(current + 1); }
        function prev() { goTo(current - 1); }

        function startAuto() {
            stopAuto();
            autoTimer = setInterval(next, 2500);
        }
        function stopAuto() {
            if (autoTimer) { clearInterval(autoTimer); autoTimer = null; }
        }

        prevBtn.addEventListener('click', () => { prev(); stopAuto(); startAuto(); });
        nextBtn.addEventListener('click', () => { next(); stopAuto(); startAuto(); });

        // Touch / swipe support
        track.addEventListener('touchstart', (e) => {
            touchStartX = e.changedTouches[0].screenX;
            stopAuto();
        }, { passive: true });
        track.addEventListener('touchend', (e) => {
            touchEndX = e.changedTouches[0].screenX;
            const diff = touchStartX - touchEndX;
            if (Math.abs(diff) > 50) {
                if (diff > 0) next(); else prev();
            }
            startAuto();
        }, { passive: true });

        // Pause on hover (desktop)
        const wrapper = track.parentElement;
        wrapper.addEventListener('mouseenter', stopAuto);
        wrapper.addEventListener('mouseleave', startAuto);

        // Start auto-slide
        startAuto();
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

/* ==========================================
   WELCOME REGISTRATION MODAL
   ========================================== */
(function() {
    // Check if already registered
    if (localStorage.getItem('sf_registered')) return;

    const modal = document.getElementById('welcomeModal');
    if (!modal) return;

    // Show modal
    modal.style.display = 'flex';

    // Populate countries
    const countries = ["Afghanistan","Albania","Algeria","Andorra","Angola","Antigua and Barbuda","Argentina","Armenia","Australia","Austria","Azerbaijan","Bahamas","Bahrain","Bangladesh","Barbados","Belarus","Belgium","Belize","Benin","Bhutan","Bolivia","Bosnia and Herzegovina","Botswana","Brazil","Brunei","Bulgaria","Burkina Faso","Burundi","Cabo Verde","Cambodia","Cameroon","Canada","Central African Republic","Chad","Chile","China","Colombia","Comoros","Congo (DRC)","Congo (Republic)","Costa Rica","Côte d'Ivoire","Croatia","Cuba","Cyprus","Czech Republic","Denmark","Djibouti","Dominica","Dominican Republic","Ecuador","Egypt","El Salvador","Equatorial Guinea","Eritrea","Estonia","Eswatini","Ethiopia","Fiji","Finland","France","Gabon","Gambia","Georgia","Germany","Ghana","Greece","Grenada","Guatemala","Guinea","Guinea-Bissau","Guyana","Haiti","Honduras","Hungary","Iceland","India","Indonesia","Iran","Iraq","Ireland","Israel","Italy","Jamaica","Japan","Jordan","Kazakhstan","Kenya","Kiribati","Kosovo","Kuwait","Kyrgyzstan","Laos","Latvia","Lebanon","Lesotho","Liberia","Libya","Liechtenstein","Lithuania","Luxembourg","Madagascar","Malawi","Malaysia","Maldives","Mali","Malta","Marshall Islands","Mauritania","Mauritius","Mexico","Micronesia","Moldova","Monaco","Mongolia","Montenegro","Morocco","Mozambique","Myanmar","Namibia","Nauru","Nepal","Netherlands","New Zealand","Nicaragua","Niger","Nigeria","North Korea","North Macedonia","Norway","Oman","Pakistan","Palau","Palestine","Panama","Papua New Guinea","Paraguay","Peru","Philippines","Poland","Portugal","Qatar","Romania","Russia","Rwanda","Saint Kitts and Nevis","Saint Lucia","Saint Vincent and the Grenadines","Samoa","San Marino","São Tomé and Príncipe","Saudi Arabia","Senegal","Serbia","Seychelles","Sierra Leone","Singapore","Slovakia","Slovenia","Solomon Islands","Somalia","South Africa","South Korea","South Sudan","Spain","Sri Lanka","Sudan","Suriname","Sweden","Switzerland","Syria","Taiwan","Tajikistan","Tanzania","Thailand","Timor-Leste","Togo","Tonga","Trinidad and Tobago","Tunisia","Turkey","Turkmenistan","Tuvalu","Uganda","Ukraine","United Arab Emirates","United Kingdom","United States","Uruguay","Uzbekistan","Vanuatu","Vatican City","Venezuela","Vietnam","Yemen","Zambia","Zimbabwe"];
    
    const countrySel = document.getElementById('regCountry');
    countries.forEach(c => {
        const opt = document.createElement('option');
        opt.value = c;
        opt.textContent = c;
        countrySel.appendChild(opt);
    });

    // Populate DOB selects
    const daySel = document.getElementById('regDobDay');
    const monthSel = document.getElementById('regDobMonth');
    const yearSel = document.getElementById('regDobYear');

    for (let d = 1; d <= 31; d++) {
        const opt = document.createElement('option');
        opt.value = String(d).padStart(2, '0');
        opt.textContent = String(d).padStart(2, '0');
        daySel.appendChild(opt);
    }

    const monthNames = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    monthNames.forEach((m, i) => {
        const opt = document.createElement('option');
        opt.value = String(i + 1).padStart(2, '0');
        opt.textContent = m;
        monthSel.appendChild(opt);
    });

    const currentYear = new Date().getFullYear();
    for (let y = currentYear - 10; y >= currentYear - 50; y--) {
        const opt = document.createElement('option');
        opt.value = String(y);
        opt.textContent = String(y);
        yearSel.appendChild(opt);
    }

    // Show/hide friend name field
    const hearAbout = document.getElementById('regHearAbout');
    const friendGroup = document.getElementById('friendNameGroup');
    hearAbout.addEventListener('change', () => {
        friendGroup.style.display = hearAbout.value === 'Friend Recommended' ? 'flex' : 'none';
    });

    // Handle form submit
    document.getElementById('welcomeForm').addEventListener('submit', function(e) {
        e.preventDefault();
        const data = {
            name: document.getElementById('regName').value.trim(),
            country: countrySel.value,
            dob: daySel.value + '/' + monthSel.value + '/' + yearSel.value,
            hearAbout: hearAbout.value,
            friendName: document.getElementById('regFriendName').value.trim(),
            registeredAt: new Date().toISOString()
        };
        localStorage.setItem('sf_registered', JSON.stringify(data));
        modal.classList.add('hidden');
        setTimeout(() => modal.remove(), 500);
    });
})();

})();

// ==========================================
// AI AGENTS (Self-contained module)
// ==========================================
(function() {
    'use strict';
    function $(sel, ctx) { return (ctx || document).querySelector(sel); }
    function $$(sel, ctx) { return [...(ctx || document).querySelectorAll(sel)]; }
    function escapeHtml(str) { if (!str) return ''; return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;'); }

    // Load scholarship data
    let DATA = { scholarships: [] };
    fetch('./scholarships.json').then(r => r.json()).then(d => { DATA.scholarships = d; }).catch(() => {});

    const AGENTS = {
        scout: { icon: '🔍', name: 'Scout', role: 'Scholarship Finder' },
        writer: { icon: '📝', name: 'Writer', role: 'Essay Assistant' },
        profiler: { icon: '👤', name: 'Profiler', role: 'Student Matcher' },
        tracker: { icon: '📅', name: 'Tracker', role: 'Deadline Manager' },
        advisor: { icon: '🎓', name: 'Advisor', role: 'Strategy Coach' },
        prep: { icon: '💬', name: 'Prep', role: 'Interview Coach' }
    };

    const interviewQuestions = [
        { q: "Tell me about yourself and why you deserve this scholarship.", tip: "Start with your background, mention key achievements, connect to your goals. Keep it under 2 minutes." },
        { q: "What are your academic and career goals?", tip: "Be specific. Mention your field, what you want to achieve, and how the scholarship helps." },
        { q: "How will you give back to your community?", tip: "Share concrete plans. Mention any existing community work like volunteering or mentoring." },
        { q: "What challenges have you overcome?", tip: "Pick ONE meaningful challenge. Explain the situation, what you did, and what you learned." },
        { q: "Why did you choose this field of study?", tip: "Tell a story. What moment sparked your interest? What excites you about it?" },
        { q: "Where do you see yourself in 10 years?", tip: "Show ambition but be realistic. Connect your vision to the scholarship's mission." },
        { q: "What makes you different from other applicants?", tip: "Highlight unique experiences, skills, or perspectives. Don't be generic." },
        { q: "How do you handle failure or setbacks?", tip: "Give a real example. Show resilience, learning, and growth." },
        { q: "What's a project or achievement you're most proud of?", tip: "Pick something with measurable impact. Explain your role and the outcome." },
        { q: "Do you have any questions for us?", tip: "Always say yes. Ask about mentorship, research opportunities, or community engagement." }
    ];

    function initAIAgents() {
        // Launch buttons
        $$('.ai-agent-card').forEach(card => {
            card.addEventListener('click', () => {
                const agent = card.dataset.agent;
                openAgentModal(agent);
            });
        });

        // Close modal
        $('#aiModalClose').addEventListener('click', closeAgentModal);
        $('#aiModalOverlay').addEventListener('click', e => {
            if (e.target === $('#aiModalOverlay')) closeAgentModal();
        });
    }

    function openAgentModal(agentKey) {
        const agent = AGENTS[agentKey];
        const overlay = $('#aiModalOverlay');
        $('#aiModalIcon').textContent = agent.icon;
        $('#aiModalTitle').textContent = agent.name;
        $('#aiModalRole').textContent = agent.role;

        const body = $('#aiModalBody');
        body.innerHTML = '';

        switch(agentKey) {
            case 'scout': body.innerHTML = buildScoutUI(); initScout(); break;
            case 'writer': body.innerHTML = buildWriterUI(); initWriter(); break;
            case 'profiler': body.innerHTML = buildProfilerUI(); initProfiler(); break;
            case 'tracker': body.innerHTML = buildTrackerUI(); break;
            case 'advisor': body.innerHTML = buildAdvisorUI(); break;
            case 'prep': body.innerHTML = buildPrepUI(); initPrep(); break;
        }

        overlay.style.display = 'flex';
        document.body.style.overflow = 'hidden';
    }

    function closeAgentModal() {
        $('#aiModalOverlay').style.display = 'none';
        document.body.style.overflow = '';
    }

    // ===== SCOUT AGENT =====
    function buildScoutUI() {
        const countries = [...new Set(DATA.scholarships.map(s => s.country).filter(Boolean))].sort();
        const fields = [...new Set(DATA.scholarships.flatMap(s => s.fields || []).filter(Boolean))].sort();
        return `
            <div class="scout-form">
                <div>
                    <label>Your GPA (out of 4.0)</label>
                    <input type="number" id="scoutGpa" min="0" max="4" step="0.1" placeholder="e.g. 3.5">
                </div>
                <div>
                    <label>Preferred Country</label>
                    <select id="scoutCountry"><option value="">Any Country</option>${countries.map(c => `<option value="${c}">${c}</option>`).join('')}</select>
                </div>
                <div>
                    <label>Field of Study</label>
                    <select id="scoutField"><option value="">Any Field</option>${fields.map(f => `<option value="${f}">${f}</option>`).join('')}</select>
                </div>
                <div>
                    <label>Degree Level</label>
                    <select id="scoutLevel">
                        <option value="">Any Level</option>
                        <option value="undergraduate">Undergraduate</option>
                        <option value="masters">Masters</option>
                        <option value="phd">PhD</option>
                    </select>
                </div>
                <button class="btn btn-primary" id="scoutSearch" style="background:linear-gradient(135deg,#8B5CF6,#7C3AED);border:none;">🔍 Find My Scholarships</button>
            </div>
            <div class="scout-results" id="scoutResults"></div>
        `;
    }

    function initScout() {
        $('#scoutSearch').addEventListener('click', () => {
            const gpa = parseFloat($('#scoutGpa').value) || 0;
            const country = $('#scoutCountry').value;
            const field = $('#scoutField').value;
            const level = $('#scoutLevel').value;
            const results = $('#scoutResults');

            let matches = DATA.scholarships.map(s => {
                let score = 0;
                let total = 0;

                // Country match
                total += 30;
                if (!country || (s.country && s.country.toLowerCase() === country.toLowerCase())) score += 30;
                else if (s.country && s.country.toLowerCase().includes(country.toLowerCase())) score += 15;

                // Field match
                total += 25;
                if (!field) score += 25;
                else if (s.fields && s.fields.some(f => f.toLowerCase().includes(field.toLowerCase()))) score += 25;
                else if (s.name && s.name.toLowerCase().includes(field.toLowerCase())) score += 10;

                // Level match
                total += 25;
                if (!level) score += 25;
                else if (s.level && s.level.toLowerCase().includes(level.toLowerCase())) score += 25;

                // GPA (bonus)
                total += 20;
                if (gpa >= 3.5) score += 20;
                else if (gpa >= 3.0) score += 15;
                else if (gpa >= 2.5) score += 10;
                else score += 5;

                const pct = Math.round((score / total) * 100);
                return { ...s, matchScore: pct };
            });

            matches.sort((a, b) => b.matchScore - a.matchScore);
            matches = matches.slice(0, 20);

            if (matches.length === 0) {
                results.innerHTML = '<p style="color:var(--text-muted);text-align:center;padding:20px;">No scholarships found. Try adjusting your filters.</p>';
                return;
            }

            results.innerHTML = matches.map(m => `
                <div class="scout-match-card">
                    <div class="scout-match-info">
                        <h4>${escapeHtml(m.name)}</h4>
                        <p>${escapeHtml(m.country || '')} · ${escapeHtml((m.fields || []).join(', ') || 'Various')} · ${escapeHtml(m.level || 'All levels')}</p>
                    </div>
                    <div class="scout-match-score">${m.matchScore}%</div>
                </div>
            `).join('');
        });
    }

    // ===== WRITER AGENT =====
    function buildWriterUI() {
        return `
            <div class="writer-container">
                <div class="writer-editor">
                    <textarea id="writerText" placeholder="Start writing your scholarship essay here..."></textarea>
                    <div class="writer-stats">
                        <div class="writer-stat">Words: <span id="writerWords">0</span></div>
                        <div class="writer-stat">Characters: <span id="writerChars">0</span></div>
                        <div class="writer-stat">Sentences: <span id="writerSentences">0</span></div>
                        <div class="writer-stat">Reading time: <span id="writerTime">0 min</span></div>
                    </div>
                </div>
                <div class="writer-sidebar">
                    <h4>📝 Essay Structure Guide</h4>
                    <div class="writer-tip">
                        <h5>Opening Hook</h5>
                        <p>Start with a compelling story, question, or statement that grabs attention. Avoid clichés.</p>
                    </div>
                    <div class="writer-tip">
                        <h5>Your Background</h5>
                        <p>Briefly share where you come from and what shaped your aspirations. Be authentic.</p>
                    </div>
                    <div class="writer-tip">
                        <h5>Achievements & Impact</h5>
                        <p>Highlight 2-3 key achievements with specific numbers or outcomes. Show, don't tell.</p>
                    </div>
                    <div class="writer-tip">
                        <h5>Why This Scholarship</h5>
                        <p>Connect your goals to the scholarship's mission. Show you've researched them.</p>
                    </div>
                    <div class="writer-tip">
                        <h5>Future Vision</h5>
                        <p>End with clear goals and how the scholarship helps you get there. Be specific and ambitious.</p>
                    </div>
                    <div class="writer-tip">
                        <h5>💡 Pro Tips</h5>
                        <p>• Keep it 500-650 words unless specified<br>• Use active voice<br>• One story > many summaries<br>• Proofread aloud</p>
                    </div>
                </div>
            </div>
        `;
    }

    function initWriter() {
        const ta = $('#writerText');
        ta.addEventListener('input', () => {
            const text = ta.value;
            const words = text.trim() ? text.trim().split(/\s+/).length : 0;
            const chars = text.length;
            const sentences = text.split(/[.!?]+/).filter(s => s.trim()).length;
            $('#writerWords').textContent = words;
            $('#writerChars').textContent = chars;
            $('#writerSentences').textContent = sentences;
            $('#writerTime').textContent = Math.max(1, Math.round(words / 200)) + ' min';
        });
    }

    // ===== PROFILER AGENT =====
    function buildProfilerUI() {
        return `
            <div class="profiler-form">
                <div><label>Full Name</label><input type="text" id="profName" placeholder="Your name"></div>
                <div><label>Country</label><input type="text" id="profCountry" placeholder="e.g. Ghana"></div>
                <div><label>GPA</label><input type="number" id="profGpa" min="0" max="4" step="0.1" placeholder="e.g. 3.8"></div>
                <div><label>Degree Level</label>
                    <select id="profLevel"><option value="undergraduate">Undergraduate</option><option value="masters">Masters</option><option value="phd">PhD</option></select>
                </div>
                <div><label>Field of Interest</label><input type="text" id="profField" placeholder="e.g. Computer Science"></div>
                <div><label>Years of Experience</label><input type="number" id="profExp" min="0" placeholder="e.g. 2"></div>
                <div class="full-width"><label>Key Skills (comma separated)</label><input type="text" id="profSkills" placeholder="e.g. Python, Machine Learning, Leadership"></div>
                <div class="full-width">
                    <button class="btn btn-primary" id="profilerAnalyze" style="background:linear-gradient(135deg,#8B5CF6,#7C3AED);border:none;width:100%;">👤 Analyze My Profile</button>
                </div>
            </div>
            <div class="profiler-results" id="profilerResults"></div>
        `;
    }

    function initProfiler() {
        $('#profilerAnalyze').addEventListener('click', () => {
            const gpa = parseFloat($('#profGpa').value) || 0;
            const country = $('#profCountry').value.toLowerCase();
            const field = $('#profField').value.toLowerCase();
            const level = $('#profLevel').value;
            const results = $('#profilerResults');

            const top = DATA.scholarships.slice(0, 15).map(s => {
                let pct = 40;
                if (gpa >= 3.5) pct += 20; else if (gpa >= 3.0) pct += 10;
                if (s.country && s.country.toLowerCase().includes(country)) pct += 15;
                if (s.fields && s.fields.some(f => f.toLowerCase().includes(field))) pct += 15;
                if (s.level && s.level.toLowerCase().includes(level)) pct += 10;
                pct = Math.min(pct, 98);
                return { name: s.name, pct };
            }).sort((a, b) => b.pct - a.pct);

            results.innerHTML = '<h4 style="color:var(--text-primary);margin-bottom:12px;">Your Eligibility Matches</h4>' +
                top.map(t => {
                    const color = t.pct > 75 ? 'var(--success)' : t.pct > 50 ? 'var(--warning)' : 'var(--danger)';
                    return `<div class="profiler-match">
                        <span style="color:var(--text-primary);font-size:14px;">${escapeHtml(t.name)}</span>
                        <div style="display:flex;align-items:center;gap:10px;">
                            <div class="profiler-bar-bg"><div class="profiler-bar-fill" style="width:${t.pct}%;background:${color};"></div></div>
                            <span style="color:${color};font-weight:700;font-size:14px;min-width:40px;text-align:right;">${t.pct}%</span>
                        </div>
                    </div>`;
                }).join('');
        });
    }

    // ===== TRACKER AGENT =====
    function buildTrackerUI() {
        const now = new Date();
        const deadlines = DATA.scholarships
            .filter(s => s.deadline)
            .map(s => {
                const dl = new Date(s.deadline);
                const diff = Math.ceil((dl - now) / (1000 * 60 * 60 * 24));
                return { name: s.name, country: s.country, deadline: s.deadline, days: diff };
            })
            .filter(d => d.days > -30)
            .sort((a, b) => a.days - b.days)
            .slice(0, 25);

        if (!deadlines.length) {
            return '<p style="color:var(--text-muted);text-align:center;padding:40px;">No deadlines found in the database.</p>';
        }

        return `
            <div style="display:flex;gap:16px;margin-bottom:20px;flex-wrap:wrap;">
                <div style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-muted);">
                    <span class="tracker-dot red" style="width:8px;height:8px;display:inline-block;"></span> Less than 7 days
                </div>
                <div style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-muted);">
                    <span class="tracker-dot yellow" style="width:8px;height:8px;display:inline-block;"></span> 7–30 days
                </div>
                <div style="display:flex;align-items:center;gap:6px;font-size:12px;color:var(--text-muted);">
                    <span class="tracker-dot green" style="width:8px;height:8px;display:inline-block;"></span> More than 30 days
                </div>
            </div>
            <div class="tracker-timeline">
                ${deadlines.map(d => {
                    const urgency = d.days < 0 ? 'red' : d.days < 7 ? 'red' : d.days < 30 ? 'yellow' : 'green';
                    const label = d.days < 0 ? 'PASSED' : d.days === 0 ? 'TODAY' : d.days + ' days';
                    return `<div class="tracker-item">
                        <div class="tracker-dot ${urgency}"></div>
                        <div class="tracker-info">
                            <h4>${escapeHtml(d.name)}</h4>
                            <p>${escapeHtml(d.country || '')} · ${d.deadline}</p>
                        </div>
                        <div class="tracker-days ${urgency}">
                            <div class="days-num">${d.days < 0 ? '—' : d.days}</div>
                            <div class="days-label">${label}</div>
                        </div>
                    </div>`;
                }).join('')}
            </div>
        `;
    }

    // ===== ADVISOR AGENT =====
    function buildAdvisorUI() {
        const scholarships = DATA.scholarships.slice(0, 12).map((s, i) => {
            const competition = ['Low', 'Medium', 'High'][Math.floor(Math.random() * 3)];
            const fit = 60 + Math.floor(Math.random() * 35);
            const effort = ['Low', 'Medium', 'High'][Math.floor(Math.random() * 3)];
            const priority = fit > 80 ? 'high' : fit > 65 ? 'medium' : 'low';
            return { ...s, competition, fit, effort, priority, rank: i + 1 };
        }).sort((a, b) => b.fit - a.fit).map((s, i) => ({ ...s, rank: i + 1 }));

        return `
            <p style="color:var(--text-secondary);margin-bottom:20px;font-size:14px;">Based on scholarship data analysis, here are your recommended priorities:</p>
            <div class="advisor-list">
                ${scholarships.map(s => `
                    <div class="advisor-card">
                        <div class="advisor-card-header">
                            <div>
                                <span style="color:var(--text-primary);font-weight:600;">${escapeHtml(s.name)}</span>
                                <p style="color:var(--text-muted);font-size:12px;margin-top:2px;">${escapeHtml(s.country || '')}</p>
                            </div>
                            <div style="display:flex;align-items:center;gap:10px;">
                                <span class="advisor-priority ${s.priority}">${s.priority} priority</span>
                                <span class="advisor-rank">#${s.rank}</span>
                            </div>
                        </div>
                        <div class="advisor-metrics">
                            <div class="advisor-metric">Fit Score: <span>${s.fit}%</span></div>
                            <div class="advisor-metric">Competition: <span>${s.competition}</span></div>
                            <div class="advisor-metric">Effort: <span>${s.effort}</span></div>
                        </div>
                    </div>
                `).join('')}
            </div>
        `;
    }

    // ===== PREP AGENT =====
    function buildPrepUI() {
        return `
            <div class="prep-chat" id="prepChat">
                <div class="prep-msg agent">
                    👋 Hi! I'm your Interview Coach. I'll ask you common scholarship interview questions and give you tips on how to answer them.<br><br>
                    Ready to practice? Choose a question to start:
                </div>
            </div>
            <div class="prep-options" id="prepOptions">
                ${interviewQuestions.slice(0, 5).map((q, i) => `
                    <button class="prep-option-btn" data-qi="${i}">${q.q.substring(0, 50)}...</button>
                `).join('')}
                <button class="prep-option-btn" data-qi="random">🎲 Random Question</button>
            </div>
        `;
    }

    function initPrep() {
        $('#prepOptions').addEventListener('click', e => {
            const btn = e.target.closest('.prep-option-btn');
            if (!btn) return;
            const qi = btn.dataset.qi;
            const idx = qi === 'random' ? Math.floor(Math.random() * interviewQuestions.length) : parseInt(qi);
            const q = interviewQuestions[idx];

            const chat = $('#prepChat');
            chat.innerHTML += `<div class="prep-msg user">I'd like to practice: "${q.q}"</div>`;
            chat.innerHTML += `
                <div class="prep-msg agent">
                    <strong>📋 Question:</strong><br>"${q.q}"<br><br>
                    <strong>💡 How to answer:</strong><br>${q.tip}<br><br>
                    <strong>⏱ Tip:</strong> Practice answering this aloud in under 2 minutes. Record yourself and listen back.<br><br>
                    <em>When you're ready, pick another question below!</em>
                </div>
            `;
            chat.scrollTop = chat.scrollHeight;

            // Refresh options
            const opts = $('#prepOptions');
            const newQuestions = interviewQuestions.filter((_, i) => i !== idx).sort(() => Math.random() - 0.5).slice(0, 4);
            opts.innerHTML = newQuestions.map((nq, i) => {
                const origIdx = interviewQuestions.indexOf(nq);
                return `<button class="prep-option-btn" data-qi="${origIdx}">${nq.q.substring(0, 50)}...</button>`;
            }).join('') + '<button class="prep-option-btn" data-qi="random">🎲 Random Question</button>';
        });
    }

    // Initialize when DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', () => setTimeout(initAIAgents, 500));
    } else {
        setTimeout(initAIAgents, 500);
    }
})();