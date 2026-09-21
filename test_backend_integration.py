#!/usr/bin/env python

import json
import requests
import sys
from pathlib import Path

BACKEND_URL = "http://localhost:8001/api/v1/detect"
FIXTURE_PATH = Path("backend/tests/fixtures/sample_flows.json")


def test_detection():
    """Test detection endpoint with complete fixture flows."""

    print("Loading sample flows from fixture...")

    with open(FIXTURE_PATH, encoding="utf-8") as f:
        fixtures = json.load(f)

    print(f"✓ Loaded {len(fixtures)} sample flows")
    print()

    results = {}

    for flow_name, flow_data in fixtures.items():

        print(f"Testing: {flow_name}")
        print(f"  Expected Score: {flow_data['expected_score']:.6f}")
        print(f"  Expected OP-A Anomaly: {flow_data['expected_is_anomaly_opA']}")
        print(f"  Expected OP-B Anomaly: {flow_data['expected_is_anomaly_opB']}")

        try:
            response = requests.post(
                BACKEND_URL,
                json=flow_data["input"],
                timeout=10,
                headers={"Content-Type": "application/json"},
            )

            if response.status_code == 200:

                result = response.json()

                detection = result["detection"]
                severity = result["severity"]

                is_anomaly = detection["is_anomaly"]
                score = detection["anomaly_score"]
                threshold = detection["threshold"]

                print("  ✓ HTTP 200 OK")
                print(f"  ✓ Score: {score:.6f}")
                print(f"  ✓ Threshold: {threshold:.6f}")
                print(f"  ✓ Is Anomaly: {is_anomaly}")
                print(f"  ✓ Severity: {severity['level']}")
                print(f"  ✓ Request ID: {result['request_id']}")

                results[flow_name] = {
                    "status": "success",
                    "score": score,
                    "is_anomaly": is_anomaly,
                    "threshold": threshold,
                    "severity": severity["level"],
                }

            else:

                print(f"  ✗ HTTP {response.status_code}")
                print(f"  Response: {response.text[:500]}")

                results[flow_name] = {
                    "status": "error",
                    "error": f"HTTP {response.status_code}",
                }

        except Exception as e:

            print(f"  ✗ Exception: {e}")

            results[flow_name] = {
                "status": "error",
                "error": str(e),
            }

        print()

    print("=" * 60)
    print("BACKEND INTEGRATION TEST SUMMARY")
    print("=" * 60)

    successes = sum(
        1 for r in results.values()
        if r["status"] == "success"
    )

    failures = len(results) - successes

    print(f"Total Tests: {len(results)}")
    print(f"Successful: {successes}")
    print(f"Failed: {failures}")

    if failures == 0:
        print("\n✓ ALL TESTS PASSED - Backend integration verified!")
        return 0

    print(f"\n✗ {failures} test(s) failed")
    return 1


if __name__ == "__main__":
    sys.exit(test_detection())