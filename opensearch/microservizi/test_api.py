"""
Script di test per verificare il funzionamento dell'API MSSQL
"""

import requests
import json
import time
from typing import Dict, Any

API_URL = "http://localhost:8000"


def test_health_check():
    """Test health check endpoint"""
    print("🔍 Test Health Check...")
    try:
        response = requests.get(f"{API_URL}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ❌ Errore: {str(e)}")
        return False


def test_insert():
    """Test inserimento dati"""
    print("\n📝 Test Insert...")
    data = {
        "table_name": "employees",
        "data": [
            {
                "id": 100,
                "name": "Test User",
                "email": "test@example.com",
                "department": "Testing",
                "salary": 40000,
                "hire_date": "2024-01-01"
            }
        ]
    }

    try:
        response = requests.post(f"{API_URL}/api/v1/insert", json=data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ❌ Errore: {str(e)}")
        return False


def test_update():
    """Test aggiornamento dati"""
    print("\n✏️  Test Update...")
    data = {
        "table_name": "employees",
        "data": {
            "department": "Updated Testing",
            "salary": 45000
        },
        "where": {
            "id": 100
        }
    }

    try:
        response = requests.post(f"{API_URL}/api/v1/update", json=data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ❌ Errore: {str(e)}")
        return False


def test_upsert():
    """Test upsert dati"""
    print("\n🔄 Test Upsert...")
    data = {
        "table_name": "employees",
        "primary_key": "id",
        "data": [
            {
                "id": 100,
                "name": "Test User Updated",
                "email": "test@example.com",
                "department": "Upsert Testing",
                "salary": 50000,
                "hire_date": "2024-01-01"
            },
            {
                "id": 101,
                "name": "New Test User",
                "email": "newtest@example.com",
                "department": "New Department",
                "salary": 42000,
                "hire_date": "2024-01-15"
            }
        ]
    }

    try:
        response = requests.post(f"{API_URL}/api/v1/upsert", json=data)
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ❌ Errore: {str(e)}")
        return False


def test_delete():
    """Test eliminazione dati"""
    print("\n🗑️  Test Delete...")
    params = {
        "table_name": "employees",
        "where": {"id": 100}
    }

    try:
        response = requests.delete(
            f"{API_URL}/api/v1/delete",
            params={"table_name": "employees"},
            json={"id": 100}
        )
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"   ❌ Errore: {str(e)}")
        return False


def cleanup():
    """Pulizia dati di test"""
    print("\n🧹 Cleanup...")
    for test_id in [100, 101]:
        try:
            requests.delete(
                f"{API_URL}/api/v1/delete",
                params={"table_name": "employees"},
                json={"id": test_id}
            )
        except:
            pass


def main():
    """Esegue tutti i test"""
    print("=" * 60)
    print("🧪 Test Suite API MSSQL Uploader")
    print("=" * 60)

    # Aspetta che l'API sia pronta
    print("\n⏳ Attendo che l'API sia pronta...")
    max_retries = 5
    for i in range(max_retries):
        try:
            response = requests.get(f"{API_URL}/")
            if response.status_code == 200:
                print("✅ API pronta!")
                break
        except:
            if i < max_retries - 1:
                print(f"   Tentativo {i+1}/{max_retries}... attendo 2 secondi")
                time.sleep(2)
            else:
                print("❌ API non disponibile")
                return

    # Esegui test
    results = {
        "Health Check": test_health_check(),
        "Insert": test_insert(),
        "Update": test_update(),
        "Upsert": test_upsert(),
        "Delete": test_delete()
    }

    # Cleanup
    cleanup()

    # Riepilogo
    print("\n" + "=" * 60)
    print("📊 RISULTATI TEST")
    print("=" * 60)

    total = len(results)
    passed = sum(1 for v in results.values() if v)

    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")

    print("\n" + "-" * 60)
    print(f"Test completati: {passed}/{total} ({passed*100//total}%)")
    print("=" * 60)

    return passed == total


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
