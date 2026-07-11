"""
Shared Flask extension instances.

These are created here (uninitialized) and imported by both app.py and the
route modules, instead of route modules importing them from app.py directly.

Why this matters: when you run `python app.py`, Python loads that file as
the module `__main__`, not as a module named `app`. If routes/auth.py then
does `from app import limiter`, Python has no `app` module in sys.modules
yet, so it imports app.py a *second* time under the name `app` - re-running
the whole file, including `app = create_app()`, from scratch. That second
run re-imports routes.auth, which is still mid-import from the first run,
causing the "partially initialized module" circular-import error.

Keeping extension objects in their own module with no dependency on app.py
avoids that: both app.py and routes/auth.py can import extensions.py safely,
regardless of whether app.py is run as a script or imported as a module.
"""
from flask_wtf import CSRFProtect
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_mail import Mail

csrf = CSRFProtect()
limiter = Limiter(key_func=get_remote_address, default_limits=["200 per hour"])
mail = Mail()
