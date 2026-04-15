import requests

url = 'http://127.0.0.1:8000/profile/'
# This should fail with 403 Forbidden if CSRF is active
try:
    response = requests.post(url, data={'first_name': 'Attacker'})
    print(f'Status Code: {response.status_code}')
    if response.status_code == 403:
        print('CSRF is ACTIVE')
    else:
        print('CSRF is potentialy BYPASSED/DISABLED')
except Exception as e:
    print(f'Error: {e}')
