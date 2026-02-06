/**
 * Weekly Dispatch GUI — Frontend Application
 *
 * Handles all API calls, state management, panel switching,
 * and rendering for the newsletter builder wizard.
 */

const App = {
    // ── State ──────────────────────────────────────────────
    currentStep: 'region',
    selectedArticleIndices: new Set(),
    selectedMoreArticleIndices: new Set(),
    selectedNewsIndices: new Set(),
    selectedWorldIndices: new Set(),
    selectedPodcastIndex: -1,
    customNewsUrls: [],

    // ── API helpers ────────────────────────────────────────

    async api(method, path, body = null) {
        const opts = {
            method,
            headers: { 'Content-Type': 'application/json' },
        };
        if (body) opts.body = JSON.stringify(body);

        const res = await fetch(path, opts);
        const data = await res.json();
        if (!res.ok) {
            const msg = data.detail || data.error || 'API error';
            console.error(`API ${method} ${path}:`, msg);
            this.showToast(`Error: ${msg}`, 'error', 4000);
            throw new Error(msg);
        }
        return data;
    },

    // ── Navigation ─────────────────────────────────────────

    showStep(step) {
        // Update sidebar
        document.querySelectorAll('.step-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.step === step);
        });
        // Update panels
        document.querySelectorAll('.panel').forEach(p => p.classList.add('hidden'));
        const panel = document.getElementById(`panel-${step}`);
        if (panel) panel.classList.remove('hidden');

        this.currentStep = step;
    },

    nextStep() {
        const order = ['region','articles','subject','intro','news','chart','more-articles','banner','podcast','world','assemble'];
        const idx = order.indexOf(this.currentStep);
        if (idx < order.length - 1) {
            this.showStep(order[idx + 1]);
        }
    },

    updateProgress(progress) {
        if (!progress) return;
        // Update step status indicators
        (progress.completed || []).forEach(step => {
            const el = document.getElementById(`status-${step}`);
            if (el) el.classList.add('done');
        });
        // Update region badge
        if (progress.region_name) {
            document.getElementById('regionBadge').textContent = progress.region_name + ' Edition';
        }
    },

    // ── Preview ────────────────────────────────────────────

    _previewTimer: null,

    refreshPreview() {
        // Debounce preview refreshes to avoid blocking UI
        clearTimeout(this._previewTimer);
        this._previewTimer = setTimeout(() => this._doRefreshPreview(), 500);
    },

    async _doRefreshPreview() {
        try {
            const data = await this.api('GET', '/api/preview');
            const frame = document.getElementById('previewFrame');
            frame.srcdoc = data.html || '<p style="color:#999; padding:40px;">No content yet</p>';
        } catch (e) {
            // Preview may fail if not enough content yet — that's OK
        }
    },

    // ── Helpers ────────────────────────────────────────────

    setLoading(id, visible) {
        const el = document.getElementById(id);
        if (el) el.classList.toggle('hidden', !visible);
    },

    setVisible(id, visible) {
        const el = document.getElementById(id);
        if (el) el.classList.toggle('hidden', !visible);
    },

    // ── Toast notifications ──────────────────────────────

    showToast(message, type = 'success', duration = 2500) {
        const container = document.getElementById('toastContainer');
        if (!container) return;
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);
        setTimeout(() => {
            toast.classList.add('fade-out');
            toast.addEventListener('animationend', () => toast.remove());
        }, duration);
    },

    // ═══════════════════════════════════════════════════════
    //  STEP 0: REGION
    // ═══════════════════════════════════════════════════════

    async selectRegion(region) {
        // Visual selection
        document.querySelectorAll('.region-card').forEach(c => {
            c.classList.toggle('selected', c.dataset.region === region);
        });

        await this.api('POST', '/api/step/region', { region });

        document.getElementById('regionBadge').textContent =
            { us: 'US', europe: 'Europe & GB', australia: 'Australia' }[region] + ' Edition';

        document.getElementById('status-region').classList.add('done');
        this.refreshPreview();
        this.nextStep();
    },

    // ═══════════════════════════════════════════════════════
    //  STEP 1: FEATURED ARTICLES
    // ═══════════════════════════════════════════════════════

    async fetchArticles() {
        this.setLoading('articlesLoading', true);
        this.selectedArticleIndices.clear();
        document.getElementById('articleList').innerHTML = '';
        this.setVisible('confirmArticles', false);

        const days = parseInt(document.getElementById('articleDays').value, 10) || 7;

        try {
            const data = await this.api('GET', `/api/step/articles/fetch?days=${days}`);
            this.renderArticleCards(data.articles);
        } finally {
            this.setLoading('articlesLoading', false);
        }
    },

    formatDate(isoDate) {
        if (!isoDate) return '';
        try {
            const d = new Date(isoDate);
            return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
        } catch { return isoDate; }
    },

    renderArticleCards(articles) {
        const container = document.getElementById('articleList');
        container.innerHTML = articles.map(a => `
            <div class="card" data-index="${a.index}" onclick="App.toggleArticle(${a.index})">
                <div class="card-check"></div>
                ${a.thumbnail_url ? `<img class="card-thumb" src="${a.thumbnail_url}" alt="" />` : ''}
                <div class="card-body">
                    <strong>${this.esc(a.title)}</strong>
                    <span class="card-meta">${this.formatDate(a.date)}</span>
                    <p>${this.esc(a.description || '')}</p>
                </div>
            </div>
        `).join('');
        this.setVisible('confirmArticles', true);
    },

    toggleArticle(index) {
        const layout = parseInt(document.getElementById('articleLayout').value, 10);
        if (this.selectedArticleIndices.has(index)) {
            this.selectedArticleIndices.delete(index);
        } else {
            if (this.selectedArticleIndices.size >= layout) {
                // Deselect oldest to enforce limit
                const first = this.selectedArticleIndices.values().next().value;
                this.selectedArticleIndices.delete(first);
                const oldCard = document.querySelector(`.card[data-index="${first}"]`);
                if (oldCard) oldCard.classList.remove('selected');
            }
            this.selectedArticleIndices.add(index);
        }
        // Update visual
        const card = document.querySelector(`.card[data-index="${index}"]`);
        if (card) card.classList.toggle('selected', this.selectedArticleIndices.has(index));
        // Update hint
        const hint = document.getElementById('articleSelectionHint');
        if (hint) hint.textContent = `${this.selectedArticleIndices.size} of ${layout} selected`;
    },

    async confirmArticles() {
        const indices = [...this.selectedArticleIndices];
        const numLayout = parseInt(document.getElementById('articleLayout').value, 10);
        if (indices.length === 0) { this.showToast('Select at least one article.', 'error'); return; }

        await this.api('POST', '/api/step/articles/select', { indices, num_layout: numLayout });
        document.getElementById('status-featured_articles').classList.add('done');
        this.showToast(`${indices.length} article${indices.length > 1 ? 's' : ''} confirmed`);
        this.refreshPreview();
        this.nextStep();
    },

    // ═══════════════════════════════════════════════════════
    //  STEP 2: SUBJECT LINE
    // ═══════════════════════════════════════════════════════

    async generateSubjects() {
        this.setLoading('subjectLoading', true);
        document.getElementById('subjectList').innerHTML = '';

        try {
            const data = await this.api('GET', '/api/step/subject/generate');
            this.renderSubjectOptions(data.suggestions);
        } finally {
            this.setLoading('subjectLoading', false);
        }
    },

    renderSubjectOptions(suggestions) {
        const container = document.getElementById('subjectList');
        // suggestions may be a list of strings or a list of objects
        const items = suggestions.map(s => typeof s === 'string' ? s : s.subject || s.text || String(s));
        container.innerHTML = items.map((s, i) => `
            <div class="option" onclick="App.pickSubject(this, ${JSON.stringify(s).replace(/"/g, '&quot;')})">
                <span class="option-num">${i + 1}</span>
                <span>${this.esc(s)}</span>
            </div>
        `).join('');
    },

    pickSubject(el, text) {
        document.querySelectorAll('#subjectList .option').forEach(o => o.classList.remove('selected'));
        el.classList.add('selected');
        document.getElementById('subjectInput').value = text;
    },

    async confirmSubject() {
        const subject = document.getElementById('subjectInput').value.trim();
        if (!subject) { this.showToast('Enter or select a subject line.', 'error'); return; }

        await this.api('POST', '/api/step/subject/select', { subject });
        document.getElementById('status-subject_line').classList.add('done');
        this.showToast('Subject line confirmed');
        this.refreshPreview();
        this.nextStep();
    },

    // ═══════════════════════════════════════════════════════
    //  STEP 3: INTRO TEXT
    // ═══════════════════════════════════════════════════════

    async generateIntro() {
        this.setLoading('introLoading', true);
        document.getElementById('introPreview').innerHTML = '';

        try {
            const data = await this.api('GET', '/api/step/intro/generate');
            const text = data.intro_text || '';
            document.getElementById('introPreview').innerHTML = text;
            document.getElementById('introInput').value = text;
        } finally {
            this.setLoading('introLoading', false);
        }
    },

    async confirmIntro() {
        const text = document.getElementById('introInput').value.trim();
        if (!text) { this.showToast('Generate or enter intro text.', 'error'); return; }

        await this.api('POST', '/api/step/intro/select', { intro_text: text });
        document.getElementById('status-intro_text').classList.add('done');
        this.showToast('Intro text confirmed');
        this.refreshPreview();
        this.nextStep();
    },

    // ═══════════════════════════════════════════════════════
    //  STEP 4: NEWS SECTION
    // ═══════════════════════════════════════════════════════

    async fetchNews() {
        this.setLoading('newsLoading', true);
        this.selectedNewsIndices.clear();
        this.customNewsUrls = [];
        document.getElementById('newsList').innerHTML = '';
        document.getElementById('customNewsList').innerHTML = '';
        this.setVisible('confirmNews', false);

        try {
            const data = await this.api('GET', '/api/step/news/fetch');
            this.renderNewsCards(data.news);
        } finally {
            this.setLoading('newsLoading', false);
        }
    },

    renderNewsCards(news) {
        const container = document.getElementById('newsList');
        container.innerHTML = news.map(n => `
            <div class="card" data-index="${n.index}" onclick="App.toggleNews(${n.index})">
                <div class="card-check"></div>
                <div class="card-body">
                    <strong>${this.esc(n.title)}</strong>
                    <span class="card-meta">${this.esc(n.source)} — ${this.esc(n.date)}</span>
                    <p>${this.esc(n.description || '')}</p>
                </div>
            </div>
        `).join('');
        this.setVisible('confirmNews', true);
    },

    toggleNews(index) {
        if (this.selectedNewsIndices.has(index)) {
            this.selectedNewsIndices.delete(index);
        } else {
            if (this.selectedNewsIndices.size >= 4) {
                this.showToast('Max 4 news items. Deselect one first.', 'error');
                return;
            }
            this.selectedNewsIndices.add(index);
        }
        const card = document.querySelector(`#newsList .card[data-index="${index}"]`);
        if (card) card.classList.toggle('selected', this.selectedNewsIndices.has(index));
        // Update selection hint
        const hint = document.getElementById('newsSelectionHint');
        if (hint) hint.textContent = `${this.selectedNewsIndices.size} of 4 selected`;
    },

    addCustomNewsUrl() {
        const input = document.getElementById('customNewsUrl');
        const url = input.value.trim();
        if (!url) return;

        this.customNewsUrls.push(url);
        input.value = '';
        this.renderCustomNewsTags();
    },

    removeCustomUrl(index) {
        this.customNewsUrls.splice(index, 1);
        this.renderCustomNewsTags();
    },

    renderCustomNewsTags() {
        const container = document.getElementById('customNewsList');
        container.innerHTML = this.customNewsUrls.map((url, i) => `
            <div class="custom-url-tag">
                <span class="url-text">${this.esc(url)}</span>
                <button class="url-remove" onclick="App.removeCustomUrl(${i})" title="Remove">&times;</button>
            </div>
        `).join('');
    },

    async confirmNews() {
        const indices = [...this.selectedNewsIndices];
        if (indices.length === 0 && this.customNewsUrls.length === 0) {
            this.showToast('Select at least one news item or add a custom URL.', 'error');
            return;
        }

        await this.api('POST', '/api/step/news/select', {
            indices,
            custom_urls: this.customNewsUrls,
        });
        document.getElementById('status-news_section').classList.add('done');
        this.showToast('News section confirmed');
        this.refreshPreview();
        this.nextStep();
    },

    // ═══════════════════════════════════════════════════════
    //  STEP 5: CHART OF THE WEEK
    // ═══════════════════════════════════════════════════════

    populateChartSourceDropdown() {
        // Called when navigating to chart step — fill dropdown from state
        const select = document.getElementById('chartSourceArticle');
        if (!select) return;
        // Fetch current state to get featured articles
        this.api('GET', '/api/state').then(data => {
            const articles = (data.content && data.content.featured_articles) || [];
            select.innerHTML = articles.map((a, i) =>
                `<option value="${i}">${this.esc(a.title || `Article ${i + 1}`)}</option>`
            ).join('');
        }).catch(() => {});
    },

    async uploadChartImage(input) {
        const file = input.files && input.files[0];
        if (!file) return;

        const statusEl = document.getElementById('chartUploadStatus');
        statusEl.textContent = 'Uploading...';
        statusEl.classList.remove('hidden');

        const formData = new FormData();
        formData.append('file', file);

        try {
            const res = await fetch('/api/upload', { method: 'POST', body: formData });
            const data = await res.json();
            if (!res.ok) throw new Error(data.detail || 'Upload failed');

            // Convert relative URL to absolute for the HTML template
            const absUrl = window.location.origin + data.url;
            document.getElementById('chartImage').value = absUrl;

            // Show preview
            const preview = document.getElementById('chartImagePreview');
            const thumb = document.getElementById('chartImageThumb');
            thumb.src = data.url;
            preview.classList.remove('hidden');

            statusEl.textContent = `Uploaded: ${data.filename}`;
            this.showToast('Chart image uploaded');
        } catch (e) {
            statusEl.textContent = `Upload failed: ${e.message}`;
            this.showToast('Image upload failed: ' + e.message, 'error');
        }
    },

    async generateChartText() {
        const sourceIdx = parseInt(document.getElementById('chartSourceArticle').value, 10) || 0;
        const imageUrl = document.getElementById('chartImage').value.trim();
        if (!imageUrl) { this.showToast('Enter a chart image URL or upload a file.', 'error'); return; }

        this.setLoading('chartLoading', true);
        try {
            const data = await this.api('POST', '/api/step/chart/generate-text', {
                source_article_index: sourceIdx,
                image_url: imageUrl,
                skip: false,
            });
            document.getElementById('chartIntro').value = data.intro || '';
            document.getElementById('chartOutro').value = data.outro || '';
        } finally {
            this.setLoading('chartLoading', false);
        }
    },

    async confirmChart() {
        const sourceIdx = parseInt(document.getElementById('chartSourceArticle').value, 10) || 0;
        const imageUrl = document.getElementById('chartImage').value.trim();
        const introText = document.getElementById('chartIntro').value.trim();
        const outroText = document.getElementById('chartOutro').value.trim();

        if (!imageUrl) { this.showToast('Enter a chart image URL.', 'error'); return; }

        await this.api('POST', '/api/step/chart/select', {
            source_article_index: sourceIdx,
            image_url: imageUrl,
            intro_text: introText,
            outro_text: outroText,
            skip: false,
        });
        document.getElementById('status-chart').classList.add('done');
        this.showToast('Chart confirmed');
        this.refreshPreview();
        this.nextStep();
    },

    async skipChart() {
        await this.api('POST', '/api/step/chart/select', {
            source_article_index: 0,
            image_url: '',
            skip: true,
        });
        document.getElementById('status-chart').classList.add('done');
        this.nextStep();
    },

    // ═══════════════════════════════════════════════════════
    //  STEP 5b: MORE ARTICLES
    // ═══════════════════════════════════════════════════════

    async fetchMoreArticles() {
        this.setLoading('moreArticlesLoading', true);
        this.selectedMoreArticleIndices.clear();
        document.getElementById('moreArticlesList').innerHTML = '';
        this.setVisible('confirmMoreArticles', false);

        const days = parseInt(document.getElementById('moreArticlesDays').value, 10) || 14;

        try {
            const data = await this.api('GET', `/api/step/more-articles/fetch?days=${days}`);
            this.renderMoreArticleCards(data.articles);
        } finally {
            this.setLoading('moreArticlesLoading', false);
        }
    },

    renderMoreArticleCards(articles) {
        const container = document.getElementById('moreArticlesList');
        container.innerHTML = articles.map(a => `
            <div class="card" data-index="${a.index}" onclick="App.toggleMoreArticle(${a.index})">
                <div class="card-check"></div>
                ${a.thumbnail_url ? `<img class="card-thumb" src="${a.thumbnail_url}" alt="" />` : ''}
                <div class="card-body">
                    <strong>${this.esc(a.title)}</strong>
                    <span class="card-meta">${this.formatDate(a.date)}</span>
                    <p>${this.esc(a.description || '')}</p>
                </div>
            </div>
        `).join('');
        this.setVisible('confirmMoreArticles', true);
    },

    toggleMoreArticle(index) {
        if (this.selectedMoreArticleIndices.has(index)) {
            this.selectedMoreArticleIndices.delete(index);
        } else {
            if (this.selectedMoreArticleIndices.size >= 10) {
                this.showToast('Max 10 articles. Deselect one first.', 'error');
                return;
            }
            this.selectedMoreArticleIndices.add(index);
        }
        const card = document.querySelector(`#moreArticlesList .card[data-index="${index}"]`);
        if (card) card.classList.toggle('selected', this.selectedMoreArticleIndices.has(index));
        // Update hint
        const hint = document.getElementById('moreArticlesSelectionHint');
        if (hint) hint.textContent = `${this.selectedMoreArticleIndices.size} of 10 selected`;
    },

    async confirmMoreArticles() {
        const indices = [...this.selectedMoreArticleIndices];
        if (indices.length === 0) { this.showToast('Select at least one article, or click Skip.', 'error'); return; }

        await this.api('POST', '/api/step/more-articles/select', { indices, skip: false });
        document.getElementById('status-more_articles').classList.add('done');
        this.showToast(`${indices.length} more article${indices.length > 1 ? 's' : ''} confirmed`);
        this.refreshPreview();
        this.nextStep();
    },

    async skipMoreArticles() {
        await this.api('POST', '/api/step/more-articles/select', { indices: [], skip: true });
        document.getElementById('status-more_articles').classList.add('done');
        this.nextStep();
    },

    // ═══════════════════════════════════════════════════════
    //  STEP 6: PROMOTIONAL BANNER
    // ═══════════════════════════════════════════════════════

    async confirmBanner() {
        const imageUrl = document.getElementById('bannerImage').value.trim();
        const link = document.getElementById('bannerLink').value.trim();
        const altText = document.getElementById('bannerAlt').value.trim();

        if (!imageUrl) { this.showToast('Enter a banner image URL, or click Skip.', 'error'); return; }

        await this.api('POST', '/api/step/banner/select', {
            image_url: imageUrl,
            link,
            alt_text: altText,
            skip: false,
        });
        document.getElementById('status-banner').classList.add('done');
        this.showToast('Banner confirmed');
        this.refreshPreview();
        this.nextStep();
    },

    async skipBanner() {
        await this.api('POST', '/api/step/banner/select', { skip: true });
        document.getElementById('status-banner').classList.add('done');
        this.nextStep();
    },

    // ═══════════════════════════════════════════════════════
    //  STEP 7: PODCAST
    // ═══════════════════════════════════════════════════════

    async fetchPodcasts() {
        this.setLoading('podcastLoading', true);
        this.selectedPodcastIndex = -1;
        document.getElementById('podcastList').innerHTML = '';
        this.setVisible('podcastDetails', false);

        try {
            const data = await this.api('GET', '/api/step/podcast/fetch');
            this.renderPodcastCards(data.episodes);
        } finally {
            this.setLoading('podcastLoading', false);
        }
    },

    renderPodcastCards(episodes) {
        const container = document.getElementById('podcastList');
        container.innerHTML = episodes.map(ep => `
            <div class="card" data-index="${ep.index}" onclick="App.selectPodcast(${ep.index}, ${JSON.stringify(ep).replace(/"/g, '&quot;')})">
                <div class="card-check"></div>
                ${ep.thumbnail ? `<img class="card-thumb" src="${ep.thumbnail}" alt="" />` : ''}
                <div class="card-body">
                    <strong>${this.esc(ep.title)}</strong>
                    ${ep.guest_name ? `<span class="card-meta">Guest: ${this.esc(ep.guest_name)}${ep.company ? ` — ${this.esc(ep.company)}` : ''}</span>` : ''}
                </div>
            </div>
        `).join('');
    },

    selectPodcast(index, episode) {
        // Deselect previous
        document.querySelectorAll('#podcastList .card').forEach(c => c.classList.remove('selected'));
        // Select new
        const card = document.querySelector(`#podcastList .card[data-index="${index}"]`);
        if (card) card.classList.add('selected');

        this.selectedPodcastIndex = index;

        // Pre-fill guest details from parsed title
        document.getElementById('podcastGuest').value = episode.guest_name || '';
        document.getElementById('podcastRole').value = episode.guest_role || '';
        document.getElementById('podcastCompany').value = episode.company || '';

        this.setVisible('podcastDetails', true);
    },

    async confirmPodcast() {
        if (this.selectedPodcastIndex < 0) { this.showToast('Select a podcast episode.', 'error'); return; }

        const body = {
            episode_index: this.selectedPodcastIndex,
            moderator: document.getElementById('podcastModerator').value.trim() || 'Ed',
            guest_name: document.getElementById('podcastGuest').value.trim(),
            guest_role: document.getElementById('podcastRole').value.trim(),
            company: document.getElementById('podcastCompany').value.trim(),
            guest_linkedin: document.getElementById('podcastGuestLinkedin').value.trim(),
            company_linkedin: document.getElementById('podcastCompanyLinkedin').value.trim(),
        };

        await this.api('POST', '/api/step/podcast/select', body);
        document.getElementById('status-podcast').classList.add('done');
        this.showToast('Podcast confirmed');
        this.refreshPreview();
        this.nextStep();
    },

    // ═══════════════════════════════════════════════════════
    //  STEP 8: WORLD ARTICLES
    // ═══════════════════════════════════════════════════════

    async fetchWorldArticles() {
        this.setLoading('worldLoading', true);
        this.selectedWorldIndices.clear();
        document.getElementById('worldList').innerHTML = '';
        this.setVisible('confirmWorld', false);

        const days = parseInt(document.getElementById('worldDays').value, 10) || 14;

        try {
            const data = await this.api('GET', `/api/step/world/fetch?days=${days}`);
            this.renderWorldCards(data.articles);
        } finally {
            this.setLoading('worldLoading', false);
        }
    },

    renderWorldCards(articles) {
        const container = document.getElementById('worldList');
        container.innerHTML = articles.map(a => `
            <div class="card" data-index="${a.index}" onclick="App.toggleWorld(${a.index})">
                <div class="card-check"></div>
                ${a.thumbnail_url ? `<img class="card-thumb" src="${a.thumbnail_url}" alt="" />` : ''}
                <div class="card-body">
                    <strong>${this.esc(a.title)}</strong>
                    <span class="card-meta">${this.esc(a.detected_region || '')}</span>
                </div>
            </div>
        `).join('');
        this.setVisible('confirmWorld', true);
    },

    toggleWorld(index) {
        if (this.selectedWorldIndices.has(index)) {
            this.selectedWorldIndices.delete(index);
        } else {
            if (this.selectedWorldIndices.size >= 3) {
                this.showToast('Max 3 world articles. Deselect one first.', 'error');
                return;
            }
            this.selectedWorldIndices.add(index);
        }
        const card = document.querySelector(`#worldList .card[data-index="${index}"]`);
        if (card) card.classList.toggle('selected', this.selectedWorldIndices.has(index));
        // Update selection hint
        const hint = document.getElementById('worldSelectionHint');
        if (hint) hint.textContent = `${this.selectedWorldIndices.size} of 3 selected`;
    },

    async confirmWorld() {
        const indices = [...this.selectedWorldIndices];
        if (indices.length === 0) { this.showToast('Select at least one world article.', 'error'); return; }

        await this.api('POST', '/api/step/world/select', { indices });
        document.getElementById('status-world_articles').classList.add('done');
        this.showToast(`${indices.length} world article${indices.length > 1 ? 's' : ''} confirmed`);
        this.refreshPreview();
        this.nextStep();
    },

    // ═══════════════════════════════════════════════════════
    //  STEP 9: ASSEMBLE & PUBLISH
    // ═══════════════════════════════════════════════════════

    async assembleNewsletter() {
        this.setLoading('assembleLoading', true);
        const resultBox = document.getElementById('assembleResult');
        resultBox.classList.add('hidden');

        try {
            const data = await this.api('POST', '/api/assemble');
            resultBox.innerHTML = `
                <strong>Newsletter assembled.</strong><br>
                Subject: ${this.esc(data.subject || '')}<br>
                Preview text: ${this.esc(data.preview_text || '')}<br>
                HTML size: ${data.html_length || 0} chars<br>
                Saved to: <code>${this.esc(data.output_file || '')}</code>
            `;
            resultBox.classList.remove('hidden');
            document.getElementById('status-assemble').classList.add('done');
            this.refreshPreview();
        } finally {
            this.setLoading('assembleLoading', false);
        }
    },

    downloadNewsletter() {
        // Trigger HTML download via the download endpoint
        const link = document.createElement('a');
        link.href = '/api/download';
        link.download = '';  // browser will use Content-Disposition filename
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        this.showToast('Downloading newsletter HTML...');
    },

    async publishHubspot() {
        if (!confirm('Publish this newsletter as a draft to HubSpot?')) return;

        this.setLoading('assembleLoading', true);
        const resultBox = document.getElementById('assembleResult');

        try {
            const data = await this.api('POST', '/api/publish/hubspot', { upload_images: true });
            resultBox.innerHTML = `
                <strong>Published to HubSpot.</strong><br>
                Email ID: ${this.esc(data.email_id || '')}<br>
                ${this.esc(data.message || '')}
            `;
            resultBox.classList.remove('hidden');
            this.showToast('Draft created in HubSpot');
        } catch (e) {
            // Error already shown by api() — add helpful hint
            resultBox.innerHTML = `
                <strong style="color:#c00;">HubSpot publish failed.</strong><br>
                ${this.esc(e.message)}<br><br>
                <strong>Tip:</strong> Use the <em>Download HTML</em> button instead, then manually upload to HubSpot.
            `;
            resultBox.classList.remove('hidden');
        } finally {
            this.setLoading('assembleLoading', false);
        }
    },

    // ═══════════════════════════════════════════════════════
    //  UTILITIES
    // ═══════════════════════════════════════════════════════

    async saveCheckpoint() {
        try {
            const data = await this.api('POST', '/api/checkpoint/save');
            this.showToast('Progress saved');
        } catch (e) { /* already alerted by api() */ }
    },

    async reset() {
        if (!confirm('Reset all progress? This cannot be undone.')) return;
        await this.api('POST', '/api/reset');
        // Clear local state
        this.selectedArticleIndices.clear();
        this.selectedMoreArticleIndices.clear();
        this.selectedNewsIndices.clear();
        this.selectedWorldIndices.clear();
        this.selectedPodcastIndex = -1;
        this.customNewsUrls = [];
        // Reset UI
        document.querySelectorAll('.step-status').forEach(el => el.classList.remove('done'));
        document.getElementById('regionBadge').textContent = 'No region selected';
        document.querySelectorAll('.card-list').forEach(el => { el.innerHTML = ''; });
        document.getElementById('previewFrame').srcdoc =
            '<p style="color:#999; padding:40px; font-family:sans-serif;">Complete steps to see preview...</p>';
        this.showStep('region');
    },

    /** HTML-escape a string for safe DOM insertion. */
    esc(str) {
        const el = document.createElement('span');
        el.textContent = str || '';
        return el.innerHTML;
    },

    // ═══════════════════════════════════════════════════════
    //  INITIALIZATION
    // ═══════════════════════════════════════════════════════

    // ═══════════════════════════════════════════════════════
    //  RESIZABLE PREVIEW PANEL
    // ═══════════════════════════════════════════════════════

    initResize() {
        const handle = document.getElementById('resizeHandle');
        const panel = document.getElementById('previewPanel');
        if (!handle || !panel) return;

        let startX, startWidth;

        const onMouseMove = (e) => {
            // Preview is on the right, so dragging left = wider, right = narrower
            const delta = startX - e.clientX;
            const newWidth = Math.min(Math.max(startWidth + delta, 200), window.innerWidth * 0.7);
            panel.style.width = newWidth + 'px';
        };

        const onMouseUp = () => {
            handle.classList.remove('dragging');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';
            document.removeEventListener('mousemove', onMouseMove);
            document.removeEventListener('mouseup', onMouseUp);
        };

        handle.addEventListener('mousedown', (e) => {
            e.preventDefault();
            startX = e.clientX;
            startWidth = panel.offsetWidth;
            handle.classList.add('dragging');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';
            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });
    },

    async init() {
        // Wire sidebar buttons
        document.querySelectorAll('.step-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const step = btn.dataset.step;
                this.showStep(step);
                // Populate chart dropdown when entering chart step
                if (step === 'chart') this.populateChartSourceDropdown();
            });
        });

        // Wire resizable preview panel
        this.initResize();

        // Try to load existing checkpoint / state
        try {
            const data = await this.api('GET', '/api/state');
            if (data.progress) {
                this.updateProgress(data.progress);
                // Navigate to the first incomplete step
                const stepMap = {
                    region: 'region',
                    featured_articles: 'articles',
                    subject_line: 'subject',
                    intro_text: 'intro',
                    news_section: 'news',
                    chart: 'chart',
                    more_articles: 'more-articles',
                    banner: 'banner',
                    podcast: 'podcast',
                    world_articles: 'world',
                    assemble: 'assemble',
                };
                const nextIncomplete = stepMap[data.progress.current_step] || 'region';
                this.showStep(nextIncomplete);
            }
        } catch (e) {
            // Fresh session — stay on region
        }
    },
};

// Boot
document.addEventListener('DOMContentLoaded', () => App.init());
