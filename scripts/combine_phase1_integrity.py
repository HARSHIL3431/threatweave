"""
Phase 1: Source Dataset Integrity Verification
================================================
Re-verify SHA-256 checksums of all 8 CICIDS2017 source CSVs against 
the stored baselines in reports/DATASET_CHECKSUMS.md.

If ANY checksum fails, the script will HALT with a critical error.
"""
import os
import hashlib
import sys
import json
import datetime

DATASET_DIR = "dataset"
EXPECTED_CHECKSUMS = {
    "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv": "6ff1580f5f81c0ae28a26f7631721018577f5f7c5e0feac28b795fcfe7b411ee",
    "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv": "ca1824c51bfbb7b3c72290a11be04366ba8815878c6a1cc5c44cb1cee269e99b",
    "Friday-WorkingHours-Morning.pcap_ISCX.csv": "53a41c24d570ea83b7ac55b2e94df94e7a8216aeb80a2af0246b6bc8bb543000",
    "Monday-WorkingHours.pcap_ISCX.csv": "852c4beb34eda186f32561fa79df7a0747e92e1a6535b01270820dd9ffe17f34",
    "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv": "6bcda3857c2504676034e3ea57762d38393cc734cb377a726bd5cb153961b1b5",
    "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv": "d67066211fb1689c78406f1506f4c44704ecb92088353d5c96d96d6474eb819d",
    "Tuesday-WorkingHours.pcap_ISCX.csv": "52b8692ae8c7d2ed04671fe2b98335693c0a92c7ab157d8c8b534d6523080851",
    "Wednesday-workingHours.pcap_ISCX.csv": "893c27dc968bf7a8adef1689f90be55ca4a4dc3088fb63d6ff247ac56856df2a",
}

EXPECTED_SIZES = {
    "Friday-WorkingHours-Afternoon-DDos.pcap_ISCX.csv": 77123859,
    "Friday-WorkingHours-Afternoon-PortScan.pcap_ISCX.csv": 76906168,
    "Friday-WorkingHours-Morning.pcap_ISCX.csv": 58316725,
    "Monday-WorkingHours.pcap_ISCX.csv": 176927918,
    "Thursday-WorkingHours-Afternoon-Infilteration.pcap_ISCX.csv": 83102436,
    "Thursday-WorkingHours-Morning-WebAttacks.pcap_ISCX.csv": 52023263,
    "Tuesday-WorkingHours.pcap_ISCX.csv": 135078995,
    "Wednesday-workingHours.pcap_ISCX.csv": 225166395,
}

def compute_sha256(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(65536 * 16), b""):
            sha256.update(chunk)
    return sha256.hexdigest()

def main():
    print("=" * 70)
    print("PHASE 1: SOURCE DATASET INTEGRITY VERIFICATION")
    print(f"Timestamp: {datetime.datetime.now().isoformat()}")
    print("=" * 70)
    
    results = []
    all_passed = True
    
    # Check that all 8 expected files exist
    for filename in sorted(EXPECTED_CHECKSUMS.keys()):
        filepath = os.path.join(DATASET_DIR, filename)
        entry = {"filename": filename, "exists": False, "size_match": False, "checksum_match": False}
        
        if not os.path.isfile(filepath):
            print(f"[CRITICAL] MISSING: {filename}")
            entry["error"] = "File not found"
            all_passed = False
            results.append(entry)
            continue
        
        entry["exists"] = True
        
        # Verify file size
        actual_size = os.path.getsize(filepath)
        expected_size = EXPECTED_SIZES[filename]
        if actual_size != expected_size:
            print(f"[CRITICAL] SIZE MISMATCH: {filename}")
            print(f"  Expected: {expected_size:,} bytes")
            print(f"  Actual:   {actual_size:,} bytes")
            entry["error"] = f"Size mismatch: expected {expected_size}, got {actual_size}"
            all_passed = False
            results.append(entry)
            continue
        
        entry["size_match"] = True
        entry["actual_size"] = actual_size
        print(f"[OK] Size verified: {filename} ({actual_size:,} bytes)")
        
        # Verify SHA-256 checksum
        print(f"  Computing SHA-256 for {filename}...", end=" ", flush=True)
        actual_hash = compute_sha256(filepath)
        expected_hash = EXPECTED_CHECKSUMS[filename]
        
        if actual_hash != expected_hash:
            print("FAILED!")
            print("  [CRITICAL] CHECKSUM MISMATCH!")
            print(f"  Expected: {expected_hash}")
            print(f"  Actual:   {actual_hash}")
            entry["error"] = f"Checksum mismatch"
            entry["expected_hash"] = expected_hash
            entry["actual_hash"] = actual_hash
            all_passed = False
        else:
            print("PASSED [OK]")
            entry["checksum_match"] = True
            entry["sha256"] = actual_hash
        
        results.append(entry)
    
    # Check for unexpected files
    actual_files = set(f for f in os.listdir(DATASET_DIR) if f.endswith(".csv"))
    expected_files = set(EXPECTED_CHECKSUMS.keys())
    unexpected = actual_files - expected_files
    if unexpected:
        print(f"\n[WARNING] Unexpected CSV files found in {DATASET_DIR}/:")
        for uf in sorted(unexpected):
            print(f"  - {uf}")
    
    # Summary
    passed = sum(1 for r in results if r.get("checksum_match"))
    failed = len(results) - passed
    
    print("\n" + "=" * 70)
    print(f"INTEGRITY VERIFICATION RESULT: {'ALL PASSED' if all_passed else 'FAILED'}")
    print(f"  Files verified: {passed}/8")
    print(f"  Files failed:   {failed}/8")
    print("=" * 70)
    
    # Save verification result as JSON
    os.makedirs("reports", exist_ok=True)
    verification_result = {
        "phase": "Phase 1: Source Integrity Verification",
        "timestamp": datetime.datetime.now().isoformat(),
        "all_passed": all_passed,
        "files_verified": passed,
        "files_failed": failed,
        "results": results,
    }
    with open("reports/combine_phase1_integrity.json", "w") as f:
        json.dump(verification_result, f, indent=2)
    print(f"\nSaved: reports/combine_phase1_integrity.json")
    
    if not all_passed:
        print("\n[CRITICAL] HALTING: Source dataset integrity compromised. Cannot proceed with combination.")
        sys.exit(1)
    else:
        print("\n[OK] All 8 source datasets are byte-identical to their EDA baselines.")
        print("[OK] Safe to proceed with Phase 2: Schema Harmonization & Controlled Concatenation.")

if __name__ == "__main__":
    main()
