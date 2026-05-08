#!/usr/bin/env python3
"""
Comprehensive Backend Integration Testing for ManuAI
"""
import requests
import json
import time
from typing import Dict, Any, List, Tuple

API_BASE = 'http://localhost:8000'
TIMEOUT = 10

def print_section(title: str):
    print('\n' + '='*70)
    print(f'{title}')
    print('='*70)

def print_test_result(name: str, passed: bool, message: str = ''):
    status = 'PASS' if passed else 'FAIL'
    print(f'{status} | {name}')
    if message:
        print(f'       {message}')

# =============================================================================
# 1. HEALTH CHECK
# =============================================================================
def test_health_check() -> Tuple[bool, Dict]:
    print_section('1. HEALTH CHECK TEST')
    
    url = f'{API_BASE}/health'
    print(f'Testing: {url}')
    
    try:
        start = time.time()
        response = requests.get(url, timeout=TIMEOUT)
        elapsed = time.time() - start
        
        print(f'Status Code: {response.status_code}')
        print(f'Response Time: {elapsed:.3f}s')
        
        data = response.json()
        print(f'\nJSON Response:')
        print(json.dumps(data, indent=2))
        
        # Verify structure
        print('\nStructure Validation:')
        required_keys = ['status', 'version', 'database', 'timestamp', 'model_loaded']
        all_present = True
        for key in required_keys:
            if key in data:
                print(f'  PASS {key}: {data[key]}')
            else:
                print(f'  FAIL MISSING: {key}')
                all_present = False
        
        passed = response.status_code == 200 and data.get('status') == 'healthy' and all_present
        print_test_result('Health endpoint', passed)
        
        return passed, data
        
    except Exception as e:
        print(f'FAIL ERROR: {e}')
        print_test_result('Health endpoint', False, str(e))
        return False, {}

# =============================================================================
# 2. DASHBOARD DATA TEST
# =============================================================================
def test_dashboard() -> Tuple[bool, Dict]:
    print_section('2. DASHBOARD DATA TEST')
    
    all_passed = True
    dashboard_data = {}
    
    # Test ingest stats
    print('\n--- Ingest Stats ---')
    try:
        response = requests.get(f'{API_BASE}/ingest/stats', timeout=TIMEOUT)
        print(f'Status: {response.status_code}')
        data = response.json()
        print(json.dumps(data, indent=2))
        dashboard_data['stats'] = data
        print_test_result('Stats endpoint', response.status_code == 200)
        if response.status_code != 200:
            all_passed = False
    except Exception as e:
        print(f'FAIL ERROR: {e}')
        print_test_result('Stats endpoint', False, str(e))
        all_passed = False
    
    # Test alerts
    print('\n--- Alerts Endpoint ---')
    try:
        response = requests.get(f'{API_BASE}/predict/alerts?limit=5', timeout=TIMEOUT)
        print(f'Status: {response.status_code}')
        data = response.json()
        print(f'Returned {len(data)} alerts')
        if len(data) > 0:
            print(f'Sample alert: {json.dumps(data[0], indent=2)}')
        dashboard_data['alerts'] = data
        print_test_result('Alerts endpoint', response.status_code == 200)
        if response.status_code != 200:
            all_passed = False
    except Exception as e:
        print(f'FAIL ERROR: {e}')
        print_test_result('Alerts endpoint', False, str(e))
        all_passed = False
    
    # Test prediction history
    print('\n--- Prediction History ---')
    try:
        response = requests.get(f'{API_BASE}/predict/history?limit=5', timeout=TIMEOUT)
        print(f'Status: {response.status_code}')
        data = response.json()
        print(f'Returned {len(data)} predictions')
        if len(data) > 0:
            print(f'Sample prediction: {json.dumps(data[0], indent=2)}')
        dashboard_data['history'] = data
        print_test_result('History endpoint', response.status_code == 200)
        if response.status_code != 200:
            all_passed = False
    except Exception as e:
        print(f'FAIL ERROR: {e}')
        print_test_result('History endpoint', False, str(e))
        all_passed = False
    
    # Test sensor data
    print('\n--- Sensor Data ---')
    try:
        response = requests.get(f'{API_BASE}/ingest/sensor-data?limit=5', timeout=TIMEOUT)
        print(f'Status: {response.status_code}')
        data = response.json()
        print(f'Returned {len(data)} sensor readings')
        if len(data) > 0:
            print(f'Sample reading: {json.dumps(data[0], indent=2)}')
        dashboard_data['sensors'] = data
        print_test_result('Sensor data endpoint', response.status_code == 200)
        if response.status_code != 200:
            all_passed = False
    except Exception as e:
        print(f'FAIL ERROR: {e}')
        print_test_result('Sensor data endpoint', False, str(e))
        all_passed = False
    
    return all_passed, dashboard_data

# =============================================================================
# 3. PREDICTION SYSTEM TEST
# =============================================================================
def test_predictions() -> Tuple[bool, Dict]:
    print_section('3. PREDICTION SYSTEM TEST')
    
    all_passed = True
    prediction_results = {}
    
    # Test LOW RISK prediction
    print('\n--- LOW RISK Prediction ---')
    low_risk_input = {
        'sensor_data': {
            'type': 'M',
            'air_temp_k': 300,
            'process_temp_k': 310,
            'rotational_speed_rpm': 1500,
            'torque_nm': 40,
            'tool_wear_min': 50
        },
        'save_to_db': True
    }
    
    try:
        print(f'Request payload: {json.dumps(low_risk_input, indent=2)}')
        response = requests.post(f'{API_BASE}/predict/failure', json=low_risk_input, timeout=TIMEOUT)
        print(f'Status: {response.status_code}')
        data = response.json()
        print(f'Response: {json.dumps(data, indent=2)}')
        prediction_results['low_risk'] = data
        
        passed = response.status_code == 200 and 'failure_probability' in data
        print_test_result('LOW RISK prediction', passed)
        if not passed:
            all_passed = False
    except Exception as e:
        print(f'FAIL ERROR: {e}')
        print_test_result('LOW RISK prediction', False, str(e))
        all_passed = False
    
    # Test HIGH RISK prediction
    print('\n--- HIGH RISK Prediction ---')
    high_risk_input = {
        'sensor_data': {
            'type': 'M',
            'air_temp_k': 340,
            'process_temp_k': 360,
            'rotational_speed_rpm': 2900,
            'torque_nm': 90,
            'tool_wear_min': 240
        },
        'save_to_db': True
    }
    
    try:
        print(f'Request payload: {json.dumps(high_risk_input, indent=2)}')
        response = requests.post(f'{API_BASE}/predict/failure', json=high_risk_input, timeout=TIMEOUT)
        print(f'Status: {response.status_code}')
        data = response.json()
        print(f'Response: {json.dumps(data, indent=2)}')
        prediction_results['high_risk'] = data
        
        passed = response.status_code == 200 and 'failure_probability' in data
        print_test_result('HIGH RISK prediction', passed)
        if not passed:
            all_passed = False
    except Exception as e:
        print(f'FAIL ERROR: {e}')
        print_test_result('HIGH RISK prediction', False, str(e))
        all_passed = False
    
    # Verify predictions are different
    if 'low_risk' in prediction_results and 'high_risk' in prediction_results:
        low_prob = prediction_results['low_risk'].get('failure_probability', 0)
        high_prob = prediction_results['high_risk'].get('failure_probability', 0)
        print(f'\nRisk comparison:')
        print(f'  LOW:  {low_prob:.4f}')
        print(f'  HIGH: {high_prob:.4f}')
        prediction_different = high_prob > low_prob
        print_test_result('HIGH risk > LOW risk', prediction_different)
        if not prediction_different:
            all_passed = False
    
    return all_passed, prediction_results

# =============================================================================
# 4. AGENT SYSTEM TEST
# =============================================================================
def test_agents() -> Tuple[bool, Dict]:
    print_section('4. AGENT SYSTEM TEST')
    
    all_passed = True
    agent_results = {}
    
    # Test agent status first
    print('\n--- Agent Status ---')
    try:
        response = requests.get(f'{API_BASE}/agent/status', timeout=TIMEOUT)
        print(f'Status: {response.status_code}')
        data = response.json()
        print(json.dumps(data, indent=2))
        agent_results['status'] = data
        print_test_result('Agent status endpoint', response.status_code == 200)
        if response.status_code != 200:
            all_passed = False
    except Exception as e:
        print(f'FAIL ERROR: {e}')
        print_test_result('Agent status endpoint', False, str(e))
        all_passed = False
    
    # Test agent queries
    queries = [
        'How do I replace a bearing?',
        'What causes spindle overheating?'
    ]
    
    for query in queries:
        print(f'\n--- Query: "{query}" ---')
        payload = {'question': query, 'context': {}}
        
        try:
            print(f'Request: {json.dumps(payload, indent=2)}')
            response = requests.post(f'{API_BASE}/agent/query', json=payload, timeout=30)
            print(f'Status: {response.status_code}')
            data = response.json()
            print(f'Response keys: {list(data.keys())}')
            if 'answer' in data:
                print(f'Answer preview: {data["answer"][:200]}...')
            if 'agent_used' in data:
                print(f'Agent used: {data["agent_used"]}')
            
            agent_results[query] = data
            
            passed = response.status_code == 200 and 'answer' in data
            print_test_result(f'Agent query "{query[:30]}..."', passed)
            if not passed:
                all_passed = False
        except Exception as e:
            print(f'ERROR: {e}')
            print_test_result(f'Agent query "{query[:30]}..."', False, str(e))
            all_passed = False
    
    return all_passed, agent_results

# =============================================================================
# 5. DOCUMENT SEARCH TEST
# =============================================================================
def test_search() -> Tuple[bool, Dict]:
    print_section('5. DOCUMENT SEARCH / RAG TEST')
    
    all_passed = True
    search_results = {}
    
    search_queries = ['bearing', 'maintenance', 'vibration']
    
    for query in search_queries:
        print(f'\n--- Search: "{query}" ---')
        
        try:
            url = f'{API_BASE}/search/documents?q={query}&limit=3'
            print(f'URL: {url}')
            response = requests.get(url, timeout=TIMEOUT)
            print(f'Status: {response.status_code}')
            data = response.json()
            
            if 'results' in data:
                print(f'Found {len(data["results"])} results')
                for i, result in enumerate(data['results'][:2], 1):
                    print(f'\n  Result {i}:')
                    print(f'    Source: {result.get("source", "N/A")}')
                    print(f'    Score: {result.get("relevance_score", 0):.2f}')
                    print(f'    Content preview: {result.get("content", "")[:100]}...')
            else:
                print(json.dumps(data, indent=2))
            
            search_results[query] = data
            print_test_result(f'Search "{query}"', response.status_code == 200)
            if response.status_code != 200:
                all_passed = False
        except Exception as e:
            print(f'ERROR: {e}')
            print_test_result(f'Search "{query}"', False, str(e))
            all_passed = False
    
    # Test RAG health
    print(f'\n--- RAG Health ---')
    try:
        response = requests.get(f'{API_BASE}/search/documents/health', timeout=TIMEOUT)
        print(f'Status: {response.status_code}')
        data = response.json()
        print(json.dumps(data, indent=2))
        search_results['rag_health'] = data
        print_test_result('RAG health endpoint', response.status_code == 200)
        if response.status_code != 200:
            all_passed = False
    except Exception as e:
        print(f'FAIL ERROR: {e}')
        print_test_result('RAG health endpoint', False, str(e))
        all_passed = False
    
    return all_passed, search_results

# =============================================================================
# 6. SYSTEM STATUS TEST
# =============================================================================
def test_system_status() -> Tuple[bool, Dict]:
    print_section('6. SYSTEM STATUS TEST')
    
    all_passed = True
    status_results = {}
    
    endpoints = [
        ('/health', 'Backend health'),
        ('/system/config', 'System config'),
        ('/search/documents/health', 'RAG health'),
        ('/agent/status', 'Agent status')
    ]
    
    for endpoint, name in endpoints:
        print(f'\n--- {name} ---')
        try:
            response = requests.get(f'{API_BASE}{endpoint}', timeout=TIMEOUT)
            print(f'Status: {response.status_code}')
            data = response.json()
            print(json.dumps(data, indent=2))
            status_results[endpoint] = data
            print_test_result(name, response.status_code == 200)
            if response.status_code != 200:
                all_passed = False
        except Exception as e:
            print(f'FAIL ERROR: {e}')
            print_test_result(name, False, str(e))
            all_passed = False
    
    return all_passed, status_results

# =============================================================================
# MAIN
# =============================================================================
if __name__ == '__main__':
    print('\n\n')
    print('#'*70)
    print('# ManuAI BACKEND INTEGRATION TEST SUITE')
    print('#'*70)
    
    results = {}
    
    # Run all tests
    results['health'] = test_health_check()
    results['dashboard'] = test_dashboard()
    results['predictions'] = test_predictions()
    results['agents'] = test_agents()
    results['search'] = test_search()
    results['status'] = test_system_status()
    
    # Print summary
    print_section('FINAL SUMMARY')
    
    for test_name, (passed, data) in results.items():
        status = 'PASS' if passed else 'FAIL'
        print(f'{status} | {test_name.upper()}')
    
    all_passed = all(passed for passed, _ in results.values())
    print(f'\n{"="*70}')
    if all_passed:
           print('ALL TESTS PASSED - BACKEND FULLY INTEGRATED')
    else:
           print('WARNING: SOME TESTS FAILED - SEE DETAILS ABOVE')
    print(f'{"="*70}')
