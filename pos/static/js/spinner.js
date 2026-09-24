/**
 * Reusable loading-spinner system.
 * Usage:
 *   showSpinner('Cargando...')
 *   hideSpinner()
 */

// Create the spinner overlay if it doesn't exist yet
function ensureSpinnerExists() {
    if (document.getElementById('loadingSpinner')) return;

    const spinnerHTML = `
        <div id="loadingSpinner" class="spinner-overlay" style="display: none;">
            <div class="spinner-container">
                <div class="spinner-border text-primary" role="status" style="width: 3rem; height: 3rem;">
                    <span class="sr-only">Cargando...</span>
                </div>
                <p class="spinner-text mt-3">Cargando...</p>
            </div>
        </div>
    `;

    const styleHTML = `
        <style>
            .spinner-overlay {
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background-color: rgba(0, 0, 0, 0.5);
                z-index: 9999;
                display: flex;
                justify-content: center;
                align-items: center;
            }

            .spinner-container {
                background-color: white;
                padding: 2rem;
                border-radius: 8px;
                text-align: center;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }

            .spinner-text {
                margin-top: 1rem;
                color: #333;
                font-weight: 500;
            }

            /* Inline spinner for buttons */
            .btn-spinner {
                display: inline-block;
                width: 1rem;
                height: 1rem;
                border: 2px solid currentColor;
                border-right-color: transparent;
                border-radius: 50%;
                animation: spinner-rotate 0.75s linear infinite;
                margin-right: 0.5rem;
                vertical-align: middle;
            }

            @keyframes spinner-rotate {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
        </style>
    `;

    document.head.insertAdjacentHTML('beforeend', styleHTML);
    document.body.insertAdjacentHTML('beforeend', spinnerHTML);
}

/**
 * Shows the global loading spinner.
 * @param {string} message - Message to display (optional)
 */
function showSpinner(message = 'Cargando...') {
    ensureSpinnerExists();

    const spinner = document.getElementById('loadingSpinner');
    const spinnerText = spinner.querySelector('.spinner-text');

    if (spinnerText) {
        spinnerText.textContent = message;
    }

    spinner.style.display = 'flex';
}

/**
 * Hides the global loading spinner.
 */
function hideSpinner() {
    const spinner = document.getElementById('loadingSpinner');
    if (spinner) {
        spinner.style.display = 'none';
    }
}

/**
 * Shows a spinner inside a specific button.
 * @param {HTMLElement} button - The button element
 * @param {string} loadingText - Text to show while loading (optional)
 * @returns {function} Function that restores the button
 */
function showButtonSpinner(button, loadingText = null) {
    if (!button) return () => {};

    // Save original state
    const originalHTML = button.innerHTML;
    const originalDisabled = button.disabled;

    // Create the inline spinner
    const spinnerHTML = '<span class="btn-spinner"></span>';
    const text = loadingText || button.dataset.loadingText || 'Cargando...';

    button.innerHTML = spinnerHTML + text;
    button.disabled = true;

    // Return a function that restores the button
    return () => {
        button.innerHTML = originalHTML;
        button.disabled = originalDisabled;
    };
}

/**
 * Wrapper that runs an async function while showing the spinner.
 * @param {function} asyncFn - Async function to run
 * @param {string} message - Spinner message
 * @returns {Promise} The function's result
 */
async function withSpinner(asyncFn, message = 'Cargando...') {
    showSpinner(message);
    try {
        const result = await asyncFn();
        return result;
    } finally {
        hideSpinner();
    }
}

/**
 * Wrapper that runs an async function while showing a button spinner.
 * @param {HTMLElement} button - The button element
 * @param {function} asyncFn - Async function to run
 * @param {string} loadingText - Text to show while loading
 * @returns {Promise} The function's result
 */
async function withButtonSpinner(button, asyncFn, loadingText = null) {
    const restore = showButtonSpinner(button, loadingText);
    try {
        const result = await asyncFn();
        return result;
    } finally {
        restore();
    }
}

/**
 * Shows a spinner inside a specific container.
 * @param {string|HTMLElement} container - Selector or container element
 * @param {string} message - Message (optional)
 */
function showContainerSpinner(container, message = 'Cargando...') {
    const element = typeof container === 'string'
        ? document.querySelector(container)
        : container;

    if (!element) return;

    const spinnerHTML = `
        <div class="text-center py-5 container-spinner">
            <div class="spinner-border text-primary" role="status">
                <span class="sr-only">Cargando...</span>
            </div>
            <p class="mt-2">${message}</p>
        </div>
    `;

    element.innerHTML = spinnerHTML;
}

/**
 * Hides a container's spinner.
 * @param {string|HTMLElement} container - Selector or container element
 */
function hideContainerSpinner(container) {
    const element = typeof container === 'string'
        ? document.querySelector(container)
        : container;

    if (!element) return;

    const spinner = element.querySelector('.container-spinner');
    if (spinner) {
        spinner.remove();
    }
}

// Expose functions globally
window.showSpinner = showSpinner;
window.hideSpinner = hideSpinner;
window.showButtonSpinner = showButtonSpinner;
window.withSpinner = withSpinner;
window.withButtonSpinner = withButtonSpinner;
window.showContainerSpinner = showContainerSpinner;
window.hideContainerSpinner = hideContainerSpinner;
