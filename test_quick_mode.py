
from normalizer import normalize_input, validate_minimum_viability

# Test Quick Mode
quick_data = {
    "analysis_mode": "quick",
    "cheque_date": "2023-10-01",
    "amount": 50000,
    "notice_date": "2023-10-15",
    "filing_date": "2023-11-20",
    "complainant_name": "John Doe",
    "accused_name": "Jane Smith",
    "proof_present": False
}

normalized = normalize_input(quick_data)
is_valid, errors = validate_minimum_viability(normalized)

print(f"Normalized: {normalized.get('analysis_mode')}")
print(f"Is Valid: {is_valid}")
print(f"Errors: {errors}")

# Test Detailed Mode (should fail with minimal data)
detailed_data = quick_data.copy()
detailed_data["analysis_mode"] = "detailed"
normalized_detailed = normalize_input(detailed_data)
is_valid_detailed, errors_detailed = validate_minimum_viability(normalized_detailed)

print(f"\nDetailed Is Valid: {is_valid_detailed}")
print(f"Detailed Errors count: {len(errors_detailed)}")
