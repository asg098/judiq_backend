// ═══════════════════════════════════════════════════════════════════════════
// CONFIGURATION
// ═══════════════════════════════════════════════════════════════════════════

const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1' 
    ? "http://127.0.0.1:8000" 
    : "https://cheque-bounce-ragbased.onrender.com";
const API_URL = `${API_BASE_URL}/analyze`;


const firebaseConfig = {
    apiKey: "AIzaSyBdqc1C8LPVj4zqvWJWJWMrXhPad20MZCw",
    authDomain: "idcourt-cb58f.firebaseapp.com",
    projectId: "idcourt-cb58f",
    storageBucket: "idcourt-cb58f.firebasestorage.app",
    messagingSenderId: "941086914513",
    appId: "1:941086914513:web:8edad96b7e9f0dd4be12f0",
    measurementId: "G-YQMJ6KXGBR"
};

firebase.initializeApp(firebaseConfig);
const auth = firebase.auth();

// ═══════════════════════════════════════════════════════════════════════════
// RELIABILITY LAYER — Network, Retry, Error Classification
// ═══════════════════════════════════════════════════════════════════════════

/**
 * Classify API/network errors into user-friendly messages.
 */
function classifyApiError(err, httpStatus) {
    if (!navigator.onLine) {
        return {
            title:   'No Internet Connection',
            message: 'You appear to be offline. Please check your connection and try again.',
            code:    'OFFLINE',
            retry:   true
        };
    }
    if (err && (err.message === 'Failed to fetch' || err.name === 'TypeError')) {
        return {
            title:   'Cannot Reach Legal Engine',
            message: 'The server is unreachable. It may be starting up (cold start ~30s on free tier). Please wait and retry.',
            code:    'NETWORK_ERROR',
            retry:   true
        };
    }
    if (httpStatus === 400 || httpStatus === 422) {
        return {
            title:   'Invalid Case Data',
            message: err?.user_message || err?.error || 'Some required fields are missing or invalid. Please review your inputs.',
            code:    err?.error_code || 'VALIDATION_ERROR',
            retry:   false
        };
    }
    if (httpStatus === 429) {
        return {
            title:   'Too Many Requests',
            message: 'Server is busy. Please wait 30 seconds and try again.',
            code:    'RATE_LIMIT',
            retry:   true
        };
    }
    if (httpStatus >= 500) {
        return {
            title:   'Server Error',
            message: err?.user_message || 'The analysis engine encountered an internal error. Please try again.',
            code:    err?.error_code || 'SERVER_ERROR',
            retry:   true
        };
    }
    return {
        title:   'Analysis Failed',
        message: (err && (err.user_message || err.message)) || 'An unexpected error occurred.',
        code:    'UNKNOWN',
        retry:   true
    };
}

/**
 * Fetch with automatic retry on transient failures.
 * @param {string} url
 * @param {object} options  — fetch options
 * @param {number} maxRetries
 * @param {number} baseDelay  — ms, doubles on each retry (exponential backoff)
 */
async function fetchWithRetry(url, options = {}, maxRetries = 2, baseDelay = 2000) {
    let lastError;
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
        try {
            const controller = new AbortController();
            const timeout    = setTimeout(() => controller.abort(), 90_000); // 90s timeout
            const response   = await fetch(url, { ...options, signal: controller.signal });
            clearTimeout(timeout);
            return response;
        } catch (err) {
            lastError = err;
            if (err.name === 'AbortError') {
                throw new Error('Request timed out after 90 seconds. The server may be starting up — please retry.');
            }
            if (attempt < maxRetries) {
                const delay = baseDelay * Math.pow(2, attempt);
                console.warn(`[JUDIQ] Attempt ${attempt + 1} failed. Retrying in ${delay}ms…`, err.message);
                // Update loading text to show retry status
                const loadingText = document.getElementById('analysisLoadingText');
                if (loadingText) {
                    loadingText.textContent = `Connection attempt ${attempt + 2} of ${maxRetries + 1}…`;
                }
                await new Promise(r => setTimeout(r, delay));
            }
        }
    }
    throw lastError;
}

/**
 * Show a structured error modal/banner for analysis failures.
 */
function showAnalysisError(errorInfo) {
    const { title, message, code, retry } = errorInfo;

    // Update the toast with full context
    showToast(message, 'error', title);

    // Also surface a more visible in-page error if results screen is shown
    const errBanner = document.getElementById('analysisErrorBanner');
    if (errBanner) {
        errBanner.innerHTML = `
            <div class="analysis-error-box">
                <div class="aeb-icon"><i class="fas fa-exclamation-circle"></i></div>
                <div class="aeb-body">
                    <div class="aeb-title">${title}</div>
                    <div class="aeb-message">${message}</div>
                    ${code ? `<div class="aeb-code">Error code: <code>${code}</code></div>` : ''}
                </div>
                ${retry ? `<button class="btn btn-primary aeb-retry" onclick="executeSubmitCase()">
                    <i class="fas fa-redo"></i> Retry
                </button>` : ''}
            </div>`;
        errBanner.classList.remove('hidden');
    }
}

// Network status banner (shown persistently when offline)
function initNetworkMonitor() {
    function updateBanner() {
        let banner = document.getElementById('networkStatusBanner');
        if (!banner) {
            banner = document.createElement('div');
            banner.id = 'networkStatusBanner';
            banner.className = 'network-banner hidden';
            document.body.prepend(banner);
        }
        if (!navigator.onLine) {
            banner.innerHTML = '<i class="fas fa-wifi-slash"></i> You are offline — analysis requires internet connection.';
            banner.classList.remove('hidden');
        } else {
            banner.classList.add('hidden');
        }
    }
    window.addEventListener('online',  updateBanner);
    window.addEventListener('offline', updateBanner);
    updateBanner();
}


// ═══════════════════════════════════════════════════════════════════════════
// APPLICATION STATE - 🔥 SINGLE SOURCE OF TRUTH
// ═══════════════════════════════════════════════════════════════════════════

let currentUser = null;
let currentRole = null;
let currentStep = 1;
let totalSteps = 10;
let currentResultTab = 'overview';

// 🔥 CRITICAL: ONLY use window.caseData - NO OTHER VARIABLES
// Do NOT use: analysisResult, tempData, currentCaseData, etc.

let formData = {
    case_identity: {},
    parties: {},
    transaction: {},
    cheque: {},
    dishonour: {},
    notice: {},
    evidence: {},
    defence_inputs: {},
    behaviour: {},
    jurisdiction: {},
    limitation: {},
    settlement: {},
    narrative: {}
};

// ═══════════════════════════════════════════════════════════════════════════
// WIZARD STEP DEFINITIONS
// ═══════════════════════════════════════════════════════════════════════════

const wizardSteps = [
    {
        id: 'case_identity',
        title: 'Case Identity',
        subtitle: 'Basic case information and filing details',
        fields: [
            { name: 'case_id', label: 'Case ID', type: 'text', required: true, placeholder: 'e.g., CC/2024/123' },
            { name: 'case_title', label: 'Case Title', type: 'text', required: true, placeholder: 'Complainant vs Accused' },
            { name: 'complainant_type', label: 'Complainant Entity Type', type: 'select', options: ['Individual', 'Partnership Firm', 'Pvt Ltd/Ltd Company', 'HUF', 'Proprietorship'], required: true },
            { name: 'filing_date', label: 'Filing Date', type: 'date', required: true },
            { name: 'court_name', label: 'Court Name', type: 'text', required: true, placeholder: 'e.g., District Court, Mumbai' },
            { name: 'case_type', label: 'Case Type', type: 'select', options: ['Cheque Bounce', 'Civil', 'Criminal'], required: true }
        ]
    },
    {
        id: 'parties',
        title: 'Parties Information',
        subtitle: 'Details of complainant and accused',
        fields: [
            { name: 'complainant_name', label: 'Complainant Name', type: 'text', required: true },
            { name: 'complainant_address', label: 'Complainant Address', type: 'textarea', required: true },
            { name: 'complainant_authorized', label: 'Board Resolution/Authorization Available? (If Entity)', type: 'select', options: ['Yes - Original', 'Yes - Copy', 'No', 'Not Applicable'], required: true },
            { name: 'accused_name', label: 'Accused Name', type: 'text', required: true },
            { name: 'accused_type', label: 'Accused Entity Type', type: 'select', options: ['Individual', 'Pvt Ltd/Ltd Company', 'Partnership Firm', 'Other'], required: true },
            { name: 'accused_address', label: 'Accused Address', type: 'textarea', required: true },
            { name: 'directors_named', label: 'Directors/Authorized Signatories Named? (If Entity)', type: 'select', options: ['Yes - All', 'Yes - Partial', 'No', 'Not Applicable'], required: true },
            { name: 'accused_directors', label: 'Names of Directors/Partners Responsible', type: 'textarea', required: false, placeholder: 'e.g., Mr. A (Director), Mr. B (Managing Partner)' }
        ]
    },
    {
        id: 'transaction',
        title: 'Transaction Details',
        subtitle: 'Underlying debt and transaction information',
        fields: [
            { name: 'debt_amount', label: 'Total Debt Amount (₹)', type: 'number', required: true, placeholder: '50000' },
            { name: 'transaction_date', label: 'Transaction Date', type: 'date', required: true },
            { name: 'purpose', label: 'Purpose of Transaction', type: 'textarea', required: true, placeholder: 'Describe the reason for the debt/loan...' },
            { name: 'agreement_type', label: 'Agreement Type', type: 'select', options: ['Written Agreement', 'Verbal Agreement', 'Invoice/Bill', 'Promissory Note', 'No Formal Agreement'], required: true },
            { name: 'supporting_documents', label: 'Supporting Documents Available', type: 'select', options: ['Yes - All Documents', 'Yes - Partial', 'No Documents'], required: true },
            { name: 'debt_acknowledgment', label: 'Debt Acknowledged by Accused?', type: 'select', options: ['Yes - Written', 'Yes - Verbal', 'Partially', 'No'], required: true },
            { name: 'itr_available', label: 'Complainant ITR Available? (Financial Capacity)', type: 'select', options: ['Yes', 'No'], required: false },
            { name: 'loan_via_bank', label: 'Loan Advanced via Bank/Cheque?', type: 'select', options: ['Yes', 'No'], required: false }
        ]
    },
    {
        id: 'cheque',
        title: 'Cheque Details',
        subtitle: 'Information about the dishonoured cheque',
        fields: [
            { name: 'cheque_number', label: 'Cheque Number', type: 'text', required: true, placeholder: '123456' },
            { name: 'cheque_date', label: 'Cheque Date', type: 'date', required: true },
            { name: 'cheque_amount', label: 'Cheque Amount (₹)', type: 'number', required: true },
            { name: 'bank_name', label: 'Bank Name', type: 'text', required: true },
            { name: 'branch_name', label: 'Branch Name', type: 'text', required: false },
            { name: 'account_number', label: 'Account Number', type: 'text', required: false },
            { name: 'cheque_type', label: 'Cheque Type', type: 'select', options: ['Bearer Cheque', 'Account Payee Cheque', 'Crossed Cheque'], required: true },
            { name: 'post_dated', label: 'Post-Dated Cheque?', type: 'select', options: ['Yes', 'No'], required: true }
        ]
    },
    {
        id: 'dishonour',
        title: 'Dishonour Information',
        subtitle: 'Details of cheque dishonour and bank memo',
        fields: [
            { name: 'dishonour_date', label: 'Dishonour Date', type: 'date', required: true },
            { name: 'dishonour_reason', label: 'Reason for Dishonour', type: 'select', options: ['Insufficient Funds', 'Funds Insufficient', 'Account Closed', 'Signature Mismatch', 'Signature Differs', 'Payment Stopped', 'Refer to Drawer', 'Other'], required: true },
            { name: 'bank_memo_received', label: 'Bank Dishonour Memo Received?', type: 'select', options: ['Yes', 'No'], required: true },
            { name: 'memo_date', label: 'Memo Received Date', type: 'date', required: false },
            { name: 'presentation_date', label: 'First Presentation Date', type: 'date', required: true },
            { name: 'second_presentation', label: 'Second Presentation Made?', type: 'select', options: ['Yes', 'No', 'Not Applicable'], required: false },
            { name: 'second_presentation_date', label: 'Second Presentation Date', type: 'date', required: false }
        ]
    },
    {
        id: 'notice',
        title: 'Legal Notice (Section 138)',
        subtitle: 'Statutory notice details under NI Act',
        fields: [
            { name: 'notice_sent', label: 'Legal Notice Sent?', type: 'select', options: ['Yes', 'No', 'In Progress'], required: true },
            { name: 'notice_date', label: 'Notice Sent Date', type: 'date', required: false },
            { name: 'notice_mode', label: 'Mode of Sending Notice', type: 'select', options: ['Registered Post AD', 'Speed Post', 'Courier', 'Email (Not Recommended)', 'Hand Delivery', 'Multiple Modes'], required: false },
            { name: 'notice_received', label: 'Notice Received by Accused?', type: 'select', options: ['Yes - Acknowledged', 'Yes - Refused', 'Returned Unserved', 'Unknown'], required: false },
            { name: 'notice_received_date', label: 'Notice Received/Refused Date', type: 'date', required: false },
            { name: 'reply_received', label: 'Reply from Accused Received?', type: 'select', options: ['Yes - Full Payment', 'Yes - Denial', 'Yes - Partial Response', 'No Reply'], required: false },
            { name: 'within_30_days', label: 'Notice Sent Within 30 Days of Dishonour?', type: 'select', options: ['Yes', 'No'], required: false },
            { name: 'notice_content', label: 'Notice Demand Amount (₹)', type: 'number', required: false }
        ]
    },
    {
        id: 'evidence',
        title: 'Evidence & Documentation',
        subtitle: 'Available evidence to support your case',
        fields: [
            { name: 'original_cheque', label: 'Original Cheque Available?', type: 'select', options: ['Yes - Original', 'No - Lost', 'No - With Bank'], required: true },
            { name: 'dishonour_memo', label: 'Dishonour Memo Available?', type: 'select', options: ['Yes - Original', 'Yes - Copy', 'No'], required: true },
            { name: 'agreement_documents', label: 'Loan/Agreement Documents?', type: 'select', options: ['Yes - Signed Agreement', 'Yes - Unsigned Draft', 'Promissory Note', 'None'], required: false },
            { name: 'witness_available', label: 'Witnesses Available?', type: 'select', options: ['Yes - Multiple', 'Yes - One', 'No'], required: false },
            { name: 'communication_records', label: 'Email/SMS/WhatsApp Records?', type: 'select', options: ['Yes - Extensive', 'Yes - Limited', 'No'], required: false },
            { name: 'bank_statements', label: 'Bank Statements Available?', type: 'select', options: ['Yes - Complete', 'Yes - Partial', 'No'], required: false },
            { name: 'receipts_invoices', label: 'Receipts/Invoices Available?', type: 'select', options: ['Yes', 'No'], required: false }
        ]
    },
    {
        id: 'defence_inputs',
        title: 'Known Defence Arguments',
        subtitle: 'Any defence claims made by the accused',
        fields: [
            { name: 'signature_dispute', label: 'Signature Disputed by Accused?', type: 'select', options: ['Yes - Claimed Forged', 'Yes - Claimed Unauthorized', 'No', 'Unknown'], required: false },
            { name: 'debt_denial', label: 'Debt Denied Completely?', type: 'select', options: ['Yes - Complete Denial', 'Partially Denied', 'No', 'Unknown'], required: false },
            { name: 'cheque_security_claim', label: 'Accused Claims Cheque Was Security?', type: 'select', options: ['Yes', 'No', 'Unknown'], required: false },
            { name: 'limitation_claim', label: 'Limitation Period Claimed Expired?', type: 'select', options: ['Yes', 'No', 'Unknown'], required: false },
            { name: 'already_paid_claim', label: 'Accused Claims Already Paid?', type: 'select', options: ['Yes - Full', 'Yes - Partial', 'No', 'Unknown'], required: false },
            { name: 'jurisdiction_challenge', label: 'Jurisdiction Challenged?', type: 'select', options: ['Yes', 'No', 'Unknown'], required: false },
            { name: 'other_defences', label: 'Other Known Defences', type: 'textarea', required: false, placeholder: 'Describe any other defence arguments...' }
        ]
    },
    {
        id: 'behaviour',
        title: 'Post-Dishonour Conduct',
        subtitle: 'Accused behavior after cheque dishonour',
        fields: [
            { name: 'payment_offered', label: 'Settlement/Payment Offered?', type: 'select', options: ['Yes - Full Amount', 'Yes - Partial Amount', 'Yes - But Not Paid', 'No'], required: false },
            { name: 'partial_payment_amount', label: 'Partial Payment Amount (₹)', type: 'number', required: false },
            { name: 'partial_payment', label: 'Partial Payment Actually Made?', type: 'select', options: ['Yes', 'No'], required: false },
            { name: 'evasive_conduct', label: 'Evasive/Avoiding Conduct?', type: 'select', options: ['Yes - Avoiding Calls', 'Yes - Changed Address', 'Yes - Absconding', 'No'], required: false },
            { name: 'communication_ignored', label: 'Communications Ignored?', type: 'select', options: ['Yes - Completely', 'Yes - Partially', 'No - Responding'], required: false },
            { name: 'counter_claim', label: 'Counter Claim Filed?', type: 'select', options: ['Yes', 'No', 'Threatened'], required: false }
        ]
    },
    {
        id: 'settlement',
        title: 'Settlement & Final Review',
        subtitle: 'Settlement attempts and additional information',
        fields: [
            { name: 'settlement_attempted', label: 'Out-of-Court Settlement Attempted?', type: 'select', options: ['Yes - Multiple Times', 'Yes - Once', 'No'], required: false },
            { name: 'settlement_amount', label: 'Settlement Amount Discussed (₹)', type: 'number', required: false },
            { name: 'mediation_attempted', label: 'Mediation/Arbitration Attempted?', type: 'select', options: ['Yes - Formal Mediation', 'Yes - Informal', 'No'], required: false },
            { name: 'urgency_level', label: 'Case Urgency Level', type: 'select', options: ['Very Urgent', 'Urgent', 'Normal'], required: false },
            { name: 'previous_litigation', label: 'Previous Litigation with Accused?', type: 'select', options: ['Yes', 'No'], required: false },
            { name: 'additional_notes', label: 'Additional Case Notes/Context', type: 'textarea', required: false, placeholder: 'Any other relevant information about the case...' }
        ]
    }
];

const roleActions = {
    citizen: [
        { title: 'Check Case', description: 'Analyze your cheque bounce case strength', icon: 'fa-file-alt', color: '#0ea5e9', action: 'startCaseAnalysis' },
        { title: 'Smart Upload', description: 'Analyze WhatsApp/PDF documents', icon: 'fa-cloud-upload-alt', color: '#f59e0b', action: 'openSmartUpload' },
        { title: 'View Report', description: 'Access your case analysis reports', icon: 'fa-file-pdf', color: '#8b5cf6', action: 'viewReports' },
        { title: 'What Next', description: 'Get recommended next steps', icon: 'fa-tasks', color: '#10b981', action: 'viewGuidance' }
    ],
    lawyer: [
        { title: 'Create Case', description: 'Start new case analysis', icon: 'fa-plus-circle', color: '#0ea5e9', action: 'startCaseAnalysis' },
        { title: 'Smart Upload', description: 'Ingest evidence documents', icon: 'fa-cloud-upload-alt', color: '#f59e0b', action: 'openSmartUpload' },
        { title: 'Reports', description: 'View all case reports', icon: 'fa-file-pdf', color: '#8b5cf6', action: 'viewReports' },
        { title: 'Draft Generator', description: 'Generate court-ready drafts', icon: 'fa-file-alt', color: '#f59e0b', action: 'generateDraft' },
        { title: 'Strategy', description: 'Analyze case strategy', icon: 'fa-chess', color: '#10b981', action: 'viewStrategy' }
    ],
    student: [
        { title: 'Analyze Case', description: 'Learn case analysis techniques', icon: 'fa-search', color: '#0ea5e9', action: 'startCaseAnalysis' },
        { title: 'Smart Upload', description: 'Practice with real documents', icon: 'fa-cloud-upload-alt', color: '#f59e0b', action: 'openSmartUpload' },
        { title: 'Learn Mode', description: 'Educational case studies', icon: 'fa-book', color: '#8b5cf6', action: 'learnMode' },
        { title: 'Draft', description: 'Practice legal drafting', icon: 'fa-pen', color: '#10b981', action: 'generateDraft' }
    ]
};

// ═══════════════════════════════════════════════════════════════════════════
// TOAST NOTIFICATION SYSTEM
// ═══════════════════════════════════════════════════════════════════════════

function showToast(message, type = 'info', title = '', duration = 5000) {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    const icons = {
        success: 'fa-check-circle',
        error: 'fa-times-circle',
        warning: 'fa-exclamation-triangle',
        info: 'fa-info-circle'
    };

    const titles = {
        success: title || 'Success',
        error: title || 'Error',
        warning: title || 'Warning',
        info: title || 'Info'
    };

    toast.innerHTML = `
        <div class="toast-icon">
            <i class="fas ${icons[type]}"></i>
        </div>
        <div class="toast-content">
            <div class="toast-title">${titles[type]}</div>
            <div class="toast-message">${message}</div>
        </div>
        <button class="toast-close" onclick="this.parentElement.remove()">
            <i class="fas fa-times"></i>
        </button>
    `;

    container.appendChild(toast);

    if (duration > 0) {
        setTimeout(() => {
            toast.classList.add('removing');
            setTimeout(() => toast.remove(), 300);
        }, duration);
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// LOADING OVERLAY SYSTEM
// ═══════════════════════════════════════════════════════════════════════════

function showAnalysisLoading(message = 'Processing legal data with AI...') {
    const overlay = document.getElementById('analysisLoading');
    const text = document.getElementById('analysisLoadingText');
    text.textContent = message;
    overlay.classList.remove('hidden');
}

function hideAnalysisLoading() {
    const overlay = document.getElementById('analysisLoading');
    overlay.classList.add('hidden');
}

const toBoolean = (value) => {
    if (typeof value === 'boolean') return value;
    if (typeof value === 'string') {
        const normalized = value.toLowerCase().trim();
        return normalized === 'yes' || normalized === 'yes - original' || normalized === 'yes - written' || normalized === 'on' || normalized.startsWith('yes');
    }
    return false;
};

const isTruthy = (value) => {
    if (!value) return false;
    if (typeof value === 'boolean') return value;
    const s = String(value).toLowerCase().trim();
    return s === 'yes' || s === 'on' || s === 'true' || s.startsWith('yes -');
};

// ═══════════════════════════════════════════════════════════════════════════
// API DATA PROCESSOR LAYER (CRITICAL)
// ═══════════════════════════════════════════════════════════════════════════

function prepareApiData(formData) {

    const toNumber = (value, fallback = 0) => {
        const parsed = parseFloat(value);
        return isNaN(parsed) ? fallback : parsed;
    };

    const toValidDate = (value) => {
        if (!value) return null;
        const date = new Date(value);
        return isNaN(date.getTime()) ? null : date.toISOString().split('T')[0];
    };

    const safeGet = (obj, key, fallback = '') => {
        return obj && obj[key] !== undefined && obj[key] !== null ? obj[key] : fallback;
    };

    const case_identity = {
        case_id: safeGet(formData.case_identity, 'case_id', `CASE_${Date.now()}`),
        case_title: safeGet(formData.case_identity, 'case_title', 'Untitled Case'),
        complainant_type: safeGet(formData.case_identity, 'complainant_type', 'Individual'),
        filing_date: toValidDate(formData.case_identity?.filing_date),
        court_name: safeGet(formData.case_identity, 'court_name'),
        case_type: safeGet(formData.case_identity, 'case_type', 'Cheque Bounce')
    };

    const parties = {
        complainant: {
            name: safeGet(formData.parties, 'complainant_name'),
            address: safeGet(formData.parties, 'complainant_address'),
            is_authorized: toBoolean(formData.parties?.complainant_authorized)
        },
        accused: {
            name: safeGet(formData.parties, 'accused_name'),
            type: safeGet(formData.parties, 'accused_type', 'Individual'),
            address: safeGet(formData.parties, 'accused_address'),
            directors_named: toBoolean(formData.parties?.directors_named),
            director_names: safeGet(formData.parties, 'accused_directors', '')
        },
        relationship: safeGet(formData.parties, 'relationship')
    };

    const transaction = {
        debt_amount: toNumber(formData.transaction?.debt_amount, 0),
        transaction_date: toValidDate(formData.transaction?.transaction_date),
        purpose: safeGet(formData.transaction, 'purpose'),
        agreement_type: safeGet(formData.transaction, 'agreement_type'),
        supporting_documents: safeGet(formData.transaction, 'supporting_documents'),
        debt_acknowledged: toBoolean(formData.transaction?.debt_acknowledgment)
    };

    const cheque = {
        cheque_number: safeGet(formData.cheque, 'cheque_number'),
        cheque_date: toValidDate(formData.cheque?.cheque_date),
        cheque_amount: toNumber(formData.cheque?.cheque_amount, 0),
        bank_name: safeGet(formData.cheque, 'bank_name'),
        branch_name: safeGet(formData.cheque, 'branch_name'),
        account_number: safeGet(formData.cheque, 'account_number'),
        cheque_type: safeGet(formData.cheque, 'cheque_type', 'Bearer Cheque'),
        is_post_dated: toBoolean(formData.cheque?.post_dated)
    };

    const dishonour = {
        dishonour_date: toValidDate(formData.dishonour?.dishonour_date),
        dishonour_reason: safeGet(formData.dishonour, 'dishonour_reason', 'Insufficient Funds'),
        bank_memo_received: toBoolean(formData.dishonour?.bank_memo_received),
        memo_date: toValidDate(formData.dishonour?.memo_date),
        presentation_date: toValidDate(formData.dishonour?.presentation_date),
        second_presentation_made: toBoolean(formData.dishonour?.second_presentation),
        second_presentation_date: toValidDate(formData.dishonour?.second_presentation_date)
    };

    const notice = {
        notice_sent: toBoolean(formData.notice?.notice_sent),
        notice_date: toValidDate(formData.notice?.notice_date),
        notice_mode: safeGet(formData.notice, 'notice_mode'),
        notice_received: toBoolean(formData.notice?.notice_received),
        notice_received_date: toValidDate(formData.notice?.notice_received_date),
        reply_received: toBoolean(formData.notice?.reply_received),
        within_statutory_period: toBoolean(formData.notice?.within_30_days),
        demand_amount: toNumber(formData.notice?.notice_content, transaction.debt_amount)
    };

    const evidence = {
        original_cheque_available: toBoolean(formData.evidence?.original_cheque),
        dishonour_memo_available: toBoolean(formData.evidence?.dishonour_memo),
        agreement_documents_available: toBoolean(formData.evidence?.agreement_documents),
        witnesses_available: toBoolean(formData.evidence?.witness_available),
        communication_records: toBoolean(formData.evidence?.communication_records),
        bank_statements: toBoolean(formData.evidence?.bank_statements),
        receipts_available: toBoolean(formData.evidence?.receipts_invoices)
    };

    const defence_inputs = {
        signature_disputed: toBoolean(formData.defence_inputs?.signature_dispute),
        debt_denied: toBoolean(formData.defence_inputs?.debt_denial),
        cheque_as_security_claimed: toBoolean(formData.defence_inputs?.cheque_security_claim),
        limitation_period_expired: toBoolean(formData.defence_inputs?.limitation_claim),
        already_paid_claim: toBoolean(formData.defence_inputs?.already_paid_claim),
        jurisdiction_challenged: toBoolean(formData.defence_inputs?.jurisdiction_challenge),
        other_defences: safeGet(formData.defence_inputs, 'other_defences')
    };

    const behaviour = {
        payment_offered: toBoolean(formData.behaviour?.payment_offered),
        partial_payment_made: toBoolean(formData.behaviour?.partial_payment),
        partial_payment_amount: toNumber(formData.behaviour?.partial_payment_amount, 0),
        evasive_conduct: toBoolean(formData.behaviour?.evasive_conduct),
        communication_ignored: toBoolean(formData.behaviour?.communication_ignored),
        counter_claim_filed: toBoolean(formData.behaviour?.counter_claim)
    };

    const settlement = {
        settlement_attempted: toBoolean(formData.settlement?.settlement_attempted),
        settlement_amount_proposed: toNumber(formData.settlement?.settlement_amount, 0),
        mediation_attempted: toBoolean(formData.settlement?.mediation_attempted),
        urgency_level: safeGet(formData.settlement, 'urgency_level', 'Normal'),
        previous_litigation: toBoolean(formData.settlement?.previous_litigation),
        additional_context: safeGet(formData.settlement, 'additional_notes')
    };

    function extractLocation(address) {
        if (!address) return 'Unknown';
        const parts = address.split(',');
        return parts[parts.length - 1]?.trim() || 'Unknown';
    }

    function calculateLimitationPeriod(dishonourDate, filingDate) {
        if (!dishonourDate || !filingDate) return false;
        const dishonour = new Date(dishonourDate);
        const filing = new Date(filingDate);
        const monthsDiff = (filing.getFullYear() - dishonour.getFullYear()) * 12 +
            (filing.getMonth() - dishonour.getMonth());
        return monthsDiff <= 12;
    }

    const apiPayload = {
        // ── FLAT KEYS — read directly by backend normalizer.py ──────────────
        // These are the keys the backend's normalize_input() actually looks for.
        // Without these flat keys every boolean resolves to False → score = 0.
        cheque_present: isTruthy(cheque.cheque_number) || isTruthy(dishonour.bank_memo_received) || isTruthy(evidence.original_cheque_available),
        dishonour_memo: isTruthy(dishonour.bank_memo_received) || isTruthy(evidence.dishonour_memo_available),
        notice_sent: isTruthy(notice.notice_sent),
        debt_proven: isTruthy(transaction.debt_acknowledged) || isTruthy(evidence.agreement_documents_available),
        debt_evidence_type: String(formData.transaction?.debt_acknowledgment || 'None').includes('Written') ? 'Documentary' : (isTruthy(evidence.agreement_documents) ? 'Documentary' : 'Verbal'),
        within_30_days: isTruthy(notice.within_statutory_period) ? "Yes" : "No",
        notice_date: notice.notice_date,
        notice_received_date: notice.notice_received_date,
        memo_date: dishonour.memo_date,
        filing_date: case_identity.filing_date,
        amount: cheque.cheque_amount || transaction.debt_amount,
        description: [
            transaction.purpose,
            `Cheque no. ${cheque.cheque_number || 'N/A'} for ₹${cheque.cheque_amount || 0} dishonoured on ${dishonour.dishonour_date || 'unknown date'}.`,
            `Dishonour reason: ${dishonour.dishonour_reason || 'Insufficient Funds'}.`,
            notice.notice_sent ? `Legal notice sent via ${notice.notice_mode || 'registered post'}.` : 'No legal notice sent.',
            transaction.debt_acknowledged ? 'Debt acknowledged by accused.' : '',
            evidence.dishonour_memo_available ? 'Bank dishonour memo available.' : '',
            evidence.original_cheque_available ? 'Original cheque in possession.' : '',
            defence_inputs.signature_disputed ? 'Accused disputes signature on cheque.' : '',
            defence_inputs.cheque_as_security_claimed ? 'Accused claims cheque was given as security.' : '',
            defence_inputs.debt_denied ? 'Accused denies the debt completely.' : '',
            settlement.additional_context || ''
        ].filter(Boolean).join(' ').trim(),

        // ── FLATTENED DEFENCE SIGNALS (REQUIRED BY NORMALIZER.PY) ────────────
        signature_dispute:     defence_inputs.signature_disputed,
        debt_denial:           defence_inputs.debt_denial,
        cheque_security_claim: defence_inputs.cheque_as_security_claimed,
        accused_type:          parties.accused.type,
        directors_named:       parties.accused.directors_named,
        is_authorized:         parties.complainant.is_authorized,
        
        // ── NEW HARDENING FIELDS ──────────────────────────────────────────
        complainant_itr_available: toBoolean(formData.transaction?.itr_available),
        loan_via_bank:             toBoolean(formData.transaction?.loan_via_bank),
        draft_tone:                formData.narrative?.draft_tone || 'standard',

        // ── NESTED OBJECTS — kept for future backend enhancements ───────────
        case_identity,
        parties,
        transaction,
        cheque,
        dishonour,
        notice,
        evidence,
        defence_inputs,
        behaviour,
        settlement,
        jurisdiction: {
            court_jurisdiction: case_identity.court_name,
            location: extractLocation(parties.complainant.address)
        },
        limitation: {
            filing_within_period: calculateLimitationPeriod(dishonour.dishonour_date, case_identity.filing_date),
            notice_within_period: notice.within_statutory_period
        },
        metadata: {
            user_id: currentUser?.uid || 'anonymous',
            user_role: currentRole || 'citizen',
            submission_timestamp: new Date().toISOString(),
            frontend_version: '3.0'
        }
    };

    return apiPayload;
}

// ═══════════════════════════════════════════════════════════════════════════
// INITIALIZATION & AUTH
// ═══════════════════════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    setTimeout(() => {
        document.getElementById('loadingScreen').style.display = 'none';
    }, 1000);

    // 🔥 STEP 4 FIX: FORCE RESTORE from localStorage on page load
    const storedCase = localStorage.getItem('lastCase');

    if (storedCase) {
        try {
            const parsed = JSON.parse(storedCase);
            // 🔥 Store ONLY in window.caseData
            window.caseData = parsed;
            console.log("✅ Restored case data from localStorage:", window.caseData);

            // 🔥 CRITICAL: Render immediately if data exists
            if (window.caseData && window.caseData.score !== undefined) {
                console.log("🔥 Auto-rendering restored data...");
                renderFullReport(window.caseData);
            }
        } catch (e) {
            console.error('Error restoring case data:', e);
        }
    }

    auth.onAuthStateChanged(user => {
        if (user) {
            currentUser = user;
            currentRole = localStorage.getItem('userRole');
            if (currentRole) {
                showDashboard();
            } else {
                showRoleSelection();
            }
        } else {
            showLogin();
        }
    });

    setupAuthListeners();
});

function setupAuthListeners() {
    document.getElementById('showRegister')?.addEventListener('click', (e) => {
        e.preventDefault();
        showRegister();
    });

    document.getElementById('showLogin')?.addEventListener('click', (e) => {
        e.preventDefault();
        showLogin();
    });

    document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        await handleLogin(e.target);
    });

    document.getElementById('registerForm')?.addEventListener('submit', async (e) => {
        e.preventDefault();
        await handleRegister(e.target);
    });
}

function showLogin() {
    hideAllScreens();
    document.getElementById('loginScreen').classList.remove('hidden');
}

function showRegister() {
    hideAllScreens();
    document.getElementById('registerScreen').classList.remove('hidden');
}

function showRoleSelection() {
    hideAllScreens();
    document.getElementById('roleScreen').classList.remove('hidden');
}

async function handleLogin(form) {
    const email = form.querySelector('#loginEmail').value;
    const password = form.querySelector('#loginPassword').value;
    const submitBtn = form.querySelector('button[type="submit"]');

    try {
        submitBtn.classList.add('loading');
        await auth.signInWithEmailAndPassword(email, password);
        showToast('Welcome back! Redirecting to dashboard...', 'success', 'Login Successful');
    } catch (error) {
        showToast(getErrorMessage(error.code), 'error', 'Login Failed');
    } finally {
        submitBtn.classList.remove('loading');
    }
}

async function handleRegister(form) {
    const email = form.querySelector('#registerEmail').value;
    const password = form.querySelector('#registerPassword').value;
    const confirmPassword = form.querySelector('#registerConfirmPassword').value;
    const submitBtn = form.querySelector('button[type="submit"]');

    try {
        submitBtn.classList.add('loading');

        if (password !== confirmPassword) {
            throw new Error('Passwords do not match');
        }

        if (password.length < 6) {
            throw new Error('Password must be at least 6 characters');
        }

        await auth.createUserWithEmailAndPassword(email, password);
        showToast('Account created! Please select your role.', 'success', 'Registration Successful');
        showRoleSelection();
    } catch (error) {
        showToast(error.message || getErrorMessage(error.code), 'error', 'Registration Failed');
    } finally {
        submitBtn.classList.remove('loading');
    }
}

function getErrorMessage(code) {
    const messages = {
        'auth/email-already-in-use': 'This email is already registered',
        'auth/invalid-email': 'Invalid email address',
        'auth/user-not-found': 'No account found with this email',
        'auth/wrong-password': 'Incorrect password',
        'auth/weak-password': 'Password is too weak',
        'auth/network-request-failed': 'Network error. Please check your connection'
    };
    return messages[code] || 'An error occurred. Please try again';
}

function selectRole(role) {
    currentRole = role;
    localStorage.setItem('userRole', role);
    showToast(`Role selected: ${role.charAt(0).toUpperCase() + role.slice(1)}`, 'success', 'Profile Updated');
    setTimeout(() => showDashboard(), 500);
}

function logout() {
    auth.signOut();
    localStorage.removeItem('userRole');
    currentRole = null;
    currentUser = null;
    showToast('You have been logged out', 'info', 'Logged Out');
    showLogin();
}

// ═══════════════════════════════════════════════════════════════════════════
// DASHBOARD FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════

function showDashboard() {
    hideAllScreens();
    document.getElementById('dashboardScreen').classList.remove('hidden');
    document.getElementById('userEmail').textContent = currentUser.email;
    document.getElementById('userRoleBadge').textContent = currentRole.charAt(0).toUpperCase() + currentRole.slice(1);
    renderActionCards();
    loadRecentCases();
}

function renderActionCards() {
    const grid = document.getElementById('actionCardsGrid');
    const actions = roleActions[currentRole] || [];

    grid.innerHTML = actions.map(action => `
        <div class="action-card" onclick="${action.action}()">
            <div class="action-card-icon" style="background: linear-gradient(135deg, ${action.color}22 0%, ${action.color}44 100%);">
                <i class="fas ${action.icon}" style="color: ${action.color};"></i>
            </div>
            <h3>${action.title}</h3>
            <p>${action.description}</p>
            <button class="btn btn-outline">
                <i class="fas fa-arrow-right"></i> Start
            </button>
        </div>
    `).join('');
}

function loadRecentCases() {
    const container = document.getElementById('recentCases');
    const cases = JSON.parse(localStorage.getItem('recentCases') || '[]');

    if (cases.length === 0) {
        container.innerHTML = '<p style="text-align: center; color: var(--gray-500); padding: 2rem;">No recent cases yet. Start analyzing your first case!</p>';
        return;
    }

    container.innerHTML = cases.map(caseItem => `
        <div class="recent-case-item">
            <div class="recent-case-info">
                <h4>${caseItem.title || 'Case #' + caseItem.id}</h4>
                <p>${new Date(caseItem.date).toLocaleDateString()}</p>
            </div>
            <div class="recent-case-score">${caseItem.score}/100</div>
        </div>
    `).join('');
}

function saveRecentCase(caseData, score) {
    const cases = JSON.parse(localStorage.getItem('recentCases') || '[]');
    cases.unshift({
        id: Date.now(),
        title: caseData.case_identity?.case_title || 'Untitled Case',
        date: new Date().toISOString(),
        score: Math.round(score)
    });

    if (cases.length > 10) cases.pop();
    localStorage.setItem('recentCases', JSON.stringify(cases));
}

// ═══════════════════════════════════════════════════════════════════════════
// CASE WIZARD FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════

function startCaseAnalysis(initialData = null) {
    hideAllScreens();
    document.getElementById('caseWizardScreen').classList.remove('hidden');
    currentStep = 1;
    totalSteps = wizardSteps.length;
    
    // Initialize or use provided data
    formData = {
        case_identity: {}, parties: {}, transaction: {}, cheque: {}, dishonour: {},
        notice: {}, evidence: {}, defence_inputs: {}, behaviour: {}, jurisdiction: {},
        limitation: {}, settlement: {}, narrative: {}
    };

    if (initialData) {
        Object.keys(initialData).forEach(key => {
            if (formData[key]) {
                formData[key] = { ...formData[key], ...initialData[key] };
            }
        });
    }

    initializeWizard();
}

function initializeWizard() {
    renderProgressSteps();
    renderAllSteps();
    updateWizardDisplay();
}


function renderProgressSteps() {
    const container = document.getElementById('progressSteps');
    container.innerHTML = wizardSteps.map((step, index) => `
        <div class="progress-step ${index === 0 ? 'active' : ''}" data-step="${index + 1}">
            ${step.title}
        </div>
    `).join('');
}

function renderAllSteps() {
    const container = document.getElementById('wizardStepsContainer');
    container.innerHTML = wizardSteps.map((step, index) => `
        <div class="wizard-step ${index === 0 ? 'active' : ''}" data-step="${index + 1}">
            <form id="stepForm${index + 1}" class="wizard-form">
                <div class="form-row">
                    ${step.fields.map(field => renderField(field, step.id)).join('')}
                </div>
            </form>
        </div>
    `).join('');
}

function renderField(field, stepId) {
    const required = field.required ? 'required' : '';
    const placeholder = field.placeholder ? `placeholder="${field.placeholder}"` : '';
    
    // Get current value from formData if it exists
    const value = (formData[stepId] && formData[stepId][field.name]) ? formData[stepId][field.name] : '';

    const hint = getFieldGuidance(field.name);
    const hintHTML = hint ? `<small class="field-hint"><i class="fas fa-info-circle"></i> ${hint}</small>` : '';

    if (field.type === 'textarea') {
        return `
            <div class="form-group" style="grid-column: 1 / -1;">
                <label for="${field.name}">
                    ${field.label} 
                    ${field.required ? '<span style="color: var(--error-500);">*</span>' : ''}
                </label>
                <textarea id="${field.name}" name="${field.name}" ${required} ${placeholder} rows="3">${value}</textarea>
                ${hintHTML}
            </div>
        `;
    } else if (field.type === 'select') {
        return `
            <div class="form-group">
                <label for="${field.name}">
                    ${field.label} 
                    ${field.required ? '<span style="color: var(--error-500);">*</span>' : ''}
                </label>
                <select id="${field.name}" name="${field.name}" ${required}>
                    <option value="">Select...</option>
                    ${field.options.map(opt => `<option value="${opt}" ${value === opt ? 'selected' : ''}>${opt}</option>`).join('')}
                </select>
                ${hintHTML}
            </div>
        `;
    } else {
        return `
            <div class="form-group">
                <label for="${field.name}">
                    ${field.label} 
                    ${field.required ? '<span style="color: var(--error-500);">*</span>' : ''}
                </label>
                <input type="${field.type}" id="${field.name}" name="${field.name}" value="${value}" ${required} ${placeholder}>
                ${hintHTML}
            </div>
        `;
    }
}


// 🔥 FIELD GUIDANCE SYSTEM - COMPREHENSIVE LEGAL HINTS
function getFieldGuidance(fieldName) {
    const guidance = {
        // Notice Fields - CRITICAL
        'notice_sent': '⚖️ CRITICAL: Legal notice must be sent within 30 days of dishonour - mandatory by law',
        'notice_date': 'Date when the Section 138 notice was dispatched to the accused',
        'notice_mode': 'Registered Post AD is recommended for proof of delivery',
        'within_30_days': 'Notice timing is a legal requirement - late notice weakens case significantly',

        // Bank & Dishonour - HIGH PRIORITY
        'bank_memo_received': '📄 Bank dishonour memo is primary evidence - obtain from your bank',
        'dishonour_date': 'Exact date of dishonour triggers the 30-day notice window',
        'dishonour_reason': '"Insufficient Funds" is the strongest ground under Section 138',
        'memo_date': 'Date you received the dishonour memo from the bank',

        // Transaction - FOUNDATION
        'purpose': '✍️ Detailed explanation strengthens case - mention loan/service/goods clearly',
        'debt_amount': 'Total debt amount including principal and agreed interest',
        'transaction_date': 'Date when the debt was created or transaction occurred',
        'agreement_type': 'Written agreements provide strongest proof of debt',
        'supporting_documents': '📋 Documents significantly increase case success rate',

        // Cheque Details
        'cheque_number': 'Helps verify authenticity and track the instrument',
        'cheque_amount': 'Must match or be less than total debt amount',
        'cheque_date': 'Post-dated cheques are valid under Section 138',
        'bank_name': 'Bank where the cheque account is held',

        // Evidence - STRENGTH BUILDERS
        'original_cheque': 'Original physical cheque is strong evidence in court',
        'agreement_documents': 'Loan agreements/invoices establish debt relationship',
        'witness_available': '👥 Witnesses add credibility to your testimony',
        'communication_records': 'WhatsApp/Email/SMS showing debt acknowledgment helps',
        'bank_statements': 'Shows financial transactions related to the debt',

        // Legal Process
        'case_title': 'Format: Complainant Name vs Accused Name',
        'filing_date': 'File within 1 month of notice period expiry',
        'court_name': 'Jurisdiction must be where cheque dishonoured or payable',

        // Timeline Critical
        'debt_acknowledgment': 'Accused acknowledging debt strengthens your position',
        'reply_received': 'Reply from accused shows engagement with notice',

        // New Hardening Fields
        'itr_available': '📈 ITR records prove your financial capacity to lend (Basalingappa Rule)',
        'loan_via_bank': '🏦 Bank transfers are 100% safer than cash loans in court',
        'accused_directors': '🏢 List all responsible Directors/Partners for vicarious liability (S.141)',
        'draftTone': 'Select "Aggressive" for battle-ready, assertive legal storytelling'
    };

    return guidance[fieldName] || null;
}

function updateWizardDisplay() {
    const step = wizardSteps[currentStep - 1];

    document.getElementById('wizardTitle').textContent = step.title;
    document.getElementById('wizardSubtitle').textContent = step.subtitle;
    document.getElementById('stepBadgeNumber').textContent = currentStep;

    const progress = (currentStep / totalSteps) * 100;
    document.getElementById('progressFill').style.width = progress + '%';
    document.getElementById('progressPercentage').textContent = Math.round(progress) + '%';

    document.querySelectorAll('.progress-step').forEach((el, index) => {
        el.classList.remove('active', 'completed');
        if (index + 1 === currentStep) el.classList.add('active');
        else if (index + 1 < currentStep) el.classList.add('completed');
    });

    document.querySelectorAll('.wizard-step').forEach((el, index) => {
        el.classList.remove('active');
        if (index + 1 === currentStep) el.classList.add('active');
    });

    document.getElementById('currentStepDisplay').textContent = currentStep;
    document.getElementById('totalStepsDisplay').textContent = totalSteps;
    document.getElementById('prevBtn').disabled = currentStep === 1;
    document.getElementById('nextBtn').classList.toggle('hidden', currentStep === totalSteps);
    document.getElementById('submitBtn').classList.toggle('hidden', currentStep !== totalSteps);

    document.getElementById('wizardValidationFeedback').classList.add('hidden');
}

function validateCurrentStep() {
    const currentForm = document.querySelector(`#stepForm${currentStep}`);
    const requiredFields = currentForm.querySelectorAll('[required]');
    const errors = [];

    requiredFields.forEach(field => {
        if (!field.value || field.value.trim() === '') {
            errors.push(field.previousElementSibling.textContent.replace('*', '').trim());
            field.style.borderColor = 'var(--error-500)';
        } else {
            field.style.borderColor = 'var(--gray-200)';
        }
    });

    if (errors.length > 0) {
        showValidationErrors(errors);
        return false;
    }

    return true;
}

function showValidationErrors(errors) {
    const feedback = document.getElementById('wizardValidationFeedback');
    feedback.innerHTML = `
        <i class="fas fa-exclamation-circle"></i>
        <div class="wizard-validation-content">
            <h4>Please complete the following required fields:</h4>
            <ul class="wizard-validation-list">
                ${errors.map(err => `<li>${err}</li>`).join('')}
            </ul>
        </div>
    `;
    feedback.classList.remove('hidden');
    feedback.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function nextStep() {
    if (!validateCurrentStep()) {
        return;
    }

    saveStepData();

    if (currentStep < totalSteps) {
        currentStep++;
        updateWizardDisplay();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function previousStep() {
    saveStepData();
    if (currentStep > 1) {
        currentStep--;
        updateWizardDisplay();
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }
}

function saveStepData() {
    const step = wizardSteps[currentStep - 1];
    const stepForm = document.querySelector(`#stepForm${currentStep}`);
    const formDataObj = new FormData(stepForm);

    const stepData = {};
    for (let [key, value] of formDataObj.entries()) {
        stepData[key] = value;
    }

    formData[step.id] = stepData;
}

// ═══════════════════════════════════════════════════════════════════════════
// SUBMIT CASE & API INTEGRATION (FIXED)
// ═══════════════════════════════════════════════════════════════════════════

// ═══════════════════════════════════════════════════════════════════════════
// 🔥 UX ENHANCEMENT: COMPREHENSIVE PRE-SUBMISSION VALIDATION
// ═══════════════════════════════════════════════════════════════════════════

function validateCaseCompleteness() {
    const validation = {
        isValid: true,
        criticalMissing: [],
        warnings: [],
        dataCompleteness: 0,
        confidenceLevel: 'LOW'
    };

    // STEP 1: Check critical required fields
    const caseDescription = formData.case_identity?.case_title || '';
    const dishonourDate = formData.dishonour?.dishonour_date || '';
    const hasEvidence = formData.evidence && Object.keys(formData.evidence).some(key => isTruthy(formData.evidence[key]));

    if (!caseDescription || caseDescription.trim() === '') {
        validation.criticalMissing.push('Case description/title is required');
        validation.isValid = false;
    }

    if (!dishonourDate || dishonourDate.trim() === '') {
        validation.criticalMissing.push('Cheque dishonour date is required');
        validation.isValid = false;
    }

    if (!hasEvidence) {
        validation.criticalMissing.push('At least one piece of evidence is required');
        validation.isValid = false;
    }

    // STEP 2: Check for partial data (non-blocking warnings)
    const noticeSent = isTruthy(formData.notice?.notice_sent);
    const hasDocuments = isTruthy(formData.evidence?.dishonour_memo) || isTruthy(formData.evidence?.agreement_documents);
    const hasTimeline = formData.transaction?.transaction_date;

    let completenessScore = 0;
    const totalChecks = 10;

    // Calculate data completeness
    if (caseDescription) completenessScore++;
    if (dishonourDate) completenessScore++;
    if (hasEvidence) completenessScore++;
    if (noticeSent) completenessScore++;
    if (hasDocuments) completenessScore++;
    if (hasTimeline) completenessScore++;
    if (formData.cheque?.cheque_amount) completenessScore++;
    if (formData.parties?.complainant_name) completenessScore++;
    if (formData.parties?.accused_name) completenessScore++;
    if (formData.transaction?.debt_amount) completenessScore++;

    validation.dataCompleteness = Math.round((completenessScore / totalChecks) * 100);

    // Determine confidence level
    if (validation.dataCompleteness >= 70) {
        validation.confidenceLevel = 'HIGH';
    } else if (validation.dataCompleteness >= 40) {
        validation.confidenceLevel = 'MEDIUM';
    } else {
        validation.confidenceLevel = 'LOW';
    }

    // Add warnings for missing optional but important data
    if (!noticeSent) {
        validation.warnings.push('Legal notice not sent - This significantly weakens your case (required within 30 days of dishonour)');
    }

    if (!hasDocuments) {
        validation.warnings.push('No supporting documents (bank memo, transaction proof) - Evidence strengthens your case');
    }

    if (!hasTimeline) {
        validation.warnings.push('Transaction date missing - Timeline helps establish the case chronology');
    }

    return validation;
}

function showValidationDialog(validation) {
    // Create modal overlay
    const modalHTML = `
        <div id="validationModal" class="validation-modal-overlay">
            <div class="validation-modal">
                <div class="validation-modal-header">
                    <i class="fas fa-exclamation-triangle" style="color: var(--error-600); font-size: 2rem;"></i>
                    <h3>Cannot Submit Case</h3>
                </div>
                <div class="validation-modal-content">
                    <p style="margin-bottom: 1rem; color: var(--gray-700);">
                        Please complete the following required information before analysis:
                    </p>
                    <ul class="validation-error-list">
                        ${validation.criticalMissing.map(item => `
                            <li><i class="fas fa-times-circle"></i> ${item}</li>
                        `).join('')}
                    </ul>
                    <div class="validation-help-box">
                        <i class="fas fa-lightbulb"></i>
                        <p>These fields are essential for AI analysis to provide accurate case evaluation.</p>
                    </div>
                </div>
                <div class="validation-modal-footer">
                    <button class="btn btn-primary" onclick="closeValidationModal()">
                        <i class="fas fa-check"></i> Got it, I'll complete these
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function showWarningDialog(validation) {
    const modalHTML = `
        <div id="warningModal" class="validation-modal-overlay">
            <div class="validation-modal warning-modal">
                <div class="validation-modal-header">
                    <i class="fas fa-exclamation-triangle" style="color: var(--warning-600); font-size: 2rem;"></i>
                    <h3>Weak Case Warning</h3>
                </div>
                <div class="validation-modal-content">
                    <div class="completeness-indicator">
                        <div class="completeness-label">
                            <span>Data Completeness</span>
                            <span class="completeness-value">${validation.dataCompleteness}%</span>
                        </div>
                        <div class="completeness-bar">
                            <div class="completeness-progress" style="width: ${validation.dataCompleteness}%"></div>
                        </div>
                        <div class="confidence-badge confidence-${validation.confidenceLevel.toLowerCase()}">
                            Analysis Confidence: ${validation.confidenceLevel}
                        </div>
                    </div>
                    
                    <p style="margin: 1.5rem 0 1rem; color: var(--gray-700); font-weight: 500;">
                        ⚠️ This case may receive a low score due to:
                    </p>
                    <ul class="validation-warning-list">
                        ${validation.warnings.map(item => `
                            <li><i class="fas fa-info-circle"></i> ${item}</li>
                        `).join('')}
                    </ul>
                    <div class="validation-help-box" style="background: var(--warning-50); border-color: var(--warning-200);">
                        <i class="fas fa-lightbulb" style="color: var(--warning-600);"></i>
                        <p style="color: var(--warning-900);">You can still proceed, but consider adding this information for a more accurate analysis.</p>
                    </div>
                </div>
                <div class="validation-modal-footer">
                    <button class="btn btn-outline" onclick="closeWarningModal()">
                        <i class="fas fa-arrow-left"></i> Go Back & Add More Data
                    </button>
                    <button class="btn btn-primary" onclick="proceedWithWarning()">
                        <i class="fas fa-arrow-right"></i> Proceed Anyway
                    </button>
                </div>
            </div>
        </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHTML);
}

function closeValidationModal() {
    const modal = document.getElementById('validationModal');
    if (modal) modal.remove();
}

function closeWarningModal() {
    const modal = document.getElementById('warningModal');
    if (modal) modal.remove();
}

function proceedWithWarning() {
    closeWarningModal();
    // Actually submit the case
    executeSubmitCase();
}

async function submitCase() {
    if (!validateCurrentStep()) {
        return;
    }

    saveStepData();

    // 🔥 STEP 1: STRICT INPUT VALIDATION
    const validation = validateCaseCompleteness();

    if (!validation.isValid) {
        // Show blocking error modal
        showValidationDialog(validation);
        showToast("Please fill required legal details before analysis", "warning", "Incomplete Data");
        return;
    }

    // 🔥 STEP 2: SMART WARNING (NON-BLOCKING)
    if (validation.warnings.length > 0 && validation.dataCompleteness < 60) {
        // Show warning modal with option to proceed
        showWarningDialog(validation);
        return;
    }

    // If validation passes or data is complete enough, proceed
    executeSubmitCase();
}

async function executeSubmitCase() {

    // ── Offline guard ──────────────────────────────────────────────────────
    if (!navigator.onLine) {
        showAnalysisError(classifyApiError(null, null));
        return;
    }

    const submitBtn = document.getElementById('submitBtn');
    if (submitBtn) { submitBtn.classList.add('loading'); submitBtn.disabled = true; }

    // Hide any previous error banner
    const errBanner = document.getElementById('analysisErrorBanner');
    if (errBanner) errBanner.classList.add('hidden');

    showAnalysisLoading('Initializing legal analysis engine…');

    let httpStatus = null;

    try {
        console.log('[JUDIQ] Starting case analysis…');
        const apiData = prepareApiData(formData);

        // Animate loading text
        const steps = [
            [800,  'Parsing case facts…'],
            [2000, 'Applying NI Act statutory rules…'],
            [4000, 'Running AI reasoning engine…'],
            [6000, 'Generating explainability trail…'],
            [8000, 'Building court-ready analysis…'],
        ];
        steps.forEach(([delay, text]) => {
            setTimeout(() => {
                const el = document.getElementById('analysisLoadingText');
                if (el) el.textContent = text;
            }, delay);
        });

        // ── API call with retry ────────────────────────────────────────────
        console.log(`[JUDIQ] Sending request to: ${API_URL}`);
        const response = await fetchWithRetry(API_URL, {
            method:  'POST',
            mode:    'cors',
            headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
            body:    JSON.stringify(apiData)
        }, 2, 3000);

        httpStatus = response.status;

        // ── Parse error responses ──────────────────────────────────────────
        if (!response.ok) {
            let errBody = {};
            try { errBody = await response.json(); } catch (_) {}
            const classified = classifyApiError(errBody, httpStatus);
            throw classified; // jump to catch — it's already classified
        }

        // ── Parse success response ─────────────────────────────────────────
        let data;
        try {
            data = await response.json();
        } catch (parseErr) {
            throw { title: 'Response Error', message: 'Server returned an unreadable response. Please retry.', code: 'PARSE_ERROR', retry: true };
        }

        console.log('[JUDIQ] ✅ API response received:', data);

        // ── Schema validation ──────────────────────────────────────────────
        if (!data || (!data.score && data.score !== 0)) {
            console.warn('[JUDIQ] Response missing score field — may be partial.', data);
        }
        if (data.success === false) {
            throw classifyApiError({ user_message: data.user_message, error: data.error, error_code: data.error_code }, httpStatus || 500);
        }

        // ── Store data ─────────────────────────────────────────────────────
        window.caseData = data;
        try { localStorage.setItem('lastCase', JSON.stringify(data)); } catch (_) {}

        // ── Render ─────────────────────────────────────────────────────────
        hideAnalysisLoading();
        renderFullReport(window.caseData);
        try { saveRecentCase(formData, data.score || 0); } catch (_) {}

        showToast('Case analysis completed successfully!', 'success', 'Analysis Complete');
        setTimeout(() => showResults(), 400);

    } catch (error) {
        console.error('[JUDIQ] Analysis error:', error);
        hideAnalysisLoading();

        // If it was already classified by classifyApiError, use it directly
        if (error && error.code && error.title) {
            showAnalysisError(error);
        } else {
            showAnalysisError(classifyApiError(error, httpStatus));
        }
    } finally {
        if (submitBtn) { submitBtn.classList.remove('loading'); submitBtn.disabled = false; }
    }
}


// ═══════════════════════════════════════════════════════════════════════════
// RESULTS TAB SYSTEM (NEW)
// ═══════════════════════════════════════════════════════════════════════════

function switchResultTab(tabName) {
    // Update active tab button
    document.querySelectorAll('.tab-button').forEach(btn => {
        btn.classList.remove('active');
        if (btn.getAttribute('data-tab') === tabName) {
            btn.classList.add('active');
        }
    });

    // Update active tab content - hide all first
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.add('hidden');
        content.classList.remove('active');
    });

    // Show the selected tab
    const tabId = `tab${tabName.charAt(0).toUpperCase() + tabName.slice(1)}`;
    const targetTab = document.getElementById(tabId);
    if (targetTab) {
        targetTab.classList.remove('hidden');
        targetTab.classList.add('active');
    }

    currentResultTab = tabName;
}

// ═══════════════════════════════════════════════════════════════════════════
// 🔥 STEP 2: COMPREHENSIVE RENDER FUNCTION - RENDERS ALL FIELDS
// ═══════════════════════════════════════════════════════════════════════════

function renderFullReport(data) {
    // Scroll to results container top
    const resContainer = document.querySelector('.results-container');
    if (resContainer) resContainer.scrollTop = 0;
    
    // Auto-sync Caseroom if present
    if (data.caseroom_id) {
        currentCaseroomId = data.caseroom_id;
        startCaseroomSync();
    }
    
    if (!data) {
        console.error("❌ No data to render");
        return;
    }
    console.log("🔥 RENDERING FULL REPORT WITH DATA:", data);

    // ── FATAL DEFECTS ALERT (Advocate-Grade Hardening) ─────────────────────
    const fatalContainer = document.getElementById('fatalDefectAlert');
    if (fatalContainer) {
        let fatalHTML = '';
        const score = data.score || 0;
        
        // 1. Premature Filing Check
        if (data.limitation && data.limitation.is_premature) {
            fatalHTML += `
                <div class="fatal-banner">
                    <i class="fas fa-exclamation-triangle"></i>
                    <div>
                        <strong>FATAL DEFECT: PREMATURE FILING DETECTED</strong>
                        <p>The 15-day statutory 'cure period' for the accused has not expired. Filing today will lead to mandatory dismissal as per <em>Yogendra Pratap Singh vs. Savitri Pandey</em>. <strong>DO NOT FILE UNTIL ${data.limitation.earliest_filing_date || 'the period expires'}.</strong></p>
                    </div>
                </div>
            `;
        }
        
        // 2. Late Notice Check
        if (data.within_30_days === "No" || (data.limitation && data.limitation.notice_delay_days > 0)) {
            fatalHTML += `
                <div class="fatal-banner fatal-warning">
                    <i class="fas fa-clock"></i>
                    <div>
                        <strong>JURISDICTIONAL BAR: LATE STATUTORY NOTICE</strong>
                        <p>The legal notice was sent beyond the 30-day limit. The case is non-maintainable unless a robust Condonation of Delay application is filed under Section 142(1)(b).</p>
                    </div>
                </div>
            `;
        }

        // 3. Electronic Evidence Warning
        const communicationDetected = (data.weaknesses || []).some(w => String(w).includes("65B") || String(w).includes("digital evidence"));
        if (communicationDetected) {
            fatalHTML += `
                <div class="fatal-banner fatal-info">
                    <i class="fas fa-microchip"></i>
                    <div>
                        <strong>ADMISSIBILITY REQUIREMENT: SECTION 65B CERTIFICATE</strong>
                        <p>Digital evidence (WhatsApp/Email) is inadmissible without a mandatory certificate under Section 65B of the Indian Evidence Act. Ensure this is filed with the complaint.</p>
                    </div>
                </div>
            `;
        }

        fatalContainer.innerHTML = fatalHTML;
        fatalContainer.classList.toggle('hidden', fatalHTML === '');
    }

    // === SCORE ===
    const score = data.score || 0;
    const scoreEl = document.getElementById("scoreNumber");
    if (scoreEl) scoreEl.innerText = score;

    // === VERDICT ===
    const verdict = mapVerdict(data.verdict);
    const verdictTitleEl = document.getElementById("verdictTitle");
    const verdictDescEl = document.getElementById("verdictDescription");
    const cynicalBadge = document.getElementById("cynicalModeBadge");

    if (verdictTitleEl) verdictTitleEl.textContent = verdict;
    if (verdictDescEl) verdictDescEl.textContent = getVerdictDescription(score);
    
    // 🔥 CYNICAL MODE VISIBILITY
    if (cynicalBadge) {
        const isCynical = score < 65 || (data.reasoning_trace || []).some(t => String(t).includes('CYNICAL'));
        cynicalBadge.classList.toggle('hidden', !isCynical);
    }

    // === RISK LEVEL ===
    const riskEl = document.getElementById("defenceRisk");
    if (riskEl) riskEl.innerText = data.risk_level || data.defence_risk || "Unknown";

    // === COUNTS ===
    const issuesCountEl = document.getElementById("criticalIssues");
    const strengthsCountEl = document.getElementById("strongPoints");
    const conceptsCountEl = document.getElementById("conceptsDetected");

    if (issuesCountEl) issuesCountEl.innerText = (data.issues || []).length || 0;
    if (strengthsCountEl) strengthsCountEl.innerText = (data.strengths || []).length || 0;

    const semanticAnalysis = data.semantic_analysis || {};
    const conceptsCount = (semanticAnalysis.concepts_detected || []).length || 0;
    if (conceptsCountEl) conceptsCountEl.innerText = conceptsCount;

    // === VERDICT STYLING ===
    const verdictCard = document.querySelector('.result-card-hero');
    const verdictIcon = document.getElementById('verdictIcon');

    if (verdictCard && verdictIcon) {
        if (score >= 70) {
            verdictCard.className = 'result-card result-card-hero verdict-strong';
            verdictIcon.innerHTML = '<i class="fas fa-check-circle"></i>';
        } else if (score >= 40) {
            verdictCard.className = 'result-card result-card-hero verdict-moderate';
            verdictIcon.innerHTML = '<i class="fas fa-exclamation-triangle"></i>';
        } else {
            verdictCard.className = 'result-card result-card-hero verdict-weak';
            verdictIcon.innerHTML = '<i class="fas fa-times-circle"></i>';
        }
    }

    // Animate score
    animateScore(score);

    // === RENDER ALL LISTS (MANDATORY) ===
    renderList("issuesList", data.issues, "No critical issues detected");
    renderList("strengthsList", data.strengths, "No strong points identified");
    renderList("weaknessesList", data.weaknesses, "No significant weaknesses identified");
    renderList("timelineList", data.timeline, "No timeline available");
    // recommended_actions lives inside decision.next_steps
    const recommendedActions = (data.decision && data.decision.next_steps)
        || data.recommended_actions || data.next_steps || [];
    renderList("actionsList", recommendedActions, "No recommended actions");
    renderList("contradictionsList", data.contradictions || [], "No contradictions detected");

    // === LEGAL STRATEGY (handle array or string) ===
    if (Array.isArray(data.legal_strategy)) {
        renderList("strategyList", data.legal_strategy, "No strategy available");
    } else if (data.legal_strategy) {
        const strategyListEl = document.getElementById("strategyList");
        if (strategyListEl) {
            strategyListEl.innerHTML = `<div class="list-item">${data.legal_strategy}</div>`;
        }
    } else {
        renderList("strategyList", [], "No strategy available");
    }

    // === PREDICTED DEFENCES ===
    const defences = data.defence_strategy || data.predicted_defences || data.defence || data.top_defences || data.defences_ranked || [];
    displayDefences(defences);

    // === SEMANTIC ANALYSIS ===
    displaySemanticAnalysis(data.semantic_analysis || {});

    // === DECISION & NEXT STEPS ===
    if (data.decision) {
        renderDecisionPanel(data.decision);
    }

    // === REASONING TRACE ===
    const reasoning = data.reasoning_trace || data.reasoning || [];
    displayReasoningTrace(reasoning);

    // === DRAFT ===
    const draftText = data.draft || data.legal_draft || data.generated_draft 
                   || (data.data && (data.data.draft || data.data.legal_draft))
                   || "";
    const draftPreviewEl = document.getElementById("draftPreviewContent");
    const draftContentEl = document.getElementById("draftContent");

    if (draftPreviewEl) draftPreviewEl.value = draftText || "Legal draft is being generated. Please try 'Generate Report' to download the full draft.";
    if (draftContentEl) draftContentEl.value = draftText || "Legal draft is being generated. Please try 'Generate Report' to download the full draft.";

    // === LEGAL ANALYSIS (additional field) ===
    const legalAnalysisEl = document.getElementById("legalAnalysis");
    if (legalAnalysisEl && data.legal_analysis) {
        legalAnalysisEl.innerText = data.legal_analysis;
    } else if (legalAnalysisEl) {
        legalAnalysisEl.innerText = "No legal analysis available";
    }

    console.log("✅ Full report rendered successfully - ALL fields processed");

    // 🔥 EXPERT FIX: Limitation Countdown & Corporate Alert
    renderLimitationClock(data);
    renderCorporateWarning(data);

    // 🔥 STEP 3 & 4: ADD SCORE EXPLANATION AND INSIGHT PANEL
    renderScoreExplanation(data);
    renderImprovementSuggestions(data);
    renderConfidenceIndicator(data);
    renderCaseSummaryCard(data);
    renderAIReasoningLayer(data);
}
/**
 * 🔥 EXPERT FIX: Implement Draft Tone Customization
 * Resolves ReferenceError and adds client-side tone shifting
 */
function setDraftTone(tone) {
    const draftPreviewEl = document.getElementById("draftPreviewContent");
    if (!draftPreviewEl || !draftPreviewEl.value) return;

    // Update UI active state
    document.querySelectorAll('.btn-tone').forEach(btn => {
        btn.classList.remove('active');
        if (btn.innerText.toLowerCase() === tone) {
            btn.classList.add('active');
        }
    });

    let currentDraft = draftPreviewEl.value;

    // Simple semantic substitution for tone shifting
    const toneMaps = {
        aggressive: [
            ["demand that you pay", "STRICTLY DEMAND IMMEDIATE PAYMENT"],
            ["initiate criminal proceedings", "COMMENCE RIGOROUS CRIMINAL PROSECUTION"],
            ["failure to make payment", "WILFUL AND DISHONEST DEFAULT"],
            ["Negotiable Instruments Act", "PUNITIVE PROVISIONS of the Negotiable Instruments Act"],
            ["Sir/Madam", "TAKE NOTICE"],
            ["Yours faithfully", "IN ANTICIPATION OF COMPLIANCE"]
        ],
        conciliatory: [
            ["demand that you pay", "kindly request you to clear the outstanding dues"],
            ["initiate criminal proceedings", "resolve this matter amicably to avoid litigation"],
            ["failure to make payment", "inadvertent delay in payment"],
            ["Sir/Madam", "Dear Sir/Madam"],
            ["Yours faithfully", "Yours sincerely"]
        ],
        standard: [] // Reset to standard would require original - for now we just show a message
    };

    if (tone === 'standard') {
        // If we have the original in window.caseData, restore it
        if (window.caseData && window.caseData.draft) {
            draftPreviewEl.value = window.caseData.draft;
        }
        showToast("Draft reset to standard professional tone.", "info");
        return;
    }

    const map = toneMaps[tone];
    if (map) {
        let modifiedDraft = currentDraft;
        map.forEach(([standard, replacement]) => {
            const regex = new RegExp(standard, 'gi');
            modifiedDraft = modifiedDraft.replace(regex, replacement);
        });

        draftPreviewEl.value = modifiedDraft;
        showToast(`Draft language shifted to ${tone.toUpperCase()} tone.`, "success");
    }
}

function renderLimitationClock(data) {
    const clockEl = document.getElementById('limitationCountdown');
    const daysEl = document.getElementById('countdownDays');
    const msgEl = document.getElementById('limitationMessage');
    const fillEl = document.getElementById('limitationStatusFill');

    if (!clockEl || !daysEl || !msgEl || !fillEl) return;

    // We expect the backend to provide limitation details
    // If not, we look at the timeline strings
    let daysRemaining = null;
    let message = "";

    // Attempt to extract from timeline if not explicit
    if (data.timeline) {
        const limitationLine = data.timeline.find(l => l.includes("Limitation period expires on"));
        if (limitationLine) {
            const dateMatch = limitationLine.match(/\d{4}-\d{2}-\d{2}/);
            if (dateMatch) {
                const expiryDate = new Date(dateMatch[0]);
                const today = new Date();
                daysRemaining = Math.ceil((expiryDate - today) / (1000 * 60 * 60 * 24));
                message = `Your statutory window for filing expires on ${dateMatch[0]}.`;
            }
        }
    }

    if (daysRemaining !== null) {
        clockEl.classList.remove('hidden');
        daysEl.textContent = daysRemaining;
        msgEl.textContent = message;

        // Update color and progress
        if (daysRemaining <= 0) {
            daysEl.style.color = "var(--error-600)";
            msgEl.innerHTML = "<strong>CRITICAL: Limitation period has expired.</strong> Case may be time-barred.";
            fillEl.style.width = "100%";
            fillEl.style.background = "var(--error-600)";
        } else if (daysRemaining <= 7) {
            daysEl.style.color = "var(--error-500)";
            fillEl.style.width = `${((30 - daysRemaining) / 30) * 100}%`;
            fillEl.style.background = "var(--error-500)";
        } else {
            daysEl.style.color = "var(--primary-600)";
            fillEl.style.width = `${((30 - daysRemaining) / 30) * 100}%`;
            fillEl.style.background = "var(--primary-500)";
        }
    } else {
        clockEl.classList.add('hidden');
    }
}

function renderCorporateWarning(data) {
    const alertEl = document.getElementById('corporateAlert');
    if (!alertEl) return;

    const accusedName = (window.formData && window.formData.accused_name) || "";
    const isCompany = /pvt|ltd|corp|inc|co\.|company/i.test(accusedName);

    if (isCompany) {
        alertEl.classList.remove('hidden');
    } else {
        alertEl.classList.add('hidden');
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// 🔥 NEW: CASE SUMMARY CARD - EXECUTIVE OVERVIEW
// ═══════════════════════════════════════════════════════════════════════════

function renderCaseSummaryCard(data) {
    const score = data.score || 0;
    const summaryContainer = document.getElementById('scoreExplanation');

    if (!summaryContainer) return;

    // Determine case strength level
    let strengthLevel, strengthColor, strengthIcon, actionText;
    if (score >= 70) {
        strengthLevel = 'STRONG';
        strengthColor = 'success';
        strengthIcon = 'fa-shield-alt';
        actionText = 'Your case has solid legal merit. Proceed with confidence.';
    } else if (score >= 50) {
        strengthLevel = 'MODERATE';
        strengthColor = 'warning';
        strengthIcon = 'fa-balance-scale';
        actionText = 'Your case has potential but can be strengthened with additional evidence.';
    } else {
        strengthLevel = 'WEAK';
        strengthColor = 'error';
        strengthIcon = 'fa-exclamation-triangle';
        actionText = 'Your case needs significant improvement before proceeding.';
    }

    // Build key factors list
    const keyFactors = [];
    if (data.strengths && data.strengths.length > 0) {
        keyFactors.push(`${data.strengths.length} strength${data.strengths.length > 1 ? 's' : ''} identified`);
    }
    if (data.weaknesses && data.weaknesses.length > 0) {
        keyFactors.push(`${data.weaknesses.length} weakness${data.weaknesses.length > 1 ? 'es' : ''} detected`);
    }
    if (data.issues && data.issues.length > 0) {
        keyFactors.push(`${data.issues.length} critical issue${data.issues.length > 1 ? 's' : ''} found`);
    }

    const summaryHTML = `
        <div class="case-summary-card case-${strengthColor}" style="background: linear-gradient(135deg, var(--${strengthColor}-50) 0%, white 100%); border: 2px solid var(--${strengthColor}-500); border-radius: var(--radius-xl); padding: 2rem; margin-bottom: 2rem; box-shadow: var(--shadow-lg);">
            <div style="display: flex; align-items: start; gap: 1.5rem;">
                <div class="summary-icon" style="width: 64px; height: 64px; background: var(--${strengthColor}-100); border-radius: var(--radius-lg); display: flex; align-items: center; justify-content: center; flex-shrink: 0;">
                    <i class="fas ${strengthIcon}" style="font-size: 2rem; color: var(--${strengthColor}-600);"></i>
                </div>
                <div style="flex: 1;">
                    <div style="display: flex; align-items: center; gap: 0.75rem; margin-bottom: 0.5rem;">
                        <h3 style="margin: 0; font-size: var(--font-size-2xl); font-weight: 700; color: var(--gray-900);">
                            ${strengthLevel} Case
                        </h3>
                        <span style="background: var(--${strengthColor}-100); color: var(--${strengthColor}-700); padding: 0.25rem 0.75rem; border-radius: var(--radius-full); font-size: var(--font-size-sm); font-weight: 600;">
                            ${score.toFixed(1)}/100
                        </span>
                    </div>
                    <p style="color: var(--gray-700); font-size: var(--font-size-base); line-height: 1.6; margin-bottom: 1rem;">
                        ${actionText}
                    </p>
                    ${keyFactors.length > 0 ? `
                        <div style="display: flex; flex-wrap: wrap; gap: 0.75rem;">
                            ${keyFactors.map(factor => `
                                <span style="background: white; padding: 0.5rem 1rem; border-radius: var(--radius-md); font-size: var(--font-size-sm); color: var(--gray-700); border: 1px solid var(--gray-200);">
                                    <i class="fas fa-check-circle" style="color: var(--${strengthColor}-500); margin-right: 0.25rem;"></i>
                                    ${factor}
                                </span>
                            `).join('')}
                        </div>
                    ` : ''}
                </div>
            </div>
        </div>
    `;

    // Insert at the beginning of the container
    summaryContainer.insertAdjacentHTML('afterbegin', summaryHTML);
}

// ═══════════════════════════════════════════════════════════════════════════
// 🔥 UX ENHANCEMENT: SCORE EXPLANATION SYSTEM
// ═══════════════════════════════════════════════════════════════════════════

function renderScoreExplanation(data) {
    const score = data.score || 0;
    const explanationContainer = document.getElementById('scoreExplanation');

    if (!explanationContainer) return;

    let explanation = '';
    let missingElements = [];
    let detectedWeaknesses = [];

    // Analyze what's missing or weak
    if (score < 50) {
        explanation = '<strong>Low Score Analysis:</strong> Your case received a low score due to the following factors:';

        // Check for missing critical elements
        if (!data.strengths || data.strengths.length === 0) {
            missingElements.push('No strong legal arguments detected');
        }

        if (data.issues && data.issues.length > 3) {
            missingElements.push(`${data.issues.length} critical issues identified`);
        }

        if (data.weaknesses && data.weaknesses.length > 0) {
            data.weaknesses.forEach(w => {
                const text = typeof w === 'string' ? w : (w.weakness || w.title || w.description);
                if (text) detectedWeaknesses.push(text);
            });
        }

        // Check for missing evidence via structured object
        if (!isTruthy(formData.notice?.notice_sent)) {
            missingElements.push('Legal notice not sent (mandatory requirement)');
        }

        if (!isTruthy(formData.evidence?.dishonour_memo) && !isTruthy(formData.evidence?.agreement_documents)) {
            missingElements.push('No supporting documents provided');
        }

        if (!formData.transaction?.transaction_date) {
            missingElements.push('Incomplete timeline information');
        }

    } else if (score < 70) {
        explanation = '<strong>Moderate Score Analysis:</strong> Your case shows some merit but has areas for improvement:';

        if (data.weaknesses && data.weaknesses.length > 0) {
            data.weaknesses.slice(0, 3).forEach(w => {
                const text = typeof w === 'string' ? w : (w.weakness || w.title || w.description);
                if (text) detectedWeaknesses.push(text);
            });
        }

    } else {
        explanation = '<strong>Strong Score Analysis:</strong> Your case demonstrates solid legal merit with:';
        explanationContainer.innerHTML = `
            <div class="insight-panel insight-success">
                <div class="insight-header">
                    <i class="fas fa-check-circle"></i>
                    <h4>Why This Score?</h4>
                </div>
                <p>${explanation}</p>
                <ul class="insight-list">
                    ${(data.strengths || []).slice(0, 3).map(s => {
            const text = typeof s === 'string' ? s : (s.strength || s.title || s.description);
            return `<li><i class="fas fa-check"></i> ${text}</li>`;
        }).join('')}
                </ul>
            </div>
        `;
        return;
    }

    // Render low/moderate score explanation
    explanationContainer.innerHTML = `
        <div class="insight-panel ${score < 50 ? 'insight-danger' : 'insight-warning'}">
            <div class="insight-header">
                <i class="fas fa-info-circle"></i>
                <h4>Why This Score?</h4>
            </div>
            <p>${explanation}</p>
            
            ${missingElements.length > 0 ? `
                <div class="insight-section">
                    <h5><i class="fas fa-exclamation-triangle"></i> Missing Critical Elements:</h5>
                    <ul class="insight-list">
                        ${missingElements.map(item => `<li><i class="fas fa-times"></i> ${item}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
            
            ${detectedWeaknesses.length > 0 ? `
                <div class="insight-section">
                    <h5><i class="fas fa-flag"></i> Detected Weaknesses:</h5>
                    <ul class="insight-list">
                        ${detectedWeaknesses.map(item => `<li><i class="fas fa-arrow-right"></i> ${item}</li>`).join('')}
                    </ul>
                </div>
            ` : ''}
        </div>
    `;
}

// ═══════════════════════════════════════════════════════════════════════════
// 🔥 STEP 5: IMPROVEMENT SUGGESTIONS
// ═══════════════════════════════════════════════════════════════════════════

function renderImprovementSuggestions(data) {
    const score = data.score || 0;
    const suggestionsContainer = document.getElementById('improvementSuggestions');

    if (!suggestionsContainer) return;

    if (score >= 80) {
        suggestionsContainer.innerHTML = `
            <div class="suggestions-panel suggestions-minimal">
                <p style="color: var(--success-700); font-weight: 500;">
                    <i class="fas fa-check-circle"></i> Your case is already strong. Consider reviewing the recommended actions to proceed.
                </p>
            </div>
        `;
        return;
    }

    const suggestions = [];

    // Analyze what can be improved
    if (!isTruthy(formData.notice?.notice_sent)) {
        suggestions.push({
            icon: 'fa-file-alt',
            title: 'Send Legal Notice',
            description: 'Issue a legal notice within 30 days of cheque dishonour. This is a mandatory legal requirement.',
            impact: 'High Impact',
            color: 'error'
        });
    }

    if (!isTruthy(formData.dishonour?.bank_memo_received) && !isTruthy(formData.evidence?.dishonour_memo)) {
        suggestions.push({
            icon: 'fa-university',
            title: 'Obtain Bank Memo',
            description: 'Get the official bank memo showing "Insufficient Funds" or dishonour reason.',
            impact: 'High Impact',
            color: 'error'
        });
    }

    if (!isTruthy(formData.evidence?.agreement_documents) && !formData.transaction?.transaction_date) {
        suggestions.push({
            icon: 'fa-receipt',
            title: 'Gather Transaction Proof',
            description: 'Collect invoices, agreements, or receipts proving the underlying debt.',
            impact: 'Medium Impact',
            color: 'warning'
        });
    }

    if (data.weaknesses && data.weaknesses.length > 0) {
        suggestions.push({
            icon: 'fa-shield-alt',
            title: 'Address Identified Weaknesses',
            description: `${data.weaknesses.length} weakness(es) found in your case. Review the weaknesses section for details.`,
            impact: 'Medium Impact',
            color: 'warning'
        });
    }

    if (!isTruthy(formData.evidence?.witness_available)) {
        suggestions.push({
            icon: 'fa-users',
            title: 'Consider Witness Statements',
            description: 'Gather witness statements or affidavits if available to strengthen your case.',
            impact: 'Low Impact',
            color: 'info'
        });
    }

    // Use backend suggestions if available
    if (data.recommended_actions && data.recommended_actions.length > 0) {
        // Backend provides specific actions
    }

    if (suggestions.length === 0) {
        suggestionsContainer.innerHTML = `
            <div class="suggestions-panel">
                <p style="color: var(--gray-600);">
                    <i class="fas fa-info-circle"></i> No specific improvements needed at this time.
                </p>
            </div>
        `;
        return;
    }

    suggestionsContainer.innerHTML = `
        <div class="suggestions-panel">
            <div class="suggestions-header">
                <i class="fas fa-lightbulb"></i>
                <h4>How to Improve This Case</h4>
            </div>
            <div class="suggestions-grid">
                ${suggestions.map(sug => `
                    <div class="suggestion-card suggestion-${sug.color}">
                        <div class="suggestion-icon">
                            <i class="fas ${sug.icon}"></i>
                        </div>
                        <div class="suggestion-content">
                            <h5>${sug.title}</h5>
                            <p>${sug.description}</p>
                            <span class="suggestion-impact impact-${sug.color}">${sug.impact}</span>
                        </div>
                    </div>
                `).join('')}
            </div>
        </div>
    `;
}

// ═══════════════════════════════════════════════════════════════════════════
// 🔥 STEP 7: CONFIDENCE INDICATOR
// ═══════════════════════════════════════════════════════════════════════════

function renderConfidenceIndicator(data) {
    const confidenceContainer = document.getElementById('confidenceIndicator');

    if (!confidenceContainer) return;

    // Calculate confidence based on data completeness
    const validation = validateCaseCompleteness();
    const dataCompleteness = validation.dataCompleteness;
    const score = data.score || 0;

    let confidenceLevel = 'LOW';
    let confidenceColor = 'error';
    let confidenceIcon = 'fa-exclamation-triangle';
    let confidenceText = '';

    // Determine confidence level
    if (dataCompleteness >= 70 && score > 0) {
        confidenceLevel = 'HIGH';
        confidenceColor = 'success';
        confidenceIcon = 'fa-check-circle';
        confidenceText = 'The analysis is based on comprehensive case data with all critical information provided.';
    } else if (dataCompleteness >= 40) {
        confidenceLevel = 'MEDIUM';
        confidenceColor = 'warning';
        confidenceIcon = 'fa-info-circle';
        confidenceText = 'The analysis is based on moderate case data. Adding more information may improve accuracy.';
    } else {
        confidenceLevel = 'LOW';
        confidenceColor = 'error';
        confidenceIcon = 'fa-exclamation-triangle';
        confidenceText = 'The analysis is based on limited case data. Results may not be fully accurate.';
    }

    confidenceContainer.innerHTML = `
        <div class="confidence-panel confidence-${confidenceColor}">
            <div class="confidence-badge-large">
                <i class="fas ${confidenceIcon}"></i>
                <div>
                    <span class="confidence-label">Analysis Confidence</span>
                    <span class="confidence-value">${confidenceLevel}</span>
                </div>
            </div>
            <div class="confidence-meter">
                <div class="confidence-meter-fill confidence-${confidenceColor}" style="width: ${dataCompleteness}%"></div>
            </div>
            <p class="confidence-description">${confidenceText}</p>
            <div class="confidence-stats">
                <div class="confidence-stat">
                    <span class="stat-value">${dataCompleteness}%</span>
                    <span class="stat-label">Data Completeness</span>
                </div>
                <div class="confidence-stat">
                    <span class="stat-value">${(data.strengths || []).length + (data.issues || []).length}</span>
                    <span class="stat-label">Factors Analyzed</span>
                </div>
            </div>
        </div>
    `;
}

// TASK 4: GENERIC LIST RENDERER WITH IMPROVED EMPTY STATES
// RENDER LIST function moved to utility section (see below)

function getEmptyStateHint(elementId) {
    const hints = {
        'issuesList': 'Improve your case inputs to help identify potential issues',
        'strengthsList': 'Add more evidence and documentation to discover case strengths',
        'weaknessesList': 'Comprehensive case data helps identify areas for improvement',
        'timelineList': 'Provide transaction dates and timelines for better chronology',
        'actionsList': 'Complete your case details to receive actionable recommendations',
        'contradictionsList': 'Full case information enables contradiction detection',
        'strategyList': 'Enhanced case data will generate better legal strategies'
    };

    return hints[elementId] || 'Add more case details for better analysis';
}

function mapVerdict(v) {
    const map = {
        VERY_WEAK: "Weak Case",
        WEAK: "Weak Case",
        MODERATE: "Moderate Case",
        STRONG: "Strong Case"
    };
    return map[v] || v || "Unknown";
}

function showResults() {
    hideAllScreens();
    document.getElementById('resultsScreen').classList.remove('hidden');
    switchResultTab('overview');

    // 🔥 STEP 5 FIX: ALWAYS render from window.caseData
    if (window.caseData && window.caseData.score !== undefined) {
        console.log("🔥 Re-rendering full report from window.caseData");
        renderFullReport(window.caseData);
    } else {
        console.warn("⚠️ No case data available in window.caseData");
        showToast('No case data available. Please analyze a case first.', 'warning');
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function getVerdictDescription(score) {
    if (score >= 70) return 'Your case has strong legal merit and good chances of success';
    if (score >= 40) return 'Your case has moderate strength with some concerns to address';
    return 'Your case has significant weaknesses that need attention';
}

function animateScore(targetScore) {
    const scoreElement = document.getElementById('scoreNumber');
    const progressCircle = document.getElementById('scoreProgress');
    const circumference = 2 * Math.PI * 90;

    let currentScore = 0;
    const duration = 2000;
    const increment = targetScore / (duration / 16);

    const animate = () => {
        currentScore += increment;
        if (currentScore >= targetScore) currentScore = targetScore;

        scoreElement.textContent = Math.round(currentScore);
        progressCircle.style.strokeDashoffset = circumference - (currentScore / 100) * circumference;

        if (currentScore < targetScore) requestAnimationFrame(animate);
    };

    progressCircle.style.strokeDasharray = circumference;
    progressCircle.style.strokeDashoffset = circumference;
    progressCircle.style.transition = 'stroke-dashoffset 0.1s linear';
    animate();
}

function displayIssues(issues) {
    const container = document.getElementById('issuesList');
    if (!issues || issues.length === 0) {
        container.innerHTML = '<p style="color: var(--gray-500);">No critical issues detected</p>';
        return;
    }
    container.innerHTML = issues.map(issue => {
        const issueText = typeof issue === 'string' ? issue : (issue.issue || issue.title || issue.description || 'Issue detected');
        const description = typeof issue === 'object' ? (issue.description || issue.impact || '') : '';
        const severity = typeof issue === 'object' ? (issue.severity || 'Medium') : 'Medium';
        return `
            <div class="issue-item">
                <i class="fas fa-exclamation-circle"></i>
                <div style="flex: 1;">
                    <strong>${issueText}</strong>
                    ${severity ? `<span class="badge badge-${severity.toLowerCase()}" style="margin-left: 0.5rem; font-size: 0.75rem; padding: 0.125rem 0.5rem; border-radius: 0.25rem; background: var(--warning-50); color: var(--warning-700);">${severity}</span>` : ''}
                    ${description ? `<p style="margin-top: 0.5rem; font-size: 0.875rem; color: var(--gray-600);">${description}</p>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

function displayStrengths(strengths) {
    const container = document.getElementById('strengthsList');
    if (!strengths || strengths.length === 0) {
        container.innerHTML = '<p style="color: var(--gray-500);">Building case strengths...</p>';
        return;
    }
    container.innerHTML = strengths.map(strength => {
        const strengthText = typeof strength === 'string' ? strength : (strength.strength || strength.title || strength.description || 'Strength found');
        const description = typeof strength === 'object' ? (strength.description || strength.explanation || '') : '';
        const impact = typeof strength === 'object' ? (strength.impact || '') : '';
        return `
            <div class="strength-item">
                <i class="fas fa-check-circle"></i>
                <div style="flex: 1;">
                    <strong>${strengthText}</strong>
                    ${description ? `<p style="margin-top: 0.5rem; font-size: 0.875rem; color: var(--gray-600);">${description}</p>` : ''}
                    ${impact ? `<p style="margin-top: 0.25rem; font-size: 0.75rem; color: var(--success-600);"><i class="fas fa-arrow-up"></i> Impact: ${impact}</p>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// NEW FUNCTION: Display Weaknesses
function displayWeaknesses(weaknesses) {
    const container = document.getElementById('weaknessesList');
    if (!container) return; // Skip if element doesn't exist

    if (!weaknesses || weaknesses.length === 0) {
        container.innerHTML = '<p style="color: var(--gray-500);">No significant weaknesses identified</p>';
        return;
    }
    container.innerHTML = weaknesses.map(weakness => {
        const weaknessText = typeof weakness === 'string' ? weakness : (weakness.weakness || weakness.title || weakness.description || 'Weakness identified');
        const description = typeof weakness === 'object' ? (weakness.description || weakness.impact || '') : '';
        const severity = typeof weakness === 'object' ? (weakness.severity || 'Medium') : 'Medium';
        return `
            <div class="weakness-item" style="padding: 1rem; border-left: 3px solid var(--warning-500); background: var(--warning-50); border-radius: 0.5rem; margin-bottom: 0.75rem;">
                <div style="display: flex; align-items: start; gap: 0.75rem;">
                    <i class="fas fa-exclamation-triangle" style="color: var(--warning-600); margin-top: 0.25rem;"></i>
                    <div style="flex: 1;">
                        <strong style="color: var(--gray-900);">${weaknessText}</strong>
                        <span class="badge" style="margin-left: 0.5rem; font-size: 0.75rem; padding: 0.125rem 0.5rem; border-radius: 0.25rem; background: var(--warning-100); color: var(--warning-800);">${severity}</span>
                        ${description ? `<p style="margin-top: 0.5rem; font-size: 0.875rem; color: var(--gray-700);">${description}</p>` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

// NEW FUNCTION: Display Timeline
function displayTimeline(timeline) {
    const container = document.getElementById('timelineList');
    if (!container) return; // Skip if element doesn't exist

    if (!timeline || timeline.length === 0) {
        container.innerHTML = '<p style="color: var(--gray-500);">No timeline events generated</p>';
        return;
    }
    container.innerHTML = timeline.map((event, index) => {
        const eventText = typeof event === 'string' ? event : (event.event || event.title || event.action || 'Timeline event');
        const date = typeof event === 'object' ? (event.date || event.deadline || '') : '';
        const description = typeof event === 'object' ? (event.description || event.details || '') : '';
        const status = typeof event === 'object' ? (event.status || 'pending') : 'pending';

        return `
            <div class="timeline-item" style="position: relative; padding-left: 2rem; padding-bottom: 1.5rem; border-left: 2px solid var(--gray-300);">
                <div class="timeline-marker" style="position: absolute; left: -0.5rem; top: 0; width: 1rem; height: 1rem; border-radius: 50%; background: ${status === 'completed' ? 'var(--success-500)' : 'var(--primary-500)'}; border: 3px solid white; box-shadow: 0 0 0 2px var(--gray-200);"></div>
                <div class="timeline-content" style="background: white; padding: 1rem; border-radius: 0.5rem; box-shadow: var(--shadow-sm);">
                    <div style="display: flex; justify-content: space-between; align-items: start; margin-bottom: 0.5rem;">
                        <strong style="color: var(--gray-900); font-size: 0.95rem;">${eventText}</strong>
                        ${date ? `<span style="font-size: 0.75rem; color: var(--gray-600); white-space: nowrap; margin-left: 1rem;"><i class="fas fa-calendar"></i> ${date}</span>` : ''}
                    </div>
                    ${description ? `<p style="font-size: 0.875rem; color: var(--gray-600); margin-top: 0.5rem;">${description}</p>` : ''}
                    ${status ? `<span class="badge" style="display: inline-block; margin-top: 0.5rem; font-size: 0.7rem; padding: 0.125rem 0.5rem; border-radius: 0.25rem; background: ${status === 'completed' ? 'var(--success-100)' : 'var(--primary-100)'}; color: ${status === 'completed' ? 'var(--success-700)' : 'var(--primary-700)'};">${status}</span>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

// NEW FUNCTION: Display Strategy
function displayStrategy(strategy) {
    const container = document.getElementById('strategyContent');
    if (!container) return; // Skip if element doesn't exist

    if (!strategy || (typeof strategy === 'string' && !strategy.trim()) || (Array.isArray(strategy) && strategy.length === 0)) {
        container.innerHTML = '<p style="color: var(--gray-500);">No specific strategy recommendations available</p>';
        return;
    }

    // Handle if strategy is a string
    if (typeof strategy === 'string') {
        container.innerHTML = `<div style="background: var(--primary-50); padding: 1.5rem; border-radius: 0.75rem; border-left: 4px solid var(--primary-500);"><p style="color: var(--gray-800); line-height: 1.6; white-space: pre-wrap;">${strategy}</p></div>`;
        return;
    }

    // Handle if strategy is an array of strategies
    if (Array.isArray(strategy)) {
        container.innerHTML = strategy.map((strat, index) => {
            const stratText = typeof strat === 'string' ? strat : (strat.strategy || strat.recommendation || strat.title || 'Strategy recommendation');
            const description = typeof strat === 'object' ? (strat.description || strat.details || '') : '';
            const priority = typeof strat === 'object' ? (strat.priority || 'medium') : 'medium';
            return `
                <div style="background: var(--primary-50); padding: 1.25rem; border-radius: 0.75rem; margin-bottom: 1rem; border-left: 4px solid var(--primary-500);">
                    <div style="display: flex; align-items: start; gap: 0.75rem;">
                        <span style="flex-shrink: 0; width: 1.5rem; height: 1.5rem; display: flex; align-items: center; justify-content: center; background: var(--primary-500); color: white; border-radius: 50%; font-weight: 600; font-size: 0.875rem;">${index + 1}</span>
                        <div style="flex: 1;">
                            <strong style="color: var(--gray-900); display: block; margin-bottom: 0.5rem;">${stratText}</strong>
                            <span class="badge" style="font-size: 0.7rem; padding: 0.125rem 0.5rem; border-radius: 0.25rem; background: ${priority === 'high' ? 'var(--error-100)' : priority === 'low' ? 'var(--success-100)' : 'var(--warning-100)'}; color: ${priority === 'high' ? 'var(--error-700)' : priority === 'low' ? 'var(--success-700)' : 'var(--warning-700)'};">Priority: ${priority}</span>
                            ${description ? `<p style="margin-top: 0.75rem; font-size: 0.875rem; color: var(--gray-700); line-height: 1.6;">${description}</p>` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
        return;
    }

    // Handle if strategy is an object
    if (typeof strategy === 'object') {
        const stratText = strategy.strategy || strategy.recommendation || strategy.summary || 'Strategy recommendation';
        const details = strategy.details || strategy.description || '';
        container.innerHTML = `
            <div style="background: var(--primary-50); padding: 1.5rem; border-radius: 0.75rem; border-left: 4px solid var(--primary-500);">
                <strong style="color: var(--gray-900); display: block; margin-bottom: 1rem; font-size: 1.05rem;">${stratText}</strong>
                ${details ? `<p style="color: var(--gray-700); line-height: 1.6; white-space: pre-wrap;">${details}</p>` : ''}
            </div>
        `;
    }
}

function displayDefences(defences) {
    const container = document.getElementById('defencesList');
    if (!defences || defences.length === 0) {
        container.innerHTML = '<p style="color: var(--gray-500);">No defences simulated</p>';
        return;
    }
    container.innerHTML = defences.map(defence => {
        const argument = defence.argument || defence.defence || defence.title || 'Defence Strategy';
        const strength = (defence.strength || 'Medium').toLowerCase();
        const probability = defence.success_probability || defence.probability || 50;
        return `
            <div class="defence-item">
                <div class="defence-header">
                    <h4>${argument}</h4>
                    <div style="display: flex; align-items: center; gap: 1rem;">
                        <span class="defence-strength ${strength}">${defence.strength || 'Medium'}</span>
                        <div class="defence-probability">${probability}%</div>
                    </div>
                </div>
                ${defence.trigger_reason ? `<p class="defence-details"><strong>Triggered by:</strong> ${defence.trigger_reason}</p>` : ''}
                ${defence.rebuttal ? `<div class="defence-rebuttal"><strong>Counter Strategy:</strong> ${defence.rebuttal}</div>` : ''}
            </div>
        `;
    }).join('');
}

function displaySemanticAnalysis(semantic) {
    const container = document.getElementById('semanticAnalysis');
    const concepts = semantic.concepts_detected || [];
    if (concepts.length === 0) {
        container.innerHTML = '<p style="color: var(--gray-500);">No specific legal concepts detected</p>';
        return;
    }
    container.innerHTML = concepts.map(concept => `
        <div class="concept-item">
            <div class="concept-header">
                <h4>${(concept.concept || 'Legal Concept').replace(/_/g, ' ')}</h4>
                <span class="concept-confidence">${Math.round((concept.confidence || 0) * 100)}%</span>
            </div>
            ${concept.matched_phrases ? `<p class="concept-phrases">Matched: ${concept.matched_phrases.join(', ')}</p>` : ''}
        </div>
    `).join('');
}

function displayActions(actions) {
    const container = document.getElementById('actionsList');
    if (!actions || actions.length === 0) {
        container.innerHTML = '<p style="color: var(--gray-500);">No immediate actions required</p>';
        return;
    }
    container.innerHTML = actions.map(action => {
        const actionText = typeof action === 'string' ? action : (action.action || action.title || action.description || 'Action required');
        const priority = typeof action === 'object' ? (action.priority || 'medium') : 'medium';
        const description = typeof action === 'object' ? action.description : '';
        const deadline = typeof action === 'object' ? action.deadline : '';
        return `
            <div class="action-item">
                <span class="action-priority ${priority.toLowerCase()}">${priority}</span>
                <div>
                    <strong>${actionText}</strong>
                    ${description ? `<p style="margin-top: 0.5rem; font-size: 0.875rem;">${description}</p>` : ''}
                    ${deadline ? `<p style="margin-top: 0.25rem; font-size: 0.75rem; color: var(--gray-600);">Deadline: ${deadline}</p>` : ''}
                </div>
            </div>
        `;
    }).join('');
}

function displayReasoningTrace(trace) {
    const container = document.getElementById('reasoningList');
    if (!container) return;

    if (!trace || trace.length === 0) {
        container.innerHTML = '<p style="color: var(--gray-500);">No reasoning trace available</p>';
        return;
    }
    container.innerHTML = trace.map(step => `<div class="reasoning-step">${step}</div>`).join('');
}

// ═══════════════════════════════════════════════════════════════════════════
// RENDER DECISION PANEL - Shows recommended action and next steps
// ═══════════════════════════════════════════════════════════════════════════

function renderDecisionPanel(decision) {
    const actionsContainer = document.getElementById('actionsList');
    if (!actionsContainer) return;

    const label = decision.decision_label || decision.recommended_action || "Review Case";
    const detail = decision.detail || "Based on the analysis, please review the recommendations below.";
    const nextSteps = decision.next_steps || [];
    const topRisks = decision.top_3_risks || [];

    // Determine action type for styling
    const actionType = decision.recommended_action || "REVIEW";
    let actionClass = "info";
    let actionIcon = "fa-info-circle";

    if (actionType.includes("FILE_COMPLAINT") || actionType.includes("FILE")) {
        actionClass = "success";
        actionIcon = "fa-check-circle";
    } else if (actionType.includes("SEND_NOTICE") || actionType.includes("NOTICE")) {
        actionClass = "warning";
        actionIcon = "fa-exclamation-triangle";
    } else if (actionType.includes("HIGH_RISK") || actionType.includes("DEFEND")) {
        actionClass = "error";
        actionIcon = "fa-times-circle";
    } else if (actionType.includes("SETTLEMENT")) {
        actionClass = "warning";
        actionIcon = "fa-handshake";
    } else if (actionType.includes("FIX")) {
        actionClass = "warning";
        actionIcon = "fa-wrench";
    }

    let html = `
        <div class="decision-panel decision-${actionClass}">
            <div class="decision-header">
                <div class="decision-icon">
                    <i class="fas ${actionIcon}"></i>
                </div>
                <div class="decision-title-area">
                    <h4>${label}</h4>
                    <p>${detail}</p>
                </div>
            </div>
    `;

    // Add top risks if any
    if (topRisks.length > 0) {
        html += `
            <div class="decision-risks">
                <h5><i class="fas fa-flag"></i> Top Identified Risks:</h5>
                <ul>
                    ${topRisks.map(risk => {
            const riskText = typeof risk === 'string' ? risk : (risk.risk || risk.title || 'Risk identified');
            const severity = typeof risk === 'object' ? (risk.severity || 'MEDIUM') : 'MEDIUM';
            return `<li class="risk-item risk-${severity.toLowerCase()}">${riskText}</li>`;
        }).join('')}
                </ul>
            </div>
        `;
    }

    // Add next steps
    if (nextSteps.length > 0) {
        html += `
            <div class="decision-steps">
                <h5><i class="fas fa-list-ol"></i> Next Steps:</h5>
                <ol>
                    ${nextSteps.map(step => `<li>${step}</li>`).join('')}
                </ol>
            </div>
        `;
    }

    html += `</div>`;
    actionsContainer.innerHTML = html;
}

function toggleReasoning() {
    const trace = document.getElementById('reasoningTrace');
    const header = document.querySelector('.collapsible-header');
    trace.classList.toggle('hidden');
    header.classList.toggle('open');
}

function backToResults() {
    hideAllScreens();
    document.getElementById('resultsScreen').classList.remove('hidden');
}

function startNewCase() {
    if (confirm('Start a new case? Your current analysis will remain in recent cases.')) {
        startCaseAnalysis();
    }
}

// ═══════════════════════════════════════════════════════════════════════════
// DRAFT FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════

function copyDraftFromPreview() {
    const textarea = document.getElementById('draftPreviewContent');
    textarea.select();
    document.execCommand('copy');
    showToast('Draft copied to clipboard successfully!', 'success', 'Copied');
}

function downloadDraftText() {
    const content = document.getElementById('draftPreviewContent').value;
    if (!content || content.trim() === '') {
        showToast('No draft available to download', 'warning');
        return;
    }
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `legal_draft_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Draft downloaded successfully!', 'success', 'Download Complete');
}

function openDraftEditor() {
    openDraftGeneratorScreen('results');
}

function showDraftGenerator() {
    openDraftGeneratorScreen('results');
}

function generateDraft() {
    openDraftGeneratorScreen('dashboard');
}

function copyDraft() {
    const textarea = document.getElementById('draftContent');
    textarea.select();
    document.execCommand('copy');
    showToast('Draft copied to clipboard successfully!', 'success', 'Copied');
}

function downloadDraft() {
    const content = document.getElementById('draftContent').value;
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `legal_draft_${Date.now()}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    showToast('Draft downloaded successfully!', 'success', 'Download Complete');
}

function printDraft() {
    window.print();
}

// ═══════════════════════════════════════════════════════════════════════════
// REPORT FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════

function viewFullReport() {
    // 🔥 STEP 7: BUTTON SAFETY
    if (!window.caseData || !window.caseData.score) {
        showToast('Analyze case first', 'warning');
        return;
    }

    // Build report content
    const report = `
CASE ANALYSIS REPORT

Score: ${window.caseData.score || 'N/A'}/100
Verdict: ${mapVerdict(window.caseData.verdict) || 'N/A'}
Defence Risk: ${window.caseData.risk_level || window.caseData.defence_risk || 'N/A'}

CRITICAL ISSUES:
${(window.caseData.issues || []).map((issue, i) => `${i + 1}. ${typeof issue === 'string' ? issue : issue.issue || issue.title || 'Issue detected'}`).join('\n')}

STRENGTHS:
${(window.caseData.strengths || []).map((strength, i) => `${i + 1}. ${typeof strength === 'string' ? strength : strength.strength || strength.title || 'Strength identified'}`).join('\n')}

NEXT ACTIONS:
${(window.caseData.recommended_actions || window.caseData.next_actions || []).map((action, i) => `${i + 1}. ${typeof action === 'string' ? action : action.action || action.title || 'Action required'}`).join('\n')}
`;

    // Display in report content area
    const reportContentEl = document.getElementById('reportContent');
    if (reportContentEl) {
        reportContentEl.innerHTML = `<pre style="white-space: pre-wrap; font-family: inherit;">${report}</pre>`;
    }

    // Switch to analysis tab
    switchResultTab('analysis');
}

function renderReportContent() {
    const container = document.getElementById('reportContent');
    container.innerHTML = `
        ${renderReportSection('Executive Summary', renderExecutiveSummary())}
        ${renderReportSection('Case Details', renderCaseDetails())}
        ${renderReportSection('Parties', renderParties())}
        ${renderReportSection('Transaction Details', renderTransaction())}
        ${renderReportSection('Cheque Information', renderCheque())}
        ${renderReportSection('Dishonour Details', renderDishonour())}
        ${renderReportSection('Legal Notice', renderNotice())}
        ${renderReportSection('Evidence Assessment', renderEvidence())}
        ${renderReportSection('Legal Analysis', renderAnalysis())}
        ${renderReportSection('Defence Simulation', renderDefenceSimulation())}
        ${renderReportSection('Recommended Actions', renderRecommendedActions())}
    `;
}

function renderReportSection(title, content) {
    return `
        <div class="report-section">
            <h3>${title}</h3>
            ${content}
        </div>
    `;
}

function renderExecutiveSummary() {
    // Use window.caseData instead of analysisResult
    const data = window.caseData || {};
    const verdict = mapVerdict(data.verdict);
    const score = data.score ?? 0;
    const defenceRisk = data.defence_risk || data.risk_level || 'N/A';
    const issuesCount = (data.issues || []).length;

    return `
        <table class="report-table">
            <tr><th>Verdict</th><td>${verdict}</td></tr>
            <tr><th>Case Score</th><td>${score}/100</td></tr>
            <tr><th>Defence Risk</th><td>${defenceRisk}</td></tr>
            <tr><th>Critical Issues</th><td>${issuesCount}</td></tr>
        </table>
    `;
}

function renderCaseDetails() { return renderDataTable(formData.case_identity || {}); }
function renderParties() { return renderDataTable(formData.parties || {}); }
function renderTransaction() { return renderDataTable(formData.transaction || {}); }
function renderCheque() { return renderDataTable(formData.cheque || {}); }
function renderDishonour() { return renderDataTable(formData.dishonour || {}); }
function renderNotice() { return renderDataTable(formData.notice || {}); }
function renderEvidence() { return renderDataTable(formData.evidence || {}); }

function renderAnalysis() {
    // Use window.caseData instead of analysisResult
    const data = window.caseData || {};
    const narrative = data.legal_analysis || data.narrative || 'No analysis available';
    return `<p>${narrative}</p>`;
}

function renderDefenceSimulation() {
    // Use window.caseData instead of analysisResult
    const data = window.caseData || {};
    const defences = data.top_defences || data.defences_ranked || data.predicted_defences || [];
    if (defences.length === 0) return '<p>No defences simulated</p>';
    return `<ul>${defences.map(d => `
        <li><strong>${d.argument || d.defence}</strong> (${d.strength || 'Medium'} - ${d.success_probability || d.probability || 50}%)
        ${d.rebuttal ? `<br><em>Counter: ${d.rebuttal}</em>` : ''}</li>
    `).join('')}</ul>`;
}

function renderRecommendedActions() {
    // Use window.caseData instead of analysisResult
    const data = window.caseData || {};
    const actions = data.next_actions || data.recommended_actions || [];
    if (actions.length === 0) return '<p>No specific actions required at this time</p>';
    return `<ul>${actions.map(a => {
        const actionText = typeof a === 'string' ? a : (a.action || a.title || a);
        const description = typeof a === 'object' ? a.description : '';
        const deadline = typeof a === 'object' ? a.deadline : '';
        return `
            <li><strong>${actionText}</strong>
            ${description ? `<br>${description}` : ''}
            ${deadline ? `<br><em>Deadline: ${deadline}</em>` : ''}</li>
        `;
    }).join('')}</ul>`;
}

function renderDataTable(data) {
    if (!data || Object.keys(data).length === 0) return '<p>No data available</p>';
    return `<table class="report-table">${Object.entries(data).map(([key, value]) =>
        `<tr><th>${formatLabel(key)}</th><td>${value || 'N/A'}</td></tr>`
    ).join('')}</table>`;
}

function formatLabel(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}
function generateReport() {
    downloadPDF();
}

function escapeHTML(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

async function downloadPDF() {
    if (!window.caseData) {
        showToast('No case data available. Please analyze a case first.', 'warning');
        return;
    }

    showToast('Generating professional PDF report...', 'info');

    try {
        const response = await fetch(`${API_BASE_URL}/generate-pdf`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/pdf'
            },
            body: JSON.stringify(window.caseData)
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.error || 'Failed to generate PDF');
        }

        // Handle PDF blob response
        const blob = await response.blob();
        if (blob.size < 100) throw new Error('Received empty PDF from server');

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.style.display = 'none';
        a.href = url;
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);
        a.download = `JUDIQ_Report_${timestamp}.pdf`;
        document.body.appendChild(a);
        a.click();

        window.URL.revokeObjectURL(url);
        showToast('PDF report downloaded successfully!', 'success', 'Download Complete');

    } catch (error) {
        console.error('PDF Download Error:', error);
        showToast(`PDF Error: ${error.message}`, 'error', 'Download Failed');

        // Fallback to text download if PDF fails
        fallbackToTextDownload();
    }
}

function fallbackToTextDownload() {
    console.log('Initiating fallback text download...');
    const content = `JUDIQ AI CASE REPORT\nScore: ${window.caseData.score}/100\nVerdict: ${window.caseData.verdict}\n\nLegal Analysis:\n${window.caseData.legal_analysis}`;
    const blob = new Blob([content], { type: "text/plain" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `judiq_report_fallback.txt`;
    link.click();
}

// ═══════════════════════════════════════════════════════════════════════════
// 🔥 STEP 3: ENHANCED SAFE LIST RENDERER WITH SMART EMPTY STATES
// ═══════════════════════════════════════════════════════════════════════════

function renderList(id, items, fallback = "No data available") {
    const el = document.getElementById(id);
    if (!el) return; // Element doesn't exist

    if (!items || items.length === 0) {
        // Enhanced empty state with context-specific messaging
        const emptyStateMessages = {
            'issuesList': {
                icon: 'fa-check-circle',
                color: 'success',
                message: 'No critical issues detected',
                hint: 'This is a positive indicator for your case'
            },
            'contradictionsList': {
                icon: 'fa-check-circle',
                color: 'success',
                message: 'No contradictions detected',
                hint: 'Your case data is consistent'
            },
            'strengthsList': {
                icon: 'fa-info-circle',
                color: 'warning',
                message: 'No strong points identified',
                hint: 'Consider providing more evidence to strengthen your case'
            },
            'weaknessesList': {
                icon: 'fa-check-circle',
                color: 'success',
                message: 'No significant weaknesses identified',
                hint: 'Your case appears well-structured'
            },
            'timelineList': {
                icon: 'fa-calendar-times',
                color: 'gray',
                message: 'Timeline not available',
                hint: 'Provide dates for a complete timeline analysis'
            },
            'actionsList': {
                icon: 'fa-clipboard-check',
                color: 'info',
                message: 'No specific actions recommended',
                hint: 'Your case appears on track'
            },
            'strategyList': {
                icon: 'fa-lightbulb',
                color: 'gray',
                message: 'No strategy recommendations available',
                hint: 'Strategy will be generated based on your case details'
            }
        };

        const emptyState = emptyStateMessages[id] || {
            icon: 'fa-info-circle',
            color: 'gray',
            message: fallback,
            hint: ''
        };

        const colorMap = {
            'success': 'var(--success-500)',
            'warning': 'var(--warning-500)',
            'error': 'var(--error-500)',
            'info': 'var(--primary-500)',
            'gray': 'var(--gray-400)'
        };

        el.innerHTML = `
            <div class="empty-state-enhanced" style="text-align: center; padding: 2rem 1rem; background: var(--gray-50); border-radius: var(--radius-md); border: 2px dashed var(--gray-300);">
                <i class="fas ${emptyState.icon}" style="font-size: 2.5rem; color: ${colorMap[emptyState.color]}; margin-bottom: 1rem; opacity: 0.6;"></i>
                <p style="color: var(--gray-700); font-weight: 500; margin-bottom: 0.5rem; font-size: var(--font-size-base);">${emptyState.message}</p>
                ${emptyState.hint ? `<p style="color: var(--gray-500); font-size: var(--font-size-sm); font-style: italic;">${emptyState.hint}</p>` : ''}
            </div>
        `;
        return;
    }

    el.innerHTML = items.map((item, index) => {
        let displayText;

        if (typeof item === "string") {
            displayText = item;
        } else if (typeof item === "object" && item !== null) {
            // Extract text from common object structures
            displayText = item.issue || item.strength || item.weakness ||
                item.action || item.strategy || item.defence ||
                item.contradiction || item.text || item.description ||
                item.title || item.event || JSON.stringify(item, null, 2);
        } else {
            displayText = String(item);
        }

        return `
            <div class="list-item" style="padding: 0.75rem; margin-bottom: 0.5rem; background: var(--gray-50); border-radius: var(--radius-md); border-left: 3px solid var(--primary-500);">
                <strong style="color: var(--primary-600);">#${index + 1}</strong> ${escapeHTML(displayText)}
            </div>
        `;
    }).join("");
}

// ═══════════════════════════════════════════════════════════════════════════
// UTILITY FUNCTIONS
// ═══════════════════════════════════════════════════════════════════════════

function hideAllScreens() {
    const screens = [
        'loginScreen', 'registerScreen', 'roleScreen',
        'dashboardScreen', 'caseWizardScreen', 'resultsScreen',
        'draftScreen', 'reportScreen', 'draftGeneratorScreen'
    ];
    screens.forEach(screenId => {
        document.getElementById(screenId)?.classList.add('hidden');
    });
}

function viewReports() {
    if (window.caseData && window.caseData.score !== undefined) {
        viewFullReport();
    } else {
        showToast('No reports available. Please analyze a case first.', 'info', 'No Reports');
    }
}

function viewGuidance() {
    // 🔥 STEP 7: BUTTON SAFETY
    if (!window.caseData || !window.caseData.score) {
        showToast('Analyze case first', 'warning');
        return;
    }

    showResults();
    switchResultTab('strategy');
}

function viewStrategy() {
    // 🔥 STEP 7: BUTTON SAFETY
    if (!window.caseData || !window.caseData.score) {
        showToast('Analyze case first', 'warning');
        return;
    }

    showResults();
    switchResultTab('strategy');
}

function learnMode() {
    showToast('Learning mode coming soon! This will include educational case studies and tutorials.', 'info', 'Coming Soon');
}

// Make functions globally available
window.selectRole = selectRole;
window.logout = logout;
window.showDashboard = showDashboard;
window.startCaseAnalysis = startCaseAnalysis;
window.nextStep = nextStep;
window.previousStep = previousStep;
window.submitCase = submitCase;
window.showResults = showResults;
window.switchResultTab = switchResultTab;
window.toggleReasoning = toggleReasoning;
window.backToResults = backToResults;
window.startNewCase = startNewCase;
window.showDraftGenerator = showDraftGenerator;
window.generateDraft = generateDraft;
window.copyDraft = copyDraft;
window.copyDraftFromPreview = copyDraftFromPreview;
window.downloadDraft = downloadDraft;
window.downloadDraftText = downloadDraftText;
window.openDraftEditor = openDraftEditor;
window.printDraft = printDraft;
window.viewFullReport = viewFullReport;
window.downloadPDF = downloadPDF;
window.viewReports = viewReports;
window.viewGuidance = viewGuidance;
window.viewStrategy = viewStrategy;
window.learnMode = learnMode;
window.closeValidationModal = closeValidationModal;
window.closeWarningModal = closeWarningModal;
window.proceedWithWarning = proceedWithWarning;
// ═══════════════════════════════════════════════════════════════════════════
// 12-TYPE SECTION 138 DRAFT GENERATOR SYSTEM
// ═══════════════════════════════════════════════════════════════════════════

let activeDraftType = null;
let draftGenSource = 'dashboard';

const DRAFT_TYPES = [
    {
        id: 'demand_notice', number: 1, title: 'Legal Demand Notice', subtitle: 'Pre-Complaint',
        description: 'Sent within 30 days of cheque dishonour. Mandatory before filing.',
        icon: 'fa-envelope-open-text', color: '#0ea5e9',
        fields: [
            { name: 'complainant_name', label: 'Complainant Full Name', type: 'text', required: true, placeholder: 'e.g., Ramesh Kumar Sharma' },
            { name: 'complainant_address', label: 'Complainant Address', type: 'textarea', required: true, placeholder: 'Full postal address...' },
            { name: 'accused_name', label: 'Accused Full Name', type: 'text', required: true, placeholder: 'e.g., Suresh Mohan Gupta' },
            { name: 'accused_address', label: 'Accused Address', type: 'textarea', required: true, placeholder: 'Full postal address...' },
            { name: 'cheque_number', label: 'Cheque Number', type: 'text', required: true, placeholder: 'e.g., 012345' },
            { name: 'cheque_date', label: 'Cheque Date', type: 'date', required: true },
            { name: 'cheque_amount', label: 'Cheque Amount (₹)', type: 'number', required: true, placeholder: 'e.g., 250000' },
            { name: 'bank_name', label: 'Bank Name', type: 'text', required: true, placeholder: 'e.g., State Bank of India' },
            { name: 'branch_name', label: 'Branch Name', type: 'text', required: false, placeholder: 'e.g., Andheri West Branch' },
            { name: 'dishonour_date', label: 'Dishonour Date', type: 'date', required: true },
            { name: 'dishonour_reason', label: 'Reason for Dishonour', type: 'text', required: true, placeholder: 'e.g., Insufficient Funds' },
            { name: 'transaction_purpose', label: 'Purpose of Transaction / Underlying Debt', type: 'textarea', required: true, placeholder: 'Describe the loan/transaction for which the cheque was issued...' },
            { name: 'notice_date', label: 'Date of This Notice', type: 'date', required: true },
            { name: 'demand_days', label: 'Payment Demand Period', type: 'select', required: true, options: ['15 days', '30 days'] }
        ],
        generate: function (d) {
            return `LEGAL NOTICE UNDER SECTION 138 OF THE NEGOTIABLE INSTRUMENTS ACT, 1881

Date: ${formatDraftDate(d.notice_date)}

To,
${d.accused_name}
${d.accused_address}

Subject: Legal Notice under Section 138 of the Negotiable Instruments Act, 1881 for dishonour of Cheque No. ${d.cheque_number} dated ${formatDraftDate(d.cheque_date)} for Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/-

Sir/Madam,

Under the instructions and authority of my client, ${d.complainant_name}, residing at ${d.complainant_address} (hereinafter referred to as the "Complainant"), I hereby issue you this Legal Notice as under:

1. That my client and you had a business/financial relationship, wherein my client advanced a sum of Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/- (Rupees ${numberToWords(d.cheque_amount)} Only) to you towards ${d.transaction_purpose}.

2. That in discharge of your legally enforceable liability, you issued Cheque No. ${d.cheque_number} dated ${formatDraftDate(d.cheque_date)}, for a sum of Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/- (Rupees ${numberToWords(d.cheque_amount)} Only), drawn on ${d.bank_name}${d.branch_name ? ', ' + d.branch_name : ''}.

3. That the said cheque, when presented for encashment, was returned/dishonoured on ${formatDraftDate(d.dishonour_date)} with the bank's memo stating the reason: "${d.dishonour_reason}".

4. That the dishonour of the said cheque amounts to an offence under Section 138 of the Negotiable Instruments Act, 1881, as amended from time to time.

5. That you are, therefore, called upon to make payment of Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/- (Rupees ${numberToWords(d.cheque_amount)} Only) to my client within ${d.demand_days} from the receipt of this notice, failing which my client shall be constrained to initiate criminal as well as civil proceedings against you, at your cost and risk, including prosecution under Section 138 of the Negotiable Instruments Act, 1881, without any further notice.

6. That this Notice is being sent to you by Registered Post A.D. / Speed Post, in compliance with the statutory requirements of Section 138 of the NI Act.

Please treat this as a final opportunity to settle the matter amicably.

Yours faithfully,

${d.complainant_name}
(Complainant / Through Advocate)

Copy to: Complainant (for records)

Note: Date of receipt of this notice shall be the date of service for the purpose of computing the limitation period under Section 138 NI Act.`;
        }
    },
    {
        id: 'reply_notice', number: 2, title: 'Reply to Legal Notice', subtitle: 'Accused Side',
        description: 'Used by the defendant to deny liability or raise a legal defence.',
        icon: 'fa-reply', color: '#8b5cf6',
        fields: [
            { name: 'accused_name', label: 'Accused Full Name (Replying Party)', type: 'text', required: true },
            { name: 'accused_address', label: 'Accused Address', type: 'textarea', required: true },
            { name: 'complainant_name', label: 'Complainant Name', type: 'text', required: true },
            { name: 'notice_date', label: 'Date of Original Notice Received', type: 'date', required: true },
            { name: 'reply_date', label: 'Date of This Reply', type: 'date', required: true },
            { name: 'cheque_number', label: 'Cheque Number (as mentioned in notice)', type: 'text', required: true },
            { name: 'cheque_amount', label: 'Cheque Amount (Rs.)', type: 'number', required: true },
            { name: 'defence_ground', label: 'Primary Defence Ground', type: 'select', required: true, options: ['Cheque was given as Security - No Debt', 'Debt already fully repaid', 'Cheque was blank - misused', 'Signature is forged/disputed', 'No legally enforceable debt existed', 'Cheque issued under coercion/pressure', 'Other'] },
            { name: 'defence_details', label: 'Detailed Defence / Facts', type: 'textarea', required: true, placeholder: 'Explain your defence in detail...' },
            { name: 'advocate_name', label: "Accused's Advocate Name (Optional)", type: 'text', required: false }
        ],
        generate: function (d) {
            let caseCite = '';
            if (d.defence_ground.includes('Security')) {
                caseCite = '\n\nThat as held by the Hon\'ble Supreme Court in "Sampelly Satyanarayana Rao v. IREDA (2016) 10 SCC 458", a cheque given as security cannot be used for prosecution unless the debt is crystallised. In the present case, no such debt exists.';
            } else if (d.defence_ground.includes('Signature')) {
                caseCite = '\n\nThat as held in "Laxmi Dyechem v. State of Gujarat (2012) 13 SCC 375", the burden of proving a genuine signature lies heavily on the complainant, and any mismatch entitles the accused to a presumption of innocence.';
            }

            return `REPLY TO LEGAL NOTICE

Date: ${formatDraftDate(d.reply_date)}

To,
${d.complainant_name}
(And/Or through their Advocate)

Subject: Reply to your Legal Notice dated ${formatDraftDate(d.notice_date)} pertaining to Cheque No. ${d.cheque_number} for Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/-

Sir/Madam,

I, ${d.accused_name}, residing at ${d.accused_address}, hereby issue this Reply to your Notice dated ${formatDraftDate(d.notice_date)} as under:

1. At the outset, I deny each and every allegation, averment, and statement made in your notice, except those which are specifically admitted herein. The same are denied, both in law and on facts.

2. DENIAL OF LIABILITY: The contents of your notice are false, frivolous, vexatious, and devoid of any legal merit. The notice has been issued with the malafide intention of harassing and extorting money from me.

3. DEFENCE GROUND - ${d.defence_ground.toUpperCase()}:
${d.defence_details}${caseCite}

4. LEGAL POSITION: The cheque in question (No. ${d.cheque_number} for Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/-) was NOT issued in discharge of any legally enforceable debt or liability as alleged. The fundamental ingredients required under Section 138 of the Negotiable Instruments Act, 1881 are not fulfilled in the present case.

5. That your notice is, therefore, legally untenable, misconceived, and not maintainable in law. Any action initiated on the basis of your illegal and frivolous notice shall be resisted by me with full force and at your cost and risk.

6. You are hereby put on notice that if you proceed with any criminal complaint or civil action, I shall be compelled to take appropriate legal action for malicious prosecution, defamation, and seek damages accordingly.

7. I reserve all my legal rights and remedies in this matter.

Yours faithfully,

${d.accused_name}
${d.accused_address}
${d.advocate_name ? '\nThrough Advocate: ' + d.advocate_name : ''}

(This Reply is sent without prejudice to all rights and remedies available to the sender)`;
        }
    },
    {
        id: 'criminal_complaint', number: 3, title: 'Criminal Complaint (Sec. 138)', subtitle: 'Main Filing',
        description: 'Main complaint filed before the Magistrate with all facts and legal grounds.',
        icon: 'fa-gavel', color: '#ef4444',
        fields: [
            { name: 'court_name', label: 'Court Name', type: 'text', required: true, placeholder: 'e.g., Court of Judicial Magistrate First Class, Pune' },
            { name: 'complainant_name', label: 'Complainant Full Name', type: 'text', required: true },
            { name: 'complainant_address', label: 'Complainant Address', type: 'textarea', required: true },
            { name: 'complainant_occupation', label: 'Complainant Occupation', type: 'text', required: false, placeholder: 'e.g., Businessman' },
            { name: 'accused_name', label: 'Accused Full Name', type: 'text', required: true },
            { name: 'accused_address', label: 'Accused Address', type: 'textarea', required: true },
            { name: 'cheque_number', label: 'Cheque Number', type: 'text', required: true },
            { name: 'cheque_date', label: 'Cheque Date', type: 'date', required: true },
            { name: 'cheque_amount', label: 'Cheque Amount (Rs.)', type: 'number', required: true },
            { name: 'bank_name', label: 'Drawer Bank Name', type: 'text', required: true },
            { name: 'branch_name', label: 'Branch Name', type: 'text', required: false },
            { name: 'presentation_date', label: 'Date of Cheque Presentation', type: 'date', required: true },
            { name: 'dishonour_date', label: 'Date of Dishonour', type: 'date', required: true },
            { name: 'dishonour_reason', label: 'Dishonour Reason (as per bank memo)', type: 'text', required: true },
            { name: 'notice_date', label: 'Date of Demand Notice Sent', type: 'date', required: true },
            { name: 'notice_mode', label: 'Mode of Notice', type: 'select', required: true, options: ['Registered Post A.D.', 'Speed Post', 'Registered Post + Email', 'Hand Delivery with Acknowledgement'] },
            { name: 'notice_served', label: 'Was Notice Served?', type: 'select', required: true, options: ['Yes - Accused Acknowledged', 'Yes - Refused by Accused', 'Returned Unserved (deemed served)', 'Unknown'] },
            { name: 'payment_made', label: 'Did Accused Pay After Notice?', type: 'select', required: true, options: ['No - No Payment', 'Partial Payment Only'] },
            { name: 'transaction_purpose', label: 'Underlying Debt / Transaction Details', type: 'textarea', required: true },
            { name: 'filing_date', label: 'Date of Filing This Complaint', type: 'date', required: true }
        ],
        generate: function (d) {
            let s141_averment = '';
            if (d.accused_type === 'Company' || d.accused_type === 'Partnership Firm') {
                s141_averment = `\n\n11. VICARIOUS LIABILITY (S.141):
    That the Accused No. 1 is a Company/Firm and the Accused No. 2 to ___ are its Directors/Partners who were, at the time of the offence, in charge of and responsible to the Accused No. 1 for the conduct of its business. As per "Aneeta Hada v. Godfather Travels (2012) 5 SCC 661", the company has been impleaded as a primary accused along with its responsible officers.`;
            }

            return `IN THE ${d.court_name.toUpperCase()}

CRIMINAL COMPLAINT UNDER SECTION 138 READ WITH SECTION 142 OF
THE NEGOTIABLE INSTRUMENTS ACT, 1881

COMPLAINT CASE NO. _____________ / ${new Date(d.filing_date || Date.now()).getFullYear()}

IN THE MATTER OF:

COMPLAINANT:
${d.complainant_name}
${d.complainant_address}
${d.complainant_occupation ? '(Occupation: ' + d.complainant_occupation + ')' : ''}
                                                ...Complainant

VERSUS

ACCUSED:
${d.accused_name}
${d.accused_address}
                                                ...Accused

-------------------------------------------------

CRIMINAL COMPLAINT UNDER SECTION 138 OF THE NEGOTIABLE INSTRUMENTS ACT, 1881

-------------------------------------------------

MOST RESPECTFULLY SHEWETH:

1. That the Complainant, ${d.complainant_name}, is ${d.complainant_occupation ? 'engaged in ' + d.complainant_occupation : 'a law-abiding citizen/entity'}. ${d.accused_type === 'Company' ? 'The Complainant is represented by its Authorized Signatory/Director, who is duly empowered to file, sign, and verify the present complaint by way of a Board Resolution/Letter of Authority dated _________, which is produced herewith as Annexure-A.' : ''}

2. That the Accused, ${d.accused_name}, is known to the Complainant and both parties had a financial/business relationship with each other.

3. UNDERLYING TRANSACTION:
   That the Complainant advanced/paid a sum of Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/- (Rupees ${numberToWords(d.cheque_amount)} Only) to the Accused towards ${d.transaction_purpose}.

4. ISSUANCE OF CHEQUE:
   That in discharge of the aforesaid legally enforceable debt/liability, the Accused issued Cheque No. ${d.cheque_number} dated ${formatDraftDate(d.cheque_date)} for an amount of Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/- (Rupees ${numberToWords(d.cheque_amount)} Only) drawn on ${d.bank_name}${d.branch_name ? ', ' + d.branch_name : ''}.

5. PRESENTATION & DISHONOUR:
   That the Complainant presented the said cheque for encashment on ${formatDraftDate(d.presentation_date)}. However, the said cheque was returned/dishonoured by the bank on ${formatDraftDate(d.dishonour_date)} with the bank's memo stating: "${d.dishonour_reason}."

6. LEGAL DEMAND NOTICE:
   That as required under Section 138 of the NI Act, the Complainant sent a Legal Demand Notice to the Accused on ${formatDraftDate(d.notice_date)} by way of ${d.notice_mode}. The notice was ${d.notice_served}. As per "C.C. Alavi Haji v. Palapetty Muhammed (2007) 6 SCC 555", the service of notice is complete once dispatched to the correct address.

7. FAILURE TO PAY:
   That despite receipt of the said notice, the Accused has ${d.payment_made}. Accordingly, the cause of action for filing this complaint has arisen.

8. CAUSE OF ACTION:
   The cause of action arose on ${formatDraftDate(d.dishonour_date)} (date of dishonour), and again when the Accused failed to pay within the statutory period after the demand notice. This complaint is filed within limitation.

9. OFFENCE COMMITTED:
   That the acts of the Accused amount to an offence under Section 138 of the Negotiable Instruments Act, 1881, punishable with imprisonment up to 2 years, or fine up to twice the cheque amount, or both.

10. JURISDICTION:
    That this Hon'ble Court has territorial jurisdiction to entertain and try the present complaint as the cheque in question was presented for encashment at ${d.bank_name}${d.branch_name ? ' (' + d.branch_name + ' Branch)' : ''}, which is situated within the territorial limits of this Hon'ble Court, in accordance with the law laid down by the Hon'ble Supreme Court in "Dashrath Rupsingh Rathod vs. State of Maharashtra".${s141_averment}

PRAYER:
It is most respectfully prayed that this Hon'ble Court may be pleased to:

(a) Take cognizance of the offence under Section 138 of the NI Act;
(b) Issue summons/process against the Accused;
(c) Direct the Accused to pay Interim Compensation to the Complainant under Section 143A of the NI Act (up to 20% of the cheque amount);
(d) After trial, convict and sentence the Accused in accordance with law;
(e) Direct the Accused to pay fine/compensation of Rs.${(Number(d.cheque_amount) * 2).toLocaleString('en-IN')}/- (double the cheque amount) with interest;
(e) Pass any other order as deemed fit in the interest of justice.

AND FOR THIS ACT OF KINDNESS, THE COMPLAINANT AS IN DUTY BOUND SHALL EVER PRAY.

Date: ${formatDraftDate(d.filing_date)}
Place: _______________

                                        ________________________
                                        ${d.complainant_name}
                                        (Complainant)

VERIFICATION:
I, ${d.complainant_name}, the Complainant, do hereby solemnly affirm and state that the contents of paragraphs 1 to 10 of the above complaint are true and correct to the best of my knowledge, information and belief, and I believe the same to be true. No material fact has been concealed therefrom, and all supporting documents mentioned herein are annexed to the complaint.

Verified at _____________ on ${formatDraftDate(d.filing_date)}.

                                        ________________________
                                        (Complainant)`;
        }
    },
    {
        id: 'affidavit_evidence', number: 4, title: 'Affidavit of Evidence', subtitle: 'Complainant',
        description: 'Sworn statement supporting the complaint, filed along with documents.',
        icon: 'fa-file-signature', color: '#f59e0b',
        fields: [
            { name: 'case_number', label: 'Case Number / CC No.', type: 'text', required: true, placeholder: 'e.g., CC/123/2024' },
            { name: 'court_name', label: 'Court Name', type: 'text', required: true },
            { name: 'complainant_name', label: 'Deponent / Complainant Name', type: 'text', required: true },
            { name: 'complainant_age', label: 'Age of Deponent', type: 'number', required: false, placeholder: 'e.g., 42' },
            { name: 'complainant_address', label: 'Deponent Address', type: 'textarea', required: true },
            { name: 'accused_name', label: 'Accused Name', type: 'text', required: true },
            { name: 'cheque_number', label: 'Cheque Number', type: 'text', required: true },
            { name: 'cheque_date', label: 'Cheque Date', type: 'date', required: true },
            { name: 'cheque_amount', label: 'Cheque Amount (Rs.)', type: 'number', required: true },
            { name: 'bank_name', label: 'Bank Name', type: 'text', required: true },
            { name: 'dishonour_date', label: 'Dishonour Date', type: 'date', required: true },
            { name: 'dishonour_reason', label: 'Dishonour Reason', type: 'text', required: true },
            { name: 'notice_date', label: 'Demand Notice Date', type: 'date', required: true },
            { name: 'transaction_purpose', label: 'Underlying Debt/Transaction', type: 'textarea', required: true },
            { name: 'affidavit_date', label: 'Date of Affidavit', type: 'date', required: true }
        ],
        generate: function (d) {
            return `AFFIDAVIT OF EVIDENCE OF COMPLAINANT / PW-1

In the matter of: ${d.case_number}
IN THE COURT OF THE LEARNED MAGISTRATE AT ${d.court_name.toUpperCase()}

AFFIDAVIT OF ${d.complainant_name.toUpperCase()}
(Deponent / Complainant / PW-1)

-------------------------------------------------

I, ${d.complainant_name}${d.complainant_age ? ', aged about ' + d.complainant_age + ' years' : ''}, residing at ${d.complainant_address}, being the Complainant in the above case, do hereby solemnly affirm and state on oath as follows:

1. I am the Complainant in the above case and am fully conversant with the facts and circumstances of the case. I am competent to swear this affidavit.

2. That I advanced a sum of Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/- to the Accused towards ${d.transaction_purpose}.

3. That in discharge of the legally enforceable debt/liability, the Accused issued Cheque No. ${d.cheque_number} dated ${formatDraftDate(d.cheque_date)} for Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/-, drawn on ${d.bank_name}. The original cheque is produced herewith as EXHIBIT-CW1/1.

4. That on presentation, the said cheque was returned/dishonoured on ${formatDraftDate(d.dishonour_date)} with the endorsement: "${d.dishonour_reason}." The original dishonour memo is produced herewith as EXHIBIT-CW1/2.

5. That I sent a statutory Legal Demand Notice to the Accused on ${formatDraftDate(d.notice_date)} by Registered Post/Speed Post. The office copy of notice, postal receipt and tracking report are produced herewith as EXHIBIT-CW1/3 (Colly).

6. That despite receipt of the notice, the Accused failed to make payment of the cheque amount within the statutory period of 15 days, thereby committing an offence under Section 138 of the NI Act.

7. I submit that all the documents/exhibits mentioned above are original and the contents of this affidavit are true to my knowledge.

8. I have not filed any other complaint or suit in respect of the same cause of action.

                                        DEPONENT
                                        ${d.complainant_name}

Verification:
Verified at ______________ on ${formatDraftDate(d.affidavit_date)} that the contents of this affidavit are true and correct.

                                        DEPONENT`;
        }
    },
    {
        id: 'memo_of_parties', number: 5, title: 'Memo of Parties', subtitle: 'Party Details',
        description: 'Properly lists complainant and accused details for court filing.',
        icon: 'fa-users', color: '#10b981',
        fields: [
            { name: 'case_number', label: 'Case Number / CC No.', type: 'text', required: false, placeholder: 'Leave blank if not yet assigned' },
            { name: 'court_name', label: 'Court Name', type: 'text', required: true },
            { name: 'complainant_name', label: 'Complainant Full Name', type: 'text', required: true },
            { name: 'complainant_fathers_name', label: "Complainant's Father's / Husband's Name", type: 'text', required: false },
            { name: 'complainant_age', label: 'Complainant Age', type: 'number', required: false },
            { name: 'complainant_occupation', label: 'Complainant Occupation', type: 'text', required: false },
            { name: 'complainant_address', label: 'Complainant Full Address', type: 'textarea', required: true },
            { name: 'complainant_phone', label: 'Complainant Phone', type: 'tel', required: false },
            { name: 'accused_name', label: 'Accused Full Name', type: 'text', required: true },
            { name: 'accused_fathers_name', label: "Accused's Father's / Husband's Name", type: 'text', required: false },
            { name: 'accused_age', label: 'Accused Age', type: 'number', required: false },
            { name: 'accused_occupation', label: 'Accused Occupation', type: 'text', required: false },
            { name: 'accused_address', label: 'Accused Full Address', type: 'textarea', required: true },
            { name: 'accused_phone', label: 'Accused Phone (if known)', type: 'tel', required: false },
            { name: 'advocate_name', label: "Complainant's Advocate Name", type: 'text', required: false }
        ],
        generate: function (d) {
            return `MEMO OF PARTIES

${d.court_name.toUpperCase()}
CASE NO.: ${d.case_number || '_______________'}

CRIMINAL COMPLAINT UNDER SECTION 138 OF THE NEGOTIABLE INSTRUMENTS ACT, 1881

-------------------------------------------------

COMPLAINANT:

Name               : ${d.complainant_name}
${d.complainant_fathers_name ? 'S/o / W/o / D/o    : ' + d.complainant_fathers_name : ''}
${d.complainant_age ? 'Age                : ' + d.complainant_age + ' Years' : ''}
${d.complainant_occupation ? 'Occupation         : ' + d.complainant_occupation : ''}
Address            : ${d.complainant_address}
${d.complainant_phone ? 'Contact No.        : ' + d.complainant_phone : ''}

                                                            ...Complainant

VERSUS

ACCUSED:

Name               : ${d.accused_name}
${d.accused_fathers_name ? 'S/o / W/o / D/o    : ' + d.accused_fathers_name : ''}
${d.accused_age ? 'Age                : ' + d.accused_age + ' Years' : ''}
${d.accused_occupation ? 'Occupation         : ' + d.accused_occupation : ''}
Address            : ${d.accused_address}
${d.accused_phone ? 'Contact No.        : ' + d.accused_phone : ''}

                                                            ...Accused

-------------------------------------------------
${d.advocate_name ? 'Advocate for Complainant: ' + d.advocate_name : ''}

Date: _______________
Place: _______________

                                        Signature of Complainant
                                        ${d.complainant_name}`;
        }
    },
    {
        id: 'list_documents', number: 6, title: 'List of Documents / Exhibits', subtitle: 'Evidence List',
        description: 'Lists all documents: cheque copy, bank memo, notice, postal receipts.',
        icon: 'fa-list-alt', color: '#6366f1',
        fields: [
            { name: 'case_number', label: 'Case Number', type: 'text', required: false },
            { name: 'court_name', label: 'Court Name', type: 'text', required: true },
            { name: 'complainant_name', label: 'Complainant Name', type: 'text', required: true },
            { name: 'accused_name', label: 'Accused Name', type: 'text', required: true },
            { name: 'cheque_number', label: 'Cheque Number', type: 'text', required: true },
            { name: 'cheque_date', label: 'Cheque Date', type: 'date', required: true },
            { name: 'cheque_amount', label: 'Cheque Amount (Rs.)', type: 'number', required: true },
            { name: 'bank_name', label: 'Bank Name', type: 'text', required: true },
            { name: 'notice_date', label: 'Notice Date', type: 'date', required: true },
            { name: 'has_agreement', label: 'Loan/Agreement Document Available?', type: 'select', required: false, options: ['Yes', 'No'] },
            { name: 'has_witnesses', label: 'Witness Statements Available?', type: 'select', required: false, options: ['Yes', 'No'] },
            { name: 'has_whatsapp', label: 'WhatsApp/SMS/Email Records?', type: 'select', required: false, options: ['Yes', 'No'] },
            { name: 'filing_date', label: 'Date of Filing', type: 'date', required: true }
        ],
        generate: function (d) {
            let extraDocs = '';
            let idx = 6;
            if (d.has_agreement === 'Yes') { extraDocs += `\n${idx}   Loan Agreement / Promissory Note / Written Agreement          Exh. ${String.fromCharCode(64 + idx)}`; idx++; }
            if (d.has_witnesses === 'Yes') { extraDocs += `\n${idx}   Witness Statements / Affidavits of Witnesses                  Exh. ${String.fromCharCode(64 + idx)}`; idx++; }
            if (d.has_whatsapp === 'Yes') { extraDocs += `\n${idx}   WhatsApp/SMS/Email Correspondence (Printouts)                 Exh. ${String.fromCharCode(64 + idx)}`; idx++; }
            return `LIST OF DOCUMENTS / EXHIBITS FILED ALONG WITH COMPLAINT

${d.court_name.toUpperCase()}
CASE NO.: ${d.case_number || '_______________'}

${d.complainant_name}     ...Complainant
VERSUS
${d.accused_name}          ...Accused

-------------------------------------------------

LIST OF DOCUMENTS / EXHIBITS

The Complainant hereby files the following documents in support of the complaint under Section 138 NI Act:

Sr.  Description of Document                                        Exhibit
---  -------------------------------------------------------------- -------
1    Original Cheque No. ${d.cheque_number} dated                   Exh. A
     ${formatDraftDate(d.cheque_date)} for Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/-
     drawn on ${d.bank_name}

2    Original Bank Dishonour Memo / Return Memo                     Exh. B

3    Copy of Legal Demand Notice dated ${formatDraftDate(d.notice_date)}    Exh. C

4    Postal Receipt (Registered Post A.D./Speed Post)               Exh. D

5    Acknowledgement Card (A.D. Card) / Delivery Proof              Exh. E
${extraDocs}
${idx}    Affidavit of Complainant / PW-1                                Exh. ${String.fromCharCode(64 + idx)}

Note: All documents above are original unless specifically mentioned as copies.

Date: ${formatDraftDate(d.filing_date)}
Place: _______________

                                        ________________________
                                        ${d.complainant_name}
                                        (Complainant)`;
        }
    },
    {
        id: 'condonation_delay', number: 7, title: 'Application – Condonation of Delay', subtitle: 'Late Filing',
        description: 'Filed when the complaint is submitted after the limitation period.',
        icon: 'fa-clock', color: '#f97316',
        fields: [
            { name: 'court_name', label: 'Court Name', type: 'text', required: true },
            { name: 'complainant_name', label: 'Complainant Name', type: 'text', required: true },
            { name: 'complainant_address', label: 'Complainant Address', type: 'textarea', required: true },
            { name: 'accused_name', label: 'Accused Name', type: 'text', required: true },
            { name: 'cheque_number', label: 'Cheque Number', type: 'text', required: true },
            { name: 'cheque_amount', label: 'Cheque Amount (Rs.)', type: 'number', required: true },
            { name: 'dishonour_date', label: 'Cheque Dishonour Date', type: 'date', required: true },
            { name: 'limitation_expiry', label: 'Limitation Period Expiry Date', type: 'date', required: true },
            { name: 'actual_filing_date', label: 'Actual Date of Filing', type: 'date', required: true },
            { name: 'delay_days', label: 'Approximate Days of Delay', type: 'number', required: true },
            { name: 'reason_for_delay', label: 'Reason for Delay (Detailed)', type: 'textarea', required: true, placeholder: 'Explain why the complaint could not be filed within limitation period...' }
        ],
        generate: function (d) {
            return `APPLICATION UNDER SECTION 142(b) OF THE NEGOTIABLE INSTRUMENTS ACT, 1881
READ WITH SECTION 5 OF THE LIMITATION ACT, 1963
FOR CONDONATION OF DELAY IN FILING COMPLAINT

IN THE ${d.court_name.toUpperCase()}

${d.complainant_name}                              ...Applicant/Complainant
VERSUS
${d.accused_name}                                  ...Respondent/Accused

-------------------------------------------------

APPLICATION FOR CONDONATION OF DELAY OF APPROXIMATELY ${d.delay_days} DAYS

-------------------------------------------------

MOST RESPECTFULLY SHEWETH:

1. That the Applicant/Complainant is filing the above complaint under Section 138 of the Negotiable Instruments Act, 1881, against the Respondent/Accused in relation to Cheque No. ${d.cheque_number} for Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/- which was dishonoured on ${formatDraftDate(d.dishonour_date)}.

2. That the limitation period for filing the present complaint expired on ${formatDraftDate(d.limitation_expiry)}. The present complaint is being filed on ${formatDraftDate(d.actual_filing_date)}, i.e., a delay of approximately ${d.delay_days} days.

3. REASONS FOR DELAY:
${d.reason_for_delay}

4. That the delay in filing the complaint was not deliberate, wilful, or due to negligence on the part of the Complainant. The delay was caused due to the genuine and unavoidable reasons stated above.

5. That the Applicant submits that sufficient cause exists for condoning the said delay.

6. That no prejudice will be caused to the Respondent/Accused by condoning the said delay.

PRAYER:
It is most respectfully prayed that this Hon'ble Court may be pleased to condone the delay of ${d.delay_days} days in filing the above complaint and allow the complaint to be entertained on merits.

And for this act of kindness, the Applicant shall ever pray.

Date: ${formatDraftDate(d.actual_filing_date)}
Place: _______________

                                        ________________________
                                        ${d.complainant_name}
                                        (Applicant/Complainant)

VERIFICATION:
I, ${d.complainant_name}, verify that the contents of the above application are true and correct to the best of my knowledge and belief.

Verified at ______________ on ${formatDraftDate(d.actual_filing_date)}.`;
        }
    },
    {
        id: 'summons_application', number: 8, title: 'Summons / Process Application', subtitle: 'Court Summons',
        description: 'Request to the court to issue summons to the accused.',
        icon: 'fa-paper-plane', color: '#0891b2',
        fields: [
            { name: 'court_name', label: 'Court Name', type: 'text', required: true },
            { name: 'case_number', label: 'Case/CC Number', type: 'text', required: false },
            { name: 'complainant_name', label: 'Complainant Name', type: 'text', required: true },
            { name: 'accused_name', label: 'Accused Full Name', type: 'text', required: true },
            { name: 'accused_address', label: 'Accused Address (For Service)', type: 'textarea', required: true },
            { name: 'accused_phone', label: 'Accused Phone (if known)', type: 'tel', required: false },
            { name: 'accused_workplace', label: 'Accused Workplace Address (if known)', type: 'textarea', required: false },
            { name: 'cheque_number', label: 'Cheque Number', type: 'text', required: true },
            { name: 'cheque_amount', label: 'Cheque Amount (Rs.)', type: 'number', required: true },
            { name: 'mode_of_service', label: 'Preferred Mode of Summons Service', type: 'select', required: true, options: ['Ordinary Process', 'Registered Post', 'Registered Post + Ordinary Process', 'Police Service'] },
            { name: 'application_date', label: 'Date of Application', type: 'date', required: true }
        ],
        generate: function (d) {
            return `APPLICATION FOR ISSUANCE OF SUMMONS / PROCESS

IN THE ${d.court_name.toUpperCase()}
${d.case_number ? 'CASE NO.: ' + d.case_number : ''}

${d.complainant_name}                              ...Complainant
VERSUS
${d.accused_name}                                  ...Accused

-------------------------------------------------

APPLICATION UNDER SECTION 204 Cr.P.C. / BNSS FOR ISSUANCE OF PROCESS/SUMMONS

-------------------------------------------------

MOST RESPECTFULLY SHEWETH:

1. That the Complainant has filed a complaint under Section 138 of the Negotiable Instruments Act, 1881 against the Accused in the above case, relating to dishonour of Cheque No. ${d.cheque_number} for Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/-.

2. That it is necessary that summons/process be issued and served upon the Accused to ensure their appearance before this Hon'ble Court.

3. DETAILS OF ACCUSED FOR SERVICE OF SUMMONS:

   Accused Name    : ${d.accused_name}
   Address 1       : ${d.accused_address}
${d.accused_phone ? '   Contact No.     : ' + d.accused_phone : ''}
${d.accused_workplace ? '   Workplace Addr. : ' + d.accused_workplace : ''}

4. That the Complainant prays that summons be issued to the Accused by mode of ${d.mode_of_service} at the above address.

PRAYER:
It is most respectfully prayed that this Hon'ble Court may be pleased to:

(a) Issue summons/process against the Accused at the above address by ${d.mode_of_service};
(b) Fix a date for appearance of the Accused;
(c) Pass any other order as this Hon'ble Court deems fit.

Date: ${formatDraftDate(d.application_date)}
Place: _______________

                                        ________________________
                                        ${d.complainant_name}
                                        (Complainant)`;
        }
    },
    {
        id: 'notice_251', number: 9, title: 'Notice under Section 251 CrPC', subtitle: 'Charge Explanation',
        description: 'Document for reading and explaining charges to the accused in court.',
        icon: 'fa-balance-scale-right', color: '#7c3aed',
        fields: [
            { name: 'court_name', label: 'Court Name', type: 'text', required: true },
            { name: 'case_number', label: 'Case Number', type: 'text', required: true },
            { name: 'hearing_date', label: 'Date of Hearing', type: 'date', required: true },
            { name: 'complainant_name', label: 'Complainant Name', type: 'text', required: true },
            { name: 'accused_name', label: 'Accused Name', type: 'text', required: true },
            { name: 'accused_address', label: 'Accused Address', type: 'textarea', required: true },
            { name: 'cheque_number', label: 'Cheque Number', type: 'text', required: true },
            { name: 'cheque_date', label: 'Cheque Date', type: 'date', required: true },
            { name: 'cheque_amount', label: 'Cheque Amount (Rs.)', type: 'number', required: true },
            { name: 'bank_name', label: 'Bank Name', type: 'text', required: true },
            { name: 'dishonour_date', label: 'Dishonour Date', type: 'date', required: true },
            { name: 'dishonour_reason', label: 'Dishonour Reason', type: 'text', required: true }
        ],
        generate: function (d) {
            return `NOTICE UNDER SECTION 251 OF THE CODE OF CRIMINAL PROCEDURE, 1973 / BNSS

IN THE ${d.court_name.toUpperCase()}

CASE NO.: ${d.case_number}

${d.complainant_name}                              ...Complainant
VERSUS
${d.accused_name}                                  ...Accused

-------------------------------------------------
NOTICE TO ACCUSED / PARTICULARS OF OFFENCE
-------------------------------------------------

Date: ${formatDraftDate(d.hearing_date)}

To,
${d.accused_name}
${d.accused_address}

TAKE NOTICE that on ${formatDraftDate(d.hearing_date)}, you appeared before this Court in the above case.

YOU ARE HEREBY INFORMED that the following charge/offence is alleged against you:

-------------------------------------------------
PARTICULARS OF THE OFFENCE:
-------------------------------------------------

That you, ${d.accused_name}, being the drawer of Cheque No. ${d.cheque_number} dated ${formatDraftDate(d.cheque_date)} for Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/- (Rupees ${numberToWords(d.cheque_amount)} Only) drawn on ${d.bank_name}, issued the same in discharge of a legally enforceable debt/liability to the Complainant, ${d.complainant_name}.

That the said cheque was returned/dishonoured by the bank on ${formatDraftDate(d.dishonour_date)} with the reason: "${d.dishonour_reason}."

That despite receipt of a statutory Demand Notice, you failed to make the requisite payment within the stipulated period, thereby committing an offence punishable under:

SECTION 138 of the Negotiable Instruments Act, 1881
(Dishonour of cheque for insufficiency, etc. of funds in the account)

-------------------------------------------------

DO YOU PLEAD GUILTY OR NOT GUILTY?

[ ] I PLEAD GUILTY to the charge as stated above.
[ ] I PLEAD NOT GUILTY and claim to be tried.

-------------------------------------------------

Reply of Accused: ______________________________________

Signature of Accused: _________________________
Date: ${formatDraftDate(d.hearing_date)}

                                        JUDICIAL MAGISTRATE
                                        ${d.court_name}`;
        }
    },
    {
        id: 'cross_examination', number: 10, title: 'Cross-Examination Questions Draft', subtitle: 'Trial Strategy',
        description: 'Prepared questions for cross-examining the accused or complainant.',
        icon: 'fa-comments', color: '#dc2626',
        fields: [
            { name: 'case_number', label: 'Case Number', type: 'text', required: false },
            { name: 'court_name', label: 'Court Name', type: 'text', required: true },
            { name: 'witness_name', label: 'Name of Witness Being Cross-Examined', type: 'text', required: true },
            { name: 'witness_role', label: 'Role of Witness', type: 'select', required: true, options: ['PW-1 (Complainant)', 'DW-1 (Accused)', 'PW-2 (Bank Official)', 'Other Prosecution Witness', 'Other Defence Witness'] },
            { name: 'complainant_name', label: 'Complainant Name', type: 'text', required: true },
            { name: 'accused_name', label: 'Accused Name', type: 'text', required: true },
            { name: 'cheque_number', label: 'Cheque Number', type: 'text', required: true },
            { name: 'cheque_amount', label: 'Cheque Amount (Rs.)', type: 'number', required: true },
            { name: 'defence_strategy', label: 'Cross Strategy Focus', type: 'select', required: true, options: ['Challenge debt existence', 'Challenge notice validity', 'Challenge cheque issuance purpose', 'Challenge bank memo authenticity', 'Challenge limitation period', 'General credibility attack'] },
            { name: 'cross_date', label: 'Date of Cross-Examination', type: 'date', required: false }
        ],
        generate: function (d) {
            const strategyQs = {
                'Challenge debt existence': `Q17. (*) You have no written agreement, loan deed, or promissory note to prove the alleged debt?
Q18. The money was allegedly given in cash - do you have any receipt or record of payment?
Q19. Is it possible that the amount was a gift or advance and not a loan?
Q20. You cannot produce any bank statement showing the transfer of Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/- to the Accused?
Q21. The entire foundation of your complaint rests solely on a self-serving oral statement?`,
                'Challenge notice validity': `Q17. (*) Can you produce the original postal receipt proving the notice was dispatched within 30 days of dishonour?
Q18. The A.D. card - is the handwriting on it that of the Accused?
Q19. You admitted the notice was sent to an address which was not the Accused's last known address?
Q20. Is it correct that the notice did not specifically demand the exact cheque amount?
Q21. (*) The 15-day period for payment had not yet expired when you filed this complaint?`,
                'Challenge cheque issuance purpose': `Q17. (*) Is it not correct that the cheque was given as a blank security cheque?
Q18. You are aware that security cheques cannot be the subject matter of Section 138 proceedings?
Q19. When exactly did you fill in the date and amount on the cheque?
Q20. Do you have any document showing the cheque was issued as repayment and not as security?
Q21. The Accused had specifically asked you to return the cheque when the purpose was served?`,
                'Challenge bank memo authenticity': `Q17. Can you identify the bank official who signed the dishonour memo (Exh. B)?
Q18. Have you ever produced that official as a witness before this court?
Q19. (*) The dishonour memo has no seal of the bank - is that correct?
Q20. Are you aware that bank records can be altered?
Q21. The bank account from which the cheque was drawn was in fact active at the material time?`,
                'Challenge limitation period': `Q17. When exactly did you first receive the bank dishonour memo?
Q18. (*) So the notice was sent more than 30 days after the dishonour, is that correct?
Q19. When was the complaint actually filed before this court?
Q20. You are aware that if the complaint is filed beyond one month from the cause of action, it is barred by limitation?
Q21. No application for condonation of delay was filed before this court?`,
                'General credibility attack': `Q17. You have a financial dispute with the Accused on matters unrelated to this cheque?
Q18. (*) You have filed / threatened to file multiple cases against the Accused?
Q19. The entire case is based on your own self-interested testimony without independent corroboration?
Q20. You stand to receive Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/- if the Accused is convicted?
Q21. This complaint is a pressure tactic to settle a separate civil dispute?`
            };
            return `DRAFT QUESTIONS FOR CROSS-EXAMINATION OF ${d.witness_role.toUpperCase()}

CASE: ${d.case_number || '_____________'}
COURT: ${d.court_name}
${d.complainant_name} vs. ${d.accused_name}

WITNESS: ${d.witness_name} (${d.witness_role})
STRATEGY FOCUS: ${d.defence_strategy}
${d.cross_date ? 'DATE: ' + formatDraftDate(d.cross_date) : ''}

-------------------------------------------------
DRAFT CROSS-EXAMINATION QUESTIONS
-------------------------------------------------

SECTION A - PRELIMINARY / BACKGROUND QUESTIONS

Q1.  You are aware of the present case being CC No. ${d.case_number || '_____'} pending before this court?
Q2.  You have given your examination-in-chief by way of affidavit before this court, is that correct?
Q3.  You are personally acquainted with both the Complainant and the Accused?
Q4.  How long have you known the Complainant / Accused?

-------------------------------------------------
SECTION B - ON CHEQUE & TRANSACTION

Q5.  The cheque bearing No. ${d.cheque_number} for Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/- was allegedly drawn in discharge of a legally enforceable debt - is that your claim?
Q6.  Do you have any written agreement, promissory note, or document evidencing the loan or debt?
Q7.  Is it correct that no written agreement was executed between the parties?
Q8.  Was the cheque handed over in the presence of any witness?
Q9.  Is it possible that the cheque was given as security and not towards repayment of debt?
Q10. Are you aware that a post-dated / security cheque cannot form the basis of Section 138 proceedings?

-------------------------------------------------
SECTION C - ON NOTICE & SERVICE

Q11. You claim to have sent a legal notice under Section 138 - when was it sent?
Q12. By what mode was the notice sent?
Q13. Do you have the original postal receipt showing the notice was dispatched?
Q14. Was the A.D. card returned? Is the signature on the A.D. card that of the Accused?
Q15. Is it possible that the notice was sent to an incorrect address?
Q16. You have no proof that the Accused actually received the notice, correct?

-------------------------------------------------
SECTION D - STRATEGY: ${d.defence_strategy}

${strategyQs[d.defence_strategy] || 'Q17. Are all the facts stated in your examination-in-chief true?\nQ18. Is there any fact you may have omitted or exaggerated?\nQ19. You have no independent witness to corroborate your claims?\nQ20. Is it possible your recollection of dates and amounts may be incorrect?'}

-------------------------------------------------
SECTION E - CLOSING / CREDIBILITY

Q25. You stand to gain financially if the Accused is convicted, correct?
Q26. Is it possible that the entire complaint is filed for harassment?
Q27. You are relying entirely on what you have been told by your lawyer?

-------------------------------------------------
NOTE TO ADVOCATE:
- (*) marks high-impact questions. Use them strategically.
- Adapt to actual evidence and admissions in examination-in-chief.
- Do not ask questions the answers to which you cannot control.
- Stop cross-examination once a favorable admission is obtained.`;
        }
    },
    {
        id: 'final_arguments', number: 11, title: 'Final Arguments (Written Submissions)', subtitle: 'Legal Reasoning',
        description: 'Legal reasoning, case law citations, and conclusion for final arguments.',
        icon: 'fa-scroll', color: '#065f46',
        fields: [
            { name: 'court_name', label: 'Court Name', type: 'text', required: true },
            { name: 'case_number', label: 'Case Number', type: 'text', required: true },
            { name: 'complainant_name', label: 'Complainant Name', type: 'text', required: true },
            { name: 'accused_name', label: 'Accused Name', type: 'text', required: true },
            { name: 'cheque_number', label: 'Cheque Number', type: 'text', required: true },
            { name: 'cheque_amount', label: 'Cheque Amount (Rs.)', type: 'number', required: true },
            { name: 'cheque_date', label: 'Cheque Date', type: 'date', required: true },
            { name: 'dishonour_date', label: 'Dishonour Date', type: 'date', required: true },
            { name: 'dishonour_reason', label: 'Dishonour Reason', type: 'text', required: true },
            { name: 'side', label: 'Arguments Filed By', type: 'select', required: true, options: ['Complainant Side', 'Accused Side / Defence'] },
            { name: 'key_facts', label: 'Key Facts Proved During Trial', type: 'textarea', required: true, placeholder: 'Summarise key facts proved through evidence...' },
            { name: 'arguments_date', label: 'Date of Filing', type: 'date', required: true }
        ],
        generate: function (d) {
            const isComp = d.side === 'Complainant Side';
            return `WRITTEN ARGUMENTS / FINAL SUBMISSIONS

IN THE ${d.court_name.toUpperCase()}

CASE NO.: ${d.case_number}

${d.complainant_name}                              ...Complainant
VERSUS
${d.accused_name}                                  ...Accused

WRITTEN ARGUMENTS ON BEHALF OF THE ${d.side.toUpperCase()}

DATE: ${formatDraftDate(d.arguments_date)}

-------------------------------------------------

I. INTRODUCTION

The present complaint has been filed under Section 138 of the Negotiable Instruments Act, 1881 by the Complainant, ${d.complainant_name}, against the Accused, ${d.accused_name}, on account of dishonour of Cheque No. ${d.cheque_number} dated ${formatDraftDate(d.cheque_date)} for Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/- with the endorsement "${d.dishonour_reason}" on ${formatDraftDate(d.dishonour_date)}.

-------------------------------------------------

II. FACTS OF THE CASE

${d.key_facts}

-------------------------------------------------

III. INGREDIENTS OF SECTION 138 NI ACT

A. EXISTENCE OF LEGALLY ENFORCEABLE DEBT OR LIABILITY:
   ${isComp ? 'The Complainant has conclusively proved through documents and testimony that the cheque was issued towards repayment of a lawful debt.' : 'The Defence contends that no legally enforceable debt or liability existed. The cheque was issued as security / under duress / without consideration.'}

B. DISHONOUR OF CHEQUE:
   Cheque No. ${d.cheque_number} was returned/dishonoured on ${formatDraftDate(d.dishonour_date)} with the memo "${d.dishonour_reason}." This has been proved through the original dishonour memo (Exh. B).

C. STATUTORY DEMAND NOTICE:
   ${isComp ? 'A valid demand notice was sent by Registered Post within 30 days of dishonour. The Accused failed to pay within the statutory period of 15 days from receipt of notice.' : 'The Defence submits that the demand notice was not validly served / was sent beyond the 30-day statutory period / did not contain the requisite demand.'}

D. FAILURE TO MAKE PAYMENT:
   ${isComp ? 'The Accused failed and neglected to make payment of Rs.' + Number(d.cheque_amount).toLocaleString('en-IN') + '/- within 15 days of receipt of notice, thereby completing the offence.' : 'The Accused had no liability to pay as the alleged debt was non-existent / already repaid / the cheque was misused.'}

-------------------------------------------------

IV. RELEVANT CASE LAW

1. Dashrath Rupsingh Rathod v. State of Maharashtra (2014) 9 SCC 129
   (Jurisdiction of court where complaint is to be filed)

2. Meters and Instruments Pvt. Ltd. v. Kanchan Mehta (2018) 1 SCC 560
   (Presumption under Sec. 139; summary trial powers)

3. M.S. Narayana Menon v. State of Kerala (2006) 6 SCC 39
   (Burden of proof and presumption under Section 139 NI Act)

4. K. Bhaskaran v. Sankaran Vaidhyan Balan (1999) 7 SCC 510
   (Five ingredients of Sec. 138; place of filing of complaint)

5. Kusum Ingots & Alloys Ltd. v. Pennor India (P) Ltd (2000) 2 SCC 745
   (Vicarious liability of directors under Section 141 NI Act)

-------------------------------------------------

V. CONCLUSION & PRAYER

${isComp ?
                    `The Complainant has proved all the ingredients of Section 138 NI Act beyond reasonable doubt. The Accused is guilty of the offence charged.

PRAYER: The Accused may be convicted under Section 138 of the NI Act and sentenced to appropriate imprisonment and/or directed to pay compensation of Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/- to the Complainant with interest, in the interest of justice.` :
                    `The prosecution has failed to prove the essential ingredients of Section 138 NI Act beyond reasonable doubt. The Accused is entitled to be acquitted.

PRAYER: The Accused may be acquitted of the charge under Section 138 NI Act, as the prosecution has failed to establish its case beyond reasonable doubt.`}

Date: ${formatDraftDate(d.arguments_date)}
Place: _______________

                                        Respectfully submitted,
                                        Advocate for the ${d.side}`;
        }
    },
    {
        id: 'settlement_agreement', number: 12, title: 'Compounding / Settlement Agreement', subtitle: 'Case Closure',
        description: 'Used when parties settle. Ends litigation under Section 147 NI Act.',
        icon: 'fa-handshake', color: '#059669',
        fields: [
            { name: 'court_name', label: 'Court Name', type: 'text', required: true },
            { name: 'case_number', label: 'Case Number', type: 'text', required: true },
            { name: 'complainant_name', label: 'Complainant Full Name', type: 'text', required: true },
            { name: 'complainant_address', label: 'Complainant Address', type: 'textarea', required: true },
            { name: 'accused_name', label: 'Accused Full Name', type: 'text', required: true },
            { name: 'accused_address', label: 'Accused Address', type: 'textarea', required: true },
            { name: 'cheque_number', label: 'Cheque Number', type: 'text', required: true },
            { name: 'cheque_amount', label: 'Original Cheque Amount (Rs.)', type: 'number', required: true },
            { name: 'settlement_amount', label: 'Agreed Settlement Amount (Rs.)', type: 'number', required: true },
            { name: 'payment_mode', label: 'Mode of Settlement Payment', type: 'select', required: true, options: ['Full upfront payment', 'Instalments (as per schedule)', 'Cheque/DD', 'Online Transfer (NEFT/RTGS)', 'Cash (with receipt)'] },
            { name: 'payment_date', label: 'Date of Payment / First Instalment', type: 'date', required: true },
            { name: 'settlement_date', label: 'Date of This Agreement', type: 'date', required: true },
            { name: 'instalment_details', label: 'Instalment Schedule (if applicable)', type: 'textarea', required: false, placeholder: 'e.g., Rs.50,000 on 01-02-2025, Rs.50,000 on 01-03-2025...' }
        ],
        generate: function (d) {
            return `COMPOUNDING / SETTLEMENT AGREEMENT
UNDER SECTION 147 OF THE NEGOTIABLE INSTRUMENTS ACT, 1881

IN THE ${d.court_name.toUpperCase()}

CASE NO.: ${d.case_number}

${d.complainant_name}                              ...Complainant
VERSUS
${d.accused_name}                                  ...Accused

-------------------------------------------------

This Compounding Agreement is executed on ${formatDraftDate(d.settlement_date)}, between:

PARTY 1 (Complainant):
${d.complainant_name}, residing at ${d.complainant_address} (hereinafter "Complainant")

AND

PARTY 2 (Accused):
${d.accused_name}, residing at ${d.accused_address} (hereinafter "Accused")

WHEREAS:

A. The Complainant had filed a complaint under Section 138 of the Negotiable Instruments Act, 1881, being Case No. ${d.case_number}, before the ${d.court_name}, in relation to dishonour of Cheque No. ${d.cheque_number} for Rs.${Number(d.cheque_amount).toLocaleString('en-IN')}/-.

B. The parties have now arrived at a mutually agreeable full and final settlement of the above dispute without admission of any liability by either party.

NOW, THEREFORE, the parties agree as follows:

1. SETTLEMENT AMOUNT: The Accused agrees to pay and the Complainant agrees to accept a sum of Rs.${Number(d.settlement_amount).toLocaleString('en-IN')}/- (Rupees ${numberToWords(d.settlement_amount)} Only) as full and final settlement of all claims arising out of the above complaint and the underlying dispute.

2. MODE OF PAYMENT: ${d.payment_mode}

3. DATE OF PAYMENT: ${formatDraftDate(d.payment_date)}
${d.instalment_details ? '\n4. INSTALMENT SCHEDULE:\n' + d.instalment_details : ''}

4. NO FURTHER CLAIMS: Upon receipt of the settlement amount, the Complainant agrees that all claims, counter-claims, disputes, and proceedings in relation to the said cheque and underlying transaction shall stand fully and finally settled. The Complainant shall not initiate any fresh proceedings in relation to the same cause of action.

5. WITHDRAWAL OF COMPLAINT: The Complainant agrees to file a Joint Compounding Application before the ${d.court_name} and take all necessary steps for quashing/withdrawal of the above complaint.

6. RETURN OF CHEQUE: Upon receipt of settlement, the Complainant shall return the original cheque to the Accused.

SIGNATURES:

____________________________          ____________________________
${d.complainant_name}                 ${d.accused_name}
(Complainant)                         (Accused)

Date: ${formatDraftDate(d.settlement_date)}

-------------------------------------------------

JOINT APPLICATION FOR COMPOUNDING BEFORE COURT

To,
The Ld. Judicial Magistrate,
${d.court_name}

Sub: Joint Application for Compounding of Offence under Section 147 of the NI Act in Case No. ${d.case_number}

Respectfully Sheweth:

That the Complainant and the Accused have amicably settled the above dispute and the accused has agreed to pay Rs.${Number(d.settlement_amount).toLocaleString('en-IN')}/- as full and final settlement. Both parties jointly pray that:

(a) The offence be compounded under Section 147 of the NI Act;
(b) The complaint be dismissed as withdrawn / settled;
(c) Accused be acquitted on the basis of this compounding.

                    Complainant: ${d.complainant_name}
                    Accused: ${d.accused_name}

Date: ${formatDraftDate(d.settlement_date)}`;
        }
    }
];

// ─── Template Helper Functions ────────────────────────────────────────────────

function formatDraftDate(dateStr) {
    if (!dateStr) return '_______________';
    try {
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return dateStr;
        return d.toLocaleDateString('en-IN', { day: '2-digit', month: 'long', year: 'numeric' });
    } catch (e) { return dateStr; }
}

function numberToWords(num) {
    if (!num || isNaN(num) || num == 0) return 'zero';

    const ones = ['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen'];
    const tens = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety'];

    function convert_less_than_thousand(n) {
        if (n === 0) return '';
        if (n < 20) return ones[n];
        if (n < 100) return tens[Math.floor(n / 10)] + (n % 10 !== 0 ? '-' + ones[n % 10] : '');
        return ones[Math.floor(n / 100)] + ' hundred' + (n % 100 !== 0 ? ' and ' + convert_less_than_thousand(n % 100) : '');
    }

    let n = Math.floor(num);
    let res = '';

    if (n >= 10000000) {
        res += convert_less_than_thousand(Math.floor(n / 10000000)) + ' crore ';
        n %= 10000000;
    }
    if (n >= 100000) {
        res += convert_less_than_thousand(Math.floor(n / 100000)) + ' lakh ';
        n %= 100000;
    }
    if (n >= 1000) {
        res += convert_less_than_thousand(Math.floor(n / 1000)) + ' thousand ';
        n %= 1000;
    }
    if (n > 0) {
        res += convert_less_than_thousand(n);
    }

    return res.trim().toUpperCase();
}

// ─── Screen & UI Functions ────────────────────────────────────────────────────

function openDraftGeneratorScreen(source) {
    draftGenSource = source || (window.caseData && window.caseData.score ? 'results' : 'dashboard');
    hideAllScreens();
    document.getElementById('draftGeneratorScreen').classList.remove('hidden');
    showDraftTypeSelection();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function draftGenGoBack() {
    hideAllScreens();
    if (draftGenSource === 'results' && window.caseData && window.caseData.score) {
        document.getElementById('resultsScreen').classList.remove('hidden');
    } else {
        showDashboard();
    }
}

function showDraftTypeSelection() {
    document.getElementById('draftTypeSelection').classList.remove('hidden');
    document.getElementById('draftInputForm').classList.add('hidden');
    document.getElementById('draftOutputView').classList.add('hidden');
    renderDraftTypeGrid();
}

function showDraftInputForm() {
    document.getElementById('draftTypeSelection').classList.add('hidden');
    document.getElementById('draftInputForm').classList.remove('hidden');
    document.getElementById('draftOutputView').classList.add('hidden');
}

function showDraftOutputView() {
    document.getElementById('draftTypeSelection').classList.add('hidden');
    document.getElementById('draftInputForm').classList.add('hidden');
    document.getElementById('draftOutputView').classList.remove('hidden');
}

function renderDraftTypeGrid() {
    const grid = document.getElementById('draftTypeGrid');
    if (!grid) return;
    grid.innerHTML = DRAFT_TYPES.map(dt => `
        <div class="draft-type-card" onclick="selectDraftType('${dt.id}')">
            <div class="draft-type-num" style="background:${dt.color}18;color:${dt.color}">${dt.number}</div>
            <div class="draft-type-icon-wrap" style="color:${dt.color}">
                <i class="fas ${dt.icon}"></i>
            </div>
            <div class="draft-type-info">
                <h4>${dt.title}</h4>
                <span class="draft-type-sub">${dt.subtitle}</span>
                <p>${dt.description}</p>
            </div>
            <div class="draft-type-chevron" style="color:${dt.color}">
                <i class="fas fa-chevron-right"></i>
            </div>
        </div>
    `).join('');
}

function selectDraftType(id) {
    activeDraftType = DRAFT_TYPES.find(dt => dt.id === id);
    if (!activeDraftType) return;

    document.getElementById('draftSelectedBadge').innerHTML = `
        <span style="background:${activeDraftType.color}18;color:${activeDraftType.color};padding:0.3rem 1rem;border-radius:999px;font-size:0.8rem;font-weight:600;display:inline-flex;align-items:center;gap:0.4rem;">
            <i class="fas ${activeDraftType.icon}"></i> Type ${activeDraftType.number} of 12 &nbsp;·&nbsp; ${activeDraftType.subtitle}
        </span>`;
    document.getElementById('draftFormTitle').textContent = activeDraftType.title;
    document.getElementById('draftFormSubtitle').textContent = activeDraftType.description;

    const pre = buildDraftPrefill();
    const body = document.getElementById('draftFormBody');
    body.innerHTML = activeDraftType.fields.map(f => {
        const val = pre[f.name] || '';
        let inputHtml = '';
        if (f.type === 'textarea') {
            inputHtml = `<textarea id="dfield_${f.name}" class="draft-field-input" ${f.required ? 'required' : ''} placeholder="${f.placeholder || ''}" rows="3">${val}</textarea>`;
        } else if (f.type === 'select') {
            inputHtml = `<select id="dfield_${f.name}" class="draft-field-input" ${f.required ? 'required' : ''}>
                <option value="">-- Select --</option>
                ${(f.options || []).map(o => `<option value="${o}"${val === o ? ' selected' : ''}>${o}</option>`).join('')}
            </select>`;
        } else {
            inputHtml = `<input type="${f.type}" id="dfield_${f.name}" class="draft-field-input" ${f.required ? 'required' : ''} placeholder="${f.placeholder || ''}" value="${val}">`;
        }
        return `<div class="draft-field-group">
            <label class="draft-field-label" for="dfield_${f.name}">
                ${f.label}${f.required ? ' <span class="req-star">*</span>' : ''}
            </label>${inputHtml}
        </div>`;
    }).join('');

    showDraftInputForm();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

function buildDraftPrefill() {
    const map = {};
    try {
        const s = { 
            ...(formData.case_identity || {}), 
            ...(formData.parties || {}), 
            ...(formData.transaction || {}), 
            ...(formData.cheque || {}), 
            ...(formData.dishonour || {}), 
            ...(formData.notice || {}) 
        };
        if (s.complainant_name) map.complainant_name = s.complainant_name;
        if (s.complainant_address) map.complainant_address = s.complainant_address;
        if (s.complainant_phone) map.complainant_phone = s.complainant_phone;
        if (s.accused_name) map.accused_name = s.accused_name;
        if (s.accused_address) map.accused_address = s.accused_address;
        if (s.cheque_number) map.cheque_number = s.cheque_number;
        if (s.cheque_date) map.cheque_date = s.cheque_date;
        if (s.cheque_amount) map.cheque_amount = s.cheque_amount;
        if (s.bank_name) map.bank_name = s.bank_name;
        if (s.branch_name) map.branch_name = s.branch_name;
        if (s.dishonour_date) map.dishonour_date = s.dishonour_date;
        if (s.dishonour_reason) map.dishonour_reason = s.dishonour_reason;
        if (s.court_name) map.court_name = s.court_name;
        if (s.case_id) map.case_number = s.case_id;
        if (s.filing_date) map.filing_date = s.filing_date;
        if (s.notice_date) map.notice_date = s.notice_date;
        if (s.purpose) map.transaction_purpose = s.purpose;
    } catch (e) { }
    return map;
}

function generateDraftFromForm() {
    if (!activeDraftType) return;
    const missing = [];
    const data = {};
    for (const f of activeDraftType.fields) {
        const el = document.getElementById('dfield_' + f.name);
        if (!el) continue;
        const val = el.value.trim();
        if (f.required && !val) {
            missing.push(f.label);
            el.classList.add('field-error');
        } else {
            el.classList.remove('field-error');
            data[f.name] = val;
        }
    }
    if (missing.length > 0) {
        showToast('Please fill: ' + missing.slice(0, 3).join(', ') + (missing.length > 3 ? '...' : ''), 'error', 'Missing Fields');
        return;
    }
    try {
        const txt = activeDraftType.generate(data);
        document.getElementById('generatedDraftContent').value = txt;
        document.getElementById('draftOutputBadge').innerHTML = `
            <span style="background:${activeDraftType.color}18;color:${activeDraftType.color};padding:0.3rem 1rem;border-radius:999px;font-size:0.8rem;font-weight:600;display:inline-flex;align-items:center;gap:0.4rem;">
                <i class="fas ${activeDraftType.icon}"></i> Draft ${activeDraftType.number} – ${activeDraftType.subtitle}
            </span>`;
        document.getElementById('draftOutputTitle').textContent = activeDraftType.title;
        showDraftOutputView();
        window.scrollTo({ top: 0, behavior: 'smooth' });
        showToast('Draft generated successfully!', 'success', 'Ready');
    } catch (err) {
        showToast('Error generating draft. Check your inputs.', 'error');
        console.error('Draft error:', err);
    }
}

function copyGeneratedDraft() {
    const ta = document.getElementById('generatedDraftContent');
    ta.select();
    document.execCommand('copy');
    showToast('Draft copied to clipboard!', 'success', 'Copied');
}

function downloadGeneratedDraft() {
    const content = document.getElementById('generatedDraftContent').value;
    if (!content) { showToast('Nothing to download', 'warning'); return; }
    const name = activeDraftType ? activeDraftType.id : 'draft';
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = `JUDIQ_${name}_${Date.now()}.txt`; a.click();
    URL.revokeObjectURL(url);
    showToast('Downloaded!', 'success');
}

function printGeneratedDraft() {
    const content = document.getElementById('generatedDraftContent').value;
    const win = window.open('', '_blank');
    win.document.write(`<html><head><title>JUDIQ AI – Legal Draft</title>
    <style>body{font-family:'Courier New',monospace;font-size:12px;padding:2cm;line-height:1.8;white-space:pre-wrap;color:#111;}</style>
    </head><body>${content.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')}</body></html>`);
    win.document.close(); win.print();
}

// Register globally
window.openDraftGeneratorScreen = openDraftGeneratorScreen;
window.draftGenGoBack = draftGenGoBack;
window.showDraftTypeSelection = showDraftTypeSelection;
window.showDraftInputForm = showDraftInputForm;
window.selectDraftType = selectDraftType;
window.generateDraftFromForm = generateDraftFromForm;
window.copyGeneratedDraft = copyGeneratedDraft;
window.downloadGeneratedDraft = downloadGeneratedDraft;
window.printGeneratedDraft = printGeneratedDraft;
// ---------------------------------------------------------------------------
// SMART UPLOAD FUNCTIONS
// ---------------------------------------------------------------------------

function openSmartUpload() {
    const modal = document.getElementById("uploadModal");
    if (!modal) return;
    modal.classList.remove("hidden");
    setTimeout(() => modal.classList.add("active"), 10);

    // Reset modal state
    const zone = document.getElementById("uploadZone");
    const progress = document.getElementById("uploadProgress");
    const results = document.getElementById("extractionResults");
    if (zone) zone.classList.remove("hidden");
    if (progress) progress.classList.add("hidden");
    if (results) results.classList.add("hidden");
}

function closeUploadModal() {
    const modal = document.getElementById("uploadModal");
    if (!modal) return;
    modal.classList.remove("active");
    setTimeout(() => modal.classList.add("hidden"), 300);
}

// Drag and Drop Logic
document.addEventListener("DOMContentLoaded", () => {
    const zone = document.getElementById("uploadZone");
    const input = document.getElementById("fileInput");

    if (!zone || !input) return;

    zone.addEventListener("dragover", (e) => {
        e.preventDefault();
        zone.classList.add("drag-over");
    });

    zone.addEventListener("dragleave", () => {
        zone.classList.remove("drag-over");
    });

    zone.addEventListener("drop", (e) => {
        e.preventDefault();
        zone.classList.remove("drag-over");
        if (e.dataTransfer.files.length) {
            handleFileUpload(e.dataTransfer.files[0]);
        }
    });

    input.addEventListener("change", (e) => {
        if (e.target.files.length) {
            handleFileUpload(e.target.files[0]);
        }
    });
});

async function handleFileUpload(file) {
    const zone = document.getElementById("uploadZone");
    const progress = document.getElementById("uploadProgress");
    const progressFill = document.getElementById("uploadProgressFill");
    const status = document.getElementById("uploadStatus");

    if (!zone || !progress || !progressFill || !status) return;

    zone.classList.add("hidden");
    progress.classList.remove("hidden");

    status.textContent = "Uploading document...";
    progressFill.style.width = "30%";

    const uploadData = new FormData();
    uploadData.append("file", file);

    try {
        const response = await fetch(`${API_BASE_URL}/upload-doc`, {
            method: "POST",
            body: uploadData
        });

        status.textContent = "Extracting legal intelligence...";
        progressFill.style.width = "70%";

        const data = await response.json();

        if (data.status === "success" || data.status === "partial") {
            progressFill.style.width = "100%";
            setTimeout(() => {
                progress.classList.add("hidden");
                showExtractionResults(data.text);
                if (data.status === "partial") {
                    showToast("Some text could not be extracted", "warning");
                }
            }, 500);
        } else {
            throw new Error(data.message || "Upload failed");
        }
    } catch (error) {
        showToast(error.message, "error", "Upload Failed");
        zone.classList.remove("hidden");
        progress.classList.add("hidden");
    }
}


function showExtractionResults(text) {
    const results = document.getElementById("extractionResults");
    const preview = document.getElementById("extractedTextPreview");

    if (results && preview) {
        results.classList.remove("hidden");
        preview.value = text || "No text could be extracted from this document.";
    }
}

function proceedWithExtractedText() {
    const preview = document.getElementById("extractedTextPreview");
    if (!preview) return;
    const text = preview.value;
    if (!text || text.length < 10) {
        showToast("Insufficient text to analyze", "warning");
        return;
    }

    closeUploadModal();

    // Start case analysis with pre-filled extracted text
    const initialData = {
        transaction: { purpose: text.substring(0, 1000) },
        settlement: { additional_notes: text }
    };
    
    startCaseAnalysis(initialData);
    showToast("Wizard pre-filled with extracted data", "success");
}


window.openSmartUpload = openSmartUpload;
window.closeUploadModal = closeUploadModal;
window.proceedWithExtractedText = proceedWithExtractedText;

// ════════════════════════════════════════════════════════════════════════════
// AI REASONING LAYER — Complete Frontend Renderer (v2)
// Auto-called by renderFullReport() after every analysis.
// ════════════════════════════════════════════════════════════════════════════

function renderAIReasoningLayer(data) {
    if (!data) return;
    console.log('🧠 Rendering AI Reasoning Layer…');

    // ── 1. Case Summary ────────────────────────────────────────────────────
    const summaryEl = document.getElementById('aiCaseSummary');
    if (summaryEl) {
        summaryEl.textContent = data.case_summary || 'No automated summary generated.';
    }

    // ── 2. Translated Verdict Badge ────────────────────────────────────────
    const badgeEl = document.getElementById('translatedVerdictBadge');
    if (badgeEl) {
        if (data.translated_verdict && data.translated_verdict !== data.verdict) {
            badgeEl.innerHTML = `<i class="fas fa-language"></i>&nbsp;${data.translated_verdict}`;
            badgeEl.classList.remove('hidden');
        } else {
            badgeEl.classList.add('hidden');
        }
    }

    // ── 3. Outcome Prediction ──────────────────────────────────────────────
    const predEl = document.getElementById('aiOutcomePrediction');
    if (predEl) {
        const op = data.outcome_prediction || {};
        if (op.prediction) {
            const probText = String(op.probability || '0%');
            const probValue = parseFloat(probText) || 0;
            const band = (op.score_band || 'WEAK').toUpperCase();
            
            predEl.innerHTML = `
                <div class="rl-outcome-box rl-band-${band}">
                    <div class="rl-outcome-header">
                        <span class="rl-outcome-prediction">${op.prediction}</span>
                        <span class="rl-outcome-prob">${probText}</span>
                    </div>
                    <div class="rl-outcome-bar-wrap">
                        <div class="rl-outcome-bar" style="width:${Math.min(probValue, 100)}%"></div>
                    </div>
                    <p class="rl-outcome-rationale">${op.rationale || ''}</p>
                </div>`;
        } else {
            predEl.innerHTML = '<p class="rl-empty">No outcome prediction available.</p>';
        }
    }

    // ── 4. Statutory Interpretation ────────────────────────────────────────
    const statuteEl = document.getElementById('aiStatutoryInterpretation');
    if (statuteEl) {
        const interps = data.statutory_interpretation || [];
        if (!interps.length) {
            statuteEl.innerHTML = '<p class="rl-empty">No statutory analysis available.</p>';
        } else {
            statuteEl.innerHTML = interps.map(interp => {
                // Normalize status for CSS class (e.g. "SATISFIED" or "DEFECTIVE")
                const rawStatus = (interp.status || 'NOTE').toUpperCase();
                const statusClass = rawStatus.replace(/\s+/g, '_');
                const failList = (interp.conditions_failed || []).map(c => `• ${c}`).join('<br>');
                
                return `
                <div class="rl-statute-card status-${statusClass}">
                    <div class="rl-statute-section">Section ${interp.section}</div>
                    <div class="rl-statute-title">${interp.title || ''}</div>
                    <span class="rl-statute-status-badge">${interp.status}</span>
                    <div class="rl-statute-finding">${interp.finding || ''}</div>
                    ${failList ? `<div style="margin-top:.6rem;font-size:.78rem;color:#b91c1c;"><strong>Unmet Conditions:</strong><br>${failList}</div>` : ''}
                    ${interp.punishment ? `<div style="margin-top:.5rem;font-size:.78rem;color:var(--gray-500);">Penalty: ${interp.punishment}</div>` : ''}
                    ${interp.limit ? `<div style="margin-top:.5rem;font-size:.78rem;color:#6d28d9;">${interp.limit}</div>` : ''}
                </div>`;
            }).join('');
        }
    }

    // ── 5. Matched Precedents ──────────────────────────────────────────────
    const precEl = document.getElementById('aiMatchedPrecedents');
    if (precEl) {
        const precs = data.precedents || [];
        if (!precs.length) {
            precEl.innerHTML = '<p class="rl-empty">No precedents matched for detected concepts.</p>';
        } else {
            precEl.innerHTML = precs.map(p => `
                <div class="rl-precedent-card">
                    <div class="rl-precedent-case">
                        ${p.case || p.citation || 'Unknown Case'}
                        ${p.is_live ? '<span class="rl-prec-live">⚡ Live</span>' : ''}
                    </div>
                    <div class="rl-precedent-citation">${p.citation || ''}</div>
                    ${p.court ? `<div style="font-size:.75rem;color:var(--gray-400);margin-bottom:.4rem;">${p.court}</div>` : ''}
                    <div class="rl-precedent-principle">${p.principle || p.precedent || ''}</div>
                    <div class="rl-precedent-relevance">
                        <i class="fas fa-star"></i> Relevance: ${Math.round((p.relevance || 0) * 100)}%
                        &nbsp;·&nbsp;<span style="text-transform:uppercase;font-size:.7rem;">${(p.concept || '').replace(/_/g, ' ')}</span>
                    </div>
                </div>`).join('');
        }
    }

    // ── 6. Risks & Rebuttals ───────────────────────────────────────────────
    const risksEl = document.getElementById('aiRisksRebuttals');
    if (risksEl) {
        const risks = data.risks_and_rebuttals || [];
        if (!risks.length) {
            risksEl.innerHTML = '<p class="rl-empty">No specific risks identified for current case configuration.</p>';
        } else {
            risksEl.innerHTML = risks.map(r => `
                <div class="rl-risk-item sev-${r.severity}">
                    <div class="rl-risk-header sev-${r.severity}">
                        <span class="rl-sev-badge">${r.severity}</span>
                        <span class="rl-risk-title">${r.risk}</span>
                    </div>
                    <div class="rl-risk-desc">${r.description || ''}</div>
                    <div class="rl-rebuttal-box">
                        <strong><i class="fas fa-reply"></i> AI-Suggested Rebuttal</strong>
                        <div class="rl-rebuttal-text">${r.rebuttal || ''}</div>
                        ${r.case_law ? `<div class="rl-case-law"><i class="fas fa-book-open"></i> ${r.case_law}</div>` : ''}
                    </div>
                </div>`).join('');
        }
    }

    // ── 7. Evidence Suggestions ────────────────────────────────────────────
    const evEl = document.getElementById('aiEvidenceSuggestions');
    if (evEl) {
        const suggestions = data.evidence_suggestions || [];
        if (!suggestions.length) {
            evEl.innerHTML = '<p class="rl-empty" style="color:var(--success-600);"><i class="fas fa-check-circle"></i> No critical evidence gaps detected.</p>';
        } else {
            evEl.innerHTML = suggestions.map(s => `
                <div class="rl-evidence-item">
                    <i class="fas fa-file-search"></i>
                    <span>${s}</span>
                </div>`).join('');
        }
    }

    // ── 8. Reasoning Trail ─────────────────────────────────────────────────
    const trailEl = document.getElementById('aiReasoningTrail');
    if (trailEl) {
        const trail = data.reasoning_trail || [];
        if (!trail.length) {
            trailEl.innerHTML = '<p class="rl-empty">No reasoning trail available.</p>';
        } else {
            trailEl.innerHTML = trail.map((step, i) => {
                const match = step.match(/^(STEP[\s\S]*?(?:—[^:]*)?)\s*[—:]\s*([\s\S]+)/i);
                const label   = match ? match[1].trim() : `Step ${i + 1}`;
                const content = match ? match[2].trim() : step;
                return `
                <div class="rl-trail-item">
                    <div class="rl-trail-step">${label}</div>
                    <div>${content}</div>
                </div>`;
            }).join('');
        }
    }

    console.log('✅ AI Reasoning Layer rendered successfully.');
}

// ==========================================================================
// COLLABORATIVE CASEROOM ENGINE
// ==========================================================================
let currentCaseroomId = null;
let caseroomInterval = null;

async function initCaseroom() {
    if (!currentAnalysisResult || !currentAnalysisResult.case_id) {
        showToast('Please analyze a case first.', 'warning');
        return;
    }

    const caseId = currentAnalysisResult.case_id;
    const userId = currentUser?.uid || 'LEAD_ADVOCATE';

    try {
        showAnalysisLoading('Initializing Secure Caseroom...');
        const response = await fetch(`${API_BASE_URL}/caseroom/create`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ case_id: caseId, user_id: userId })
        });
        
        const result = await response.json();
        if (result.success) {
            currentCaseroomId = result.caseroom_id;
            showToast('Caseroom Created Successfully!', 'success');
            startCaseroomSync();
        } else {
            showToast('Failed to create caseroom.', 'error');
        }
    } catch (error) {
        console.error('Caseroom Init Error:', error);
    } finally {
        hideAnalysisLoading();
    }
}

function startCaseroomSync() {
    if (caseroomInterval) clearInterval(caseroomInterval);
    refreshCaseroom();
    caseroomInterval = setInterval(refreshCaseroom, 5000); // Poll every 5s
}

async function refreshCaseroom() {
    if (!currentCaseroomId) return;

    try {
        const response = await fetch(`${API_BASE_URL}/caseroom/${currentCaseroomId}`);
        const result = await response.json();
        if (result.success) {
            renderCaseroom(result.data);
        }
    } catch (error) {
        console.error('Caseroom Sync Error:', error);
    }
}

function renderCaseroom(data) {
    const chatBox = document.getElementById('caseroomChat');
    const chatControls = document.getElementById('chatControls');
    const participantsEl = document.getElementById('crParticipants');
    const caseIdEl = document.getElementById('crCaseId');
    const timelineEl = document.getElementById('caseroomTimeline');

    caseIdEl.textContent = data.room_info[2]; // case_id is at index 2

    // Show controls if active
    chatControls.classList.remove('hidden');

    // Render Participants
    participantsEl.innerHTML = data.participants.map(p => `
        <div class="participant-avatar" title="${p.user_id} (${p.role})">
            ${p.user_id.charAt(0).toUpperCase()}
        </div>
    `).join('');

    // Render Messages
    if (data.messages.length > 0) {
        chatBox.innerHTML = data.messages.map(m => {
            const isMe = m.user_id === (currentUser?.uid || 'LEAD_ADVOCATE');
            const type = m.user_id === 'SYSTEM' ? 'system' : (isMe ? 'user' : 'other');
            return `
                <div class="chat-bubble ${type}">
                    <strong>${m.user_id}:</strong> ${m.content}
                    <div style="font-size: 8px; opacity: 0.6; text-align: right;">${new Date(m.timestamp).toLocaleTimeString()}</div>
                </div>
            `;
        }).join('');
        chatBox.scrollTop = chatBox.scrollHeight;
    }

    // Render Tasks/Milestones
    if (data.tasks.length > 0) {
        timelineEl.innerHTML = data.tasks.map(t => `
            <div class="timeline-milestone">
                <div style="font-weight: 600; font-size: 13px;">${t.title}</div>
                <div style="font-size: 11px; color: var(--gray-500);">${t.due_date} | ${t.status}</div>
            </div>
        `).join('');
    } else {
        timelineEl.innerHTML = '<div class="evidence-empty">No milestones added.</div>';
    }
}

async function sendMessage() {
    const input = document.getElementById('chatInput');
    const text = input.value.trim();
    if (!text || !currentCaseroomId) return;

    try {
        const response = await fetch(`${API_BASE_URL}/caseroom/${currentCaseroomId}/message`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: currentUser?.uid || 'LEAD_ADVOCATE', content: text })
        });
        const result = await response.json();
        if (result.success) {
            input.value = '';
            refreshCaseroom();
        }
    } catch (error) {
        console.error('Message Send Error:', error);
    }
}

async function addTask() {
    const title = prompt("Enter Milestone Title:");
    if (!title || !currentCaseroomId) return;
    const date = new Date().toISOString().split('T')[0];

    try {
        const response = await fetch(`${API_BASE_URL}/caseroom/${currentCaseroomId}/task`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title, due_date: date, description: "Added from Caseroom" })
        });
        const result = await response.json();
        if (result.success) {
            showToast('Milestone Added', 'success');
            refreshCaseroom();
        }
    } catch (error) {
        console.error('Task Add Error:', error);
    }
}

// ─── Global init ──────────────────────────────────────────────────────────────
// Run once when the page is ready
(function initJudiQ() {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', _boot);
    } else {
        _boot();
    }
    function _boot() {
        initNetworkMonitor();
        console.log('🏛️  JudiQ Legal AI — Reliability Layer active.');
    }
})();

