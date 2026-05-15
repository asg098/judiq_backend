# JUDIQ AI: The Litigation Operating System v12.000

![JudiQ AI Banner](https://img.shields.io/badge/Status-Institutional_Beta-gold?style=for-the-badge)
![License](https://img.shields.io/badge/License-Proprietary-navy?style=for-the-badge)
![Compliance](https://img.shields.io/badge/Compliance-DPDP_2023_|_BCI-blue?style=for-the-badge)

**Win the Courtroom Before You Step In.**

JudiQ AI is an advanced legal intelligence platform engineered for Indian legal practitioners, law firms, and institutional legal departments. Specializing in **Section 138 NI Act (Cheque Bounce)** litigation, JudiQ transforms raw case data into courtroom-ready strategy, forensic audits, and high-fidelity legal drafts.

---

## 🏛️ Core Intelligence Layers

JudiQ AI doesn't just read documents; it understands the adversarial chess game of litigation.

### 1. Forensic Audit & Evidence Verification
*   **Physical Evidence Audit**: Forensic analysis of Bank Return Memos, Statutory Notices, and Service Proofs.
*   **OCR Engine**: Automated extraction and verification of data from bank memos to detect fatal defects (e.g., mismatch in return reasons).
*   **Causal Link Detection**: Validates the nexus between the underlying debt and the cheque issuance.

### 2. Digital Senior Partner (Reasoning Engine)
*   **Precedent Calibration**: Logic calibrated against landmark Supreme Court judgments (e.g., *Basalingappa vs. Mudibasappa*, *Rangappa vs. Sri Mohan*).
*   **Cognitive Reporting**: Generates "Causal Story" builders and "Timeline Anomaly" detectors.
*   **Judicial Mode**: Switch between *Balanced*, *Cynical*, and *Forensic* experience modes for different analytical depths.

### 3. Adversarial Simulation (Hostile Mode)
*   **Case Collapse Scenarios**: Simulates exact cross-examination questions and defense arguments likely to be raised.
*   **Critical Failure Points**: Identifies the single most probable reason your case might fail in court.
*   **Witness Stability Simulation**: Analyzes psychological stability and potential pressure points in witness testimony.

### 4. Litigation Operating System (Workflow)
*   **Jurisdiction Mapping**: Real-time mapping under Section 142(2) NI Act (Post-2015 Amendments) to suggest the correct court.
*   **Draft Generator**: AI-powered generation of Complaints, Legal Notices, and Evidence Affidavits.
*   **Caseroom**: A secure, collaborative workspace for document storage, task management, and physical evidence intelligence.

---

## 🛡️ Institutional-Grade Security & Compliance

*   **Sovereign Cloud**: All data processed and stored within Indian borders (Mumbai Region).
*   **DPDP 2023 Compliant**: Engineered with "Privacy by Design" principles in accordance with the Digital Personal Data Protection Act.
*   **BCI Verified Architecture**: Designed to augment, not replace, legal counsel, adhering to Bar Council of India standards.
*   **End-to-End Encryption**: Documents are encrypted using AES-256 before being stored.
*   **Adversarial Telemetry**: Real-time monitoring for malicious payload patterns and abnormal valuations.

---

## 🚀 Tech Stack

### Backend
*   **Language**: Python 3.10+
*   **Framework**: FastAPI (Asynchronous High-Performance API)
*   **Database**: PostgreSQL (Structured Case Data & Audit Logs)
*   **Security**: Cryptography (Fernet/AES-256), Pydantic (Data Validation)
*   **AI Integration**: Reasoning-aware prompt engineering via OpenAI/Anthropic/Google Vertex AI.
*   **OCR**: Tesseract & PDFPlumber for document intelligence.

### Frontend
*   **Architecture**: Single Page Application (SPA)
*   **UI/UX**: Vanilla JavaScript (ES6+), CSS3 (Custom Navy-and-Gold Glassmorphic Design System).
*   **Aesthetics**: Premium, institutionally branded interface with smooth micro-animations.

---

## 🛠️ Installation & Setup

### Prerequisites
- Python 3.10 or higher
- Node.js (optional, for frontend dev server)
- PostgreSQL

### Backend Setup
1.  Navigate to the `backend` directory:
    ```bash
    cd backend
    ```
2.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Set environment variables (create a `.env` file):
    ```env
    DATABASE_URL=postgresql://user:password@localhost/judiq
    OPENAI_API_KEY=your_key_here
    ENCRYPTION_KEY=your_32_byte_fernet_key
    ```
4.  Run the server:
    ```bash
    python api.py
    ```

### Frontend Setup
1.  The frontend is located in the `frontend` directory.
2.  Open `index.html` in a browser or serve it using any static file server:
    ```bash
    npx serve frontend
    ```

---

## 📂 Project Structure

```text
├── backend/
│   ├── api.py                  # FastAPI Entry Point
│   ├── engine_core.py          # Main Reasoning Logic
│   ├── adversarial_engine.py   # Defense Simulation
│   ├── caseroom_logic.py       # Collaborative Workspace Logic
│   ├── database_manager.py     # SQLAlchemy ORM
│   ├── draft_engine.py         # AI Drafting Logic
│   ├── ocr_engine.py           # Document Intelligence
│   └── ...                     # Specialized Analytical Engines
├── frontend/
│   ├── index.html              # Main SPA Template
│   ├── script.js               # Dashboard & Wizard Logic
│   └── styles.css              # Premium Design System
└── strategy_engine.py          # Standalone Strategy Tester
```

---

## ⚖️ Legal Disclaimer

JudiQ AI is a legal intelligence tool designed to assist qualified legal professionals. It does **not** provide legal advice. All outputs and drafts must be reviewed, verified, and signed by a licensed advocate before being filed in any court of law.

---

© 2026 JudiQ AI. Built for the Institutional Courtroom.
