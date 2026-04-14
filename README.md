# devsec-demo
## Django based class demo about Security essentials required by dev

## User Authentication Service (webwi)

This repository now includes a dedicated Django authentication app named `webwi`.

### Features

- User registration
- Login and logout
- Protected authenticated dashboard
- Password change flow
- Basic profile management

### Setup

1. Install dependencies:

	```bash
	pip install -r requirements.txt
	```

2. Ensure environment variables are set (for example in a `.env` file):

	- `DJANGO_SECRET_KEY`
	- `DJANGO_DEBUG`

3. Run migrations:

	```bash
	python manage.py migrate
	```

4. Start server:

	```bash
	python manage.py runserver
	```

### Auth URLs

- `/register/`
- `/login/`
- `/logout/`
- `/dashboard/`
- `/password/change/`
- `/profile/`

### Tests

Run all tests:

```bash
python manage.py test
```
