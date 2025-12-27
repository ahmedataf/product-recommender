document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('query-form');
    const input = document.getElementById('query-input');
    const messages = document.getElementById('messages');
    const submitBtn = document.getElementById('submit-btn');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoading = submitBtn.querySelector('.btn-loading');
    // Handle example query clicks
    document.querySelectorAll('.example').forEach(el => {
        el.addEventListener('click', () => {
            input.value = el.textContent.replace(/"/g, '');
            form.dispatchEvent(new Event('submit'));
        });
    });

    form.addEventListener('submit', async (e) => {
        e.preventDefault();

        const query = input.value.trim();
        if (!query) return;

        // Add user message
        addMessage(query, 'user');
        input.value = '';

        // Show loading state
        setLoading(true);
        const loadingMessage = addLoadingMessage();

        try {
            const response = await fetch('/api/recommend', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ query }),
            });

            if (!response.ok) {
                throw new Error('Failed to get recommendations');
            }

            const data = await response.json();

            // Remove loading message
            loadingMessage.remove();

            // Add assistant response
            addRecommendationMessage(data);

        } catch (error) {
            console.error('Error:', error);
            loadingMessage.remove();
            addMessage('Sorry, something went wrong. Please try again.', 'assistant');
        } finally {
            setLoading(false);
        }
    });

    function addMessage(content, type) {
        const div = document.createElement('div');
        div.className = `message ${type}`;
        div.innerHTML = `
            <div class="message-content">
                <p>${escapeHtml(content)}</p>
            </div>
        `;
        messages.appendChild(div);
        scrollToBottom();
        return div;
    }

    function addLoadingMessage() {
        const div = document.createElement('div');
        div.className = 'message assistant';
        div.innerHTML = `
            <div class="message-content loading">
                <span>Finding the best products for you</span>
                <div class="loading-dots">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        messages.appendChild(div);
        scrollToBottom();
        return div;
    }

    function addRecommendationMessage(data) {
        const div = document.createElement('div');
        div.className = 'message assistant';

        // Build parsed query info
        let parsedInfoHtml = '';
        const pq = data.parsed_query;
        if (pq) {
            const tags = [];
            if (pq.category) tags.push(`Category: ${pq.category.replace('_', ' ')}`);
            if (pq.use_case) tags.push(`Use: ${pq.use_case}`);
            if (pq.size_preference) tags.push(`Size: ${pq.size_preference}`);
            if (pq.capacity) tags.push(`Capacity: ${pq.capacity}`);
            if (pq.family_size) tags.push(`Family: ${pq.family_size} people`);
            if (pq.room_size) tags.push(`Room: ${pq.room_size}`);
            if (pq.must_have_features && pq.must_have_features.length > 0) {
                tags.push(...pq.must_have_features.map(f => f));
            }

            if (tags.length > 0) {
                parsedInfoHtml = `
                    <div class="parsed-info">
                        <strong>Understood:</strong>
                        <div class="parsed-tags">
                            ${tags.map(t => `<span class="parsed-tag">${escapeHtml(t)}</span>`).join('')}
                        </div>
                    </div>
                `;
            }
        }

        // Build recommendations
        let recommendationsHtml = '';
        if (data.recommendations && data.recommendations.length > 0) {
            recommendationsHtml = `
                <div class="products-grid">
                    ${data.recommendations.map(rec => createProductCard(rec)).join('')}
                </div>
            `;
        } else {
            recommendationsHtml = '<p>No products found matching your criteria. Try adjusting your requirements.</p>';
        }

        div.innerHTML = `
            <div class="message-content">
                <div class="summary-message">${escapeHtml(data.message)}</div>
                ${parsedInfoHtml}
                ${recommendationsHtml}
            </div>
        `;

        messages.appendChild(div);
        scrollToBottom();
    }

    function createProductCard(rec) {
        const product = rec.product;

        // Sizes
        let sizesHtml = '';
        if (product.sizes && product.sizes.length > 0) {
            sizesHtml = `
                <div class="product-sizes">
                    ${product.sizes.map(s => `<span class="size-tag">${escapeHtml(s)}</span>`).join('')}
                </div>
            `;
        }

        // Features (collapsible)
        let featuresHtml = '';
        if (product.features && product.features.length > 0) {
            const displayFeatures = product.features.slice(0, 5);
            featuresHtml = `
                <details class="product-features">
                    <summary>Key Features (${product.features.length})</summary>
                    <ul class="features-list">
                        ${displayFeatures.map(f => `<li>${escapeHtml(f)}</li>`).join('')}
                    </ul>
                </details>
            `;
        }

        // Product link
        let linkHtml = '';
        if (product.url) {
            linkHtml = `<a href="${product.url}" target="_blank" class="product-link">View on Hisense</a>`;
        }

        return `
            <div class="product-card">
                <div class="product-header">
                    <span class="product-name">${escapeHtml(product.name)}</span>
                    <span class="product-score">${Math.round(rec.score)}% match</span>
                </div>
                <span class="product-category">${product.category.replace('_', ' ')}</span>
                ${sizesHtml}
                <div class="product-reasoning">${escapeHtml(rec.reasoning)}</div>
                ${featuresHtml}
                ${linkHtml}
            </div>
        `;
    }

    function setLoading(isLoading) {
        submitBtn.disabled = isLoading;
        btnText.style.display = isLoading ? 'none' : 'inline';
        btnLoading.style.display = isLoading ? 'inline' : 'none';
    }

    function scrollToBottom() {
        messages.scrollTop = messages.scrollHeight;
    }

    function escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
});
