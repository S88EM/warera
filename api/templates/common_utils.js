/**
 * WarEra Common Frontend Utilities
 * Standardized across Clan Intelligence, Battles Purple Sniper, and Market Scanner.
 */

// Format numbers with space thousand-separators: 1234567 -> "1 234 567"
function formatNumber(num) {
    if (num === null || num === undefined || isNaN(num)) return '0';
    return Math.round(num).toString().replace(/\B(?=(\d{3})+(?!\d))/g, ' ');
}

// Format compact damage / money numbers: 1250000 -> "1.25M", 450000 -> "450.0k"
function formatMillions(num) {
    if (!num || isNaN(num) || num <= 0) return '0';
    if (num >= 1_000_000_000) return (num / 1_000_000_000).toFixed(2) + 'B';
    if (num >= 1_000_000) return (num / 1_000_000).toFixed(2) + 'M';
    if (num >= 1_000) return (num / 1_000).toFixed(1) + 'k';
    return Math.round(num).toString();
}

const formatDmg = formatMillions;
const formatCompact = formatMillions;

// Resolve API URL with Ingress prefix awareness
function getApiUrl(endpoint) {
    const cleanEndpoint = endpoint.replace(/^\/+/, '');
    const path = window.location.pathname;
    const ingressIdx = path.indexOf('/api/hassio_ingress/');
    if (ingressIdx !== -1) {
        const nextSlash = path.indexOf('/', ingressIdx + 20);
        const prefix = nextSlash !== -1 ? path.substring(0, nextSlash + 1) : (path + '/');
        return prefix + cleanEndpoint;
    }
    const basePath = path.replace(/\/[^/]*$/, '');
    return (basePath ? basePath : '') + '/' + cleanEndpoint;
}
window.getApiUrl = getApiUrl;

// Universal sleek Toast Notification
function showToast(msg, isSuccess = true) {
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        document.body.appendChild(toast);
    }
    const bgClass = isSuccess 
        ? 'bg-slate-900/95 text-emerald-400 border border-emerald-500/30' 
        : 'bg-slate-900/95 text-rose-400 border border-rose-500/30';
    const iconClass = isSuccess ? 'fa-circle-check text-emerald-400' : 'fa-circle-exclamation text-rose-400';

    toast.className = `fixed bottom-5 right-5 z-50 transform translate-y-0 opacity-100 transition-all duration-300 px-4 py-3 rounded-xl shadow-2xl text-xs font-semibold flex items-center gap-2.5 backdrop-blur-md ${bgClass}`;
    toast.innerHTML = `<i class="fa-solid ${iconClass} text-sm"></i> <span>${msg}</span>`;

    if (window._toastTimeout) clearTimeout(window._toastTimeout);
    window._toastTimeout = setTimeout(() => {
        toast.className = 'fixed bottom-5 right-5 z-50 transform translate-y-20 opacity-0 transition-all duration-300 pointer-events-none';
    }, 3500);
}

// Copy to clipboard helper
async function copyToClipboard(text, successMsg = 'Скопійовано у буфер!') {
    try {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(text);
        } else {
            const ta = document.createElement('textarea');
            ta.value = text;
            ta.style.position = 'fixed';
            ta.style.left = '-9999px';
            document.body.appendChild(ta);
            ta.select();
            document.execCommand('copy');
            document.body.removeChild(ta);
        }
        showToast(successMsg, true);
    } catch (e) {
        showToast('Помилка копіювання', false);
    }
}
