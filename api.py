==> Running 'uvicorn api:app --host 0.0.0.0 --port $PORT'
INFO:     Started server process [38]
INFO:     Waiting for application startup.
INFO:database_manager:Database initialized successfully.
INFO:JudiQ-API:JudiQ Backend Started | Database Initialized
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:10000 (Press CTRL+C to quit)
INFO:     103.97.166.114:0 - "OPTIONS /analyze HTTP/1.1" 405 Method Not Allowed
INFO:     103.97.166.114:0 - "OPTIONS /analyze HTTP/1.1" 405 Method Not Allowed
DEBUG TEXT: Cheque issued for loan repayment. Written agreement exists. Legal notice sent. No payment made.
DEBUG CONCEPTS: ['legal_notice_compliance', 'legally_enforceable_debt']
INFO:     35.194.133.39:0 - "POST /analyze HTTP/1.1" 200 OK
DEBUG TEXT: Cheque bounced but no legal notice was sent within time.
DEBUG CONCEPTS: ['cheque_bounce', 'notice_defect']
INFO:     35.194.133.39:0 - "POST /analyze HTTP/1.1" 200 OK
DEBUG TEXT: Cheque was given as security for business. No agreement exists.
DEBUG CONCEPTS: ['no_agreement', 'security_cheque', 'no_debt_proof']
INFO:     35.194.133.39:0 - "POST /analyze HTTP/1.1" 200 OK
Menu
DEBUG TEXT: Cheque was stolen and misused. No legally enforceable debt exists.
DEBUG CONCEPTS: ['cheque_misuse', 'no_debt_proof']
INFO:     35.194.133.39:0 - "POST /analyze HTTP/1.1" 200 OK
DEBUG TEXT: Signature on cheque is not mine. Forged signature.
DEBUG CONCEPTS: ['signature_dispute']
INFO:     35.194.133.39:0 - "POST /analyze HTTP/1.1" 200 OK
DEBUG TEXT: Loan claimed but no written proof exists. Only oral agreement.
DEBUG CONCEPTS: ['no_agreement', 'no_debt_proof']
INFO:     35.194.133.39:0 - "POST /analyze HTTP/1.1" 200 OK
INFO:     103.97.166.114:0 - "OPTIONS /analyze HTTP/1.1" 405 Method Not Allowed
INFO:     103.97.166.114:0 - "OPTIONS /analyze HTTP/1.1" 405 Method Not Allowed
