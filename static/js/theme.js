const themeToggle = document.getElementById('themeToggle');
const html = document.documentElement;
const themeIcon = themeToggle.querySelector('.theme-icon');

const savedTheme = localStorage.getItem('theme') || 'light';
html.setAttribute('data-theme', savedTheme);
updateThemeIcon(savedTheme);

themeToggle.addEventListener('click', () => {
    const currentTheme = html.getAttribute('data-theme');
    const newTheme = currentTheme === 'light' ? 'dark' : 'light';

    html.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    updateThemeIcon(newTheme);
});

function updateThemeIcon(theme) {
    if (theme === 'dark') {
        themeIcon.textContent = 'Light';
        themeToggle.setAttribute('title', 'Switch to light mode');
    } else {
        themeIcon.textContent = 'Dark';
        themeToggle.setAttribute('title', 'Switch to dark mode');
    }
}

const pageStartedAt = Date.now();

window.addEventListener('load', () => {
    const elapsed = Date.now() - pageStartedAt;
    const remaining = Math.max(0, 450 - elapsed);

    setTimeout(() => {
        document.body.classList.add('page-ready');
    }, remaining);
});

document.querySelectorAll('a[href]').forEach((link) => {
    const href = link.getAttribute('href');
    const target = link.getAttribute('target');

    if (!href || href.startsWith('#') || href.startsWith('mailto:') || href.startsWith('tel:') || target === '_blank') {
        return;
    }

    link.addEventListener('click', () => {
        document.body.classList.add('page-exit');
    });
});

const sweetOverlay = document.getElementById('sweetOverlay');
const sweetTitle = document.getElementById('sweetTitle');
const sweetMessage = document.getElementById('sweetMessage');
const sweetIcon = document.getElementById('sweetIcon');
const sweetConfirm = document.getElementById('sweetConfirm');
const sweetCancel = document.getElementById('sweetCancel');

function clearFlashMessages() {
    const flashMessages = document.getElementById('flashMessages');

    if (flashMessages) {
        flashMessages.remove();
    }

    if (sweetOverlay) {
        sweetOverlay.classList.remove('is-open');
        sweetOverlay.setAttribute('aria-hidden', 'true');
    }
}

function openSweetAlert({ title = 'Done', message = '', type = 'success', confirmText = 'OK', cancelText = '', onConfirm = null }) {
    if (!sweetOverlay) {
        if (onConfirm) onConfirm();
        return;
    }

    sweetTitle.textContent = title;
    sweetMessage.textContent = message;
    sweetIcon.textContent = type === 'warning' ? '!' : '✓';
    sweetConfirm.textContent = confirmText;
    sweetCancel.textContent = cancelText || 'Cancel';
    sweetCancel.style.display = cancelText ? 'inline-flex' : 'none';
    sweetOverlay.classList.add('is-open');
    sweetOverlay.setAttribute('aria-hidden', 'false');

    const close = () => {
        sweetOverlay.classList.remove('is-open');
        sweetOverlay.setAttribute('aria-hidden', 'true');
        sweetConfirm.onclick = null;
        sweetCancel.onclick = null;
    };

    sweetConfirm.onclick = () => {
        close();
        if (onConfirm) onConfirm();
    };

    sweetCancel.onclick = close;
}

const flashMessages = document.getElementById('flashMessages');

if (flashMessages) {
    try {
        const messages = JSON.parse(flashMessages.textContent);
        const latestMessage = messages[messages.length - 1];

        if (latestMessage) {
            const [category, message] = latestMessage;
            openSweetAlert({
                title: category === 'error' ? 'Check This' : 'Success',
                message,
                type: category === 'error' ? 'warning' : 'success'
            });
        }
    } catch (error) {
        console.warn('Could not parse flash messages', error);
    } finally {
        flashMessages.remove();
    }
}

const backButton = document.querySelector('.btn-back');
if (backButton) {
    backButton.addEventListener('click', () => {
        clearFlashMessages();
    });
}

window.addEventListener('pageshow', (event) => {
    if (event.persisted) {
        clearFlashMessages();
    }
});

document.querySelectorAll('[data-confirm]').forEach((button) => {
    button.addEventListener('click', (event) => {
        event.preventDefault();

        openSweetAlert({
            title: 'Are you sure?',
            message: button.getAttribute('data-confirm'),
            type: 'warning',
            confirmText: 'Yes',
            cancelText: 'Cancel',
            onConfirm: () => {
                button.closest('form').submit();
            }
        });
    });
});

const revealItems = document.querySelectorAll(
    '.reveal-on-scroll, .story-card, .stat-card, .search-filter-section, .categories-filter, .form-section, .post-detail, .no-stories'
);

if ('IntersectionObserver' in window) {
    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach((entry) => {
            entry.target.classList.toggle('is-visible', entry.isIntersecting);
        });
    }, {
        threshold: 0.12,
        rootMargin: '0px 0px -40px 0px'
    });

    revealItems.forEach((item) => revealObserver.observe(item));
} else {
    revealItems.forEach((item) => item.classList.add('is-visible'));
}

const colorInput = document.getElementById('color');
const colorPreview = document.querySelector('[data-color-preview]');

if (colorInput && colorPreview) {
    colorInput.addEventListener('input', () => {
        colorPreview.style.backgroundColor = colorInput.value;
    });
}

const categorySearch = document.querySelector('[data-category-search]');
const categoryCards = document.querySelectorAll('[data-category-name]');

if (categorySearch && categoryCards.length) {
    categorySearch.addEventListener('input', () => {
        const query = categorySearch.value.trim().toLowerCase();

        categoryCards.forEach((card) => {
            const matches = card.dataset.categoryName.includes(query);
            card.hidden = !matches;
        });
    });
}

document.querySelectorAll('[data-category-select-search]').forEach((searchInput) => {
    const select = document.getElementById(searchInput.dataset.categorySelectSearch);

    if (!select) {
        return;
    }

    searchInput.addEventListener('input', () => {
        const query = searchInput.value.trim().toLowerCase();

        Array.from(select.options).forEach((option, index) => {
            if (index === 0) {
                option.hidden = false;
                return;
            }

            option.hidden = query.length > 0 && !option.textContent.toLowerCase().includes(query);
        });
    });
});

document.querySelectorAll('[data-autosave-key]').forEach((form) => {
    const autosaveKey = form.dataset.autosaveKey;
    const fields = form.querySelectorAll('input[name], textarea[name], select[name]');
    const status = form.querySelector('[data-draft-status]');
    const savedData = localStorage.getItem(autosaveKey);

    const updateDraftStatus = (message) => {
        if (status) {
            status.textContent = message;
        }
    };

    if (savedData) {
        try {
            const values = JSON.parse(savedData);

            fields.forEach((field) => {
                if (Object.prototype.hasOwnProperty.call(values.fields, field.name) && values.fields[field.name] !== field.value) {
                    field.value = values.fields[field.name];
                }
            });

            updateDraftStatus('Draft restored from this device.');
        } catch (error) {
            localStorage.removeItem(autosaveKey);
        }
    }

    const saveDraft = () => {
        const values = {};

        fields.forEach((field) => {
            values[field.name] = field.value;
        });

        localStorage.setItem(autosaveKey, JSON.stringify({
            fields: values,
            savedAt: new Date().toISOString()
        }));

        updateDraftStatus(`Draft saved at ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}.`);
    };

    fields.forEach((field) => {
        field.addEventListener('input', saveDraft);
        field.addEventListener('change', saveDraft);
    });

    form.addEventListener('submit', () => {
        localStorage.removeItem(autosaveKey);
    });
});
