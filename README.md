# devsec-demo
## Django based class demo about Security essentials required by dev

## User Authentication Service

This repository now includes a Django authentication app named `igihozo` that covers:

- user registration
- login and logout
- protected account area
- password change
- basic profile/account management
- admin integration for profile records
- tests for the main authentication flows

## Setup

1. Activate the virtual environment.
2. Install dependencies if needed:

```powershell
venv\Scripts\pip.exe install -r requirements.txt
```

3. Apply migrations:

```powershell
venv\Scripts\python.exe manage.py migrate
```

4. Start the development server:

```powershell
venv\Scripts\python.exe manage.py runserver
```

## Main Routes

- `/` home page
- `/register/` registration
- `/login/` login
- `/logout/` logout
- `/account/` protected account page
- `/password-change/` password update
- `/admin/` Django admin

## Testing

Run the test suite with:

```powershell
venv\Scripts\python.exe manage.py test
```

Verified locally:

- `venv\Scripts\python.exe manage.py check`
- `venv\Scripts\python.exe manage.py migrate`
- `venv\Scripts\python.exe manage.py test`
