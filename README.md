# Local Development Setup for Kotha Kow

## Running the Server with WebSocket Support

This project uses Django Channels for real-time chat. To enable WebSocket support locally, you must run an ASGI server. There are two options:

### Option 1: Django 5+ (Recommended)
If you are using Django 5 or newer, simply run:

```
python manage.py runserver
```

Django 5+ supports ASGI and Channels natively.

### Option 2: Daphne (Any Django Version)
If you want to use Daphne explicitly, run:

```
daphne -b 127.0.0.1 -p 8000 kothakow.asgi:application
```

or

```
python -m daphne -b 127.0.0.1 -p 8000 kothakow.asgi:application
```

**Do NOT run both `runserver` and `daphne` at the same time on the same port.**

## Troubleshooting WebSocket Issues

- If you see `WebSocket connection failed` or `Chat socket closed unexpectedly`:
  - Make sure you are running the correct server (see above).
  - Only one server should be running on port 8000.
  - Make sure `DEBUG=True` in your environment for local development.
  - Hard refresh your browser (Ctrl+F5) to clear cache.
  - Check for firewall/antivirus blocking localhost connections.
  - If you see 404s for media/static files, make sure the files exist or update your code to not reference missing files.

## Static and Media Files
- Static and media files are served automatically in development (`DEBUG=True`).
- If you see 404 errors for media or static files, ensure the files exist in the correct directories:
  - `media/profile_pics/`
  - `media/chat_media/images/`
  - `media/chat_media/videos/`
  - `static/audios/` (for notification sounds)

## Environment Variables
- For local development, set `DEBUG=True` and do not set `REDIS_URL` (uses in-memory channel layer).
- For production, set `DEBUG=False` and provide a `REDIS_URL`. 