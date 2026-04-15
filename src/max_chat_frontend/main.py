from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from max_chat_frontend.core.config import get_settings
from max_chat_frontend.services.backend_api import BackendApiClient, BackendUnavailableError

settings = get_settings()
app = FastAPI(title=settings.app_name)
app.add_middleware(SessionMiddleware, secret_key=settings.frontend_secret_key)

client = BackendApiClient(settings)


def resolve_templates_dir() -> str:
    candidates = [
        Path(__file__).resolve().parents[2] / "templates",
        Path.cwd() / "templates",
        Path("/app/templates"),
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    raise RuntimeError("Templates directory was not found.")


templates = Jinja2Templates(directory=resolve_templates_dir())


def is_authenticated(request: Request) -> bool:
    return bool(request.session.get("authenticated"))


def require_auth(request: Request) -> RedirectResponse | None:
    if is_authenticated(request):
        return None
    return RedirectResponse(url="/login", status_code=302)


def fetch_with_fallback(path: str, *, default: dict, params: dict | None = None) -> tuple[dict, str | None]:
    try:
        return client.fetch(path, params=params), None
    except BackendUnavailableError:
        return default, "Backend is temporarily unavailable."


def template_response(request: Request, template_name: str, context: dict, *, status_code: int = 200) -> HTMLResponse:
    payload = {"request": request, **context}
    return templates.TemplateResponse(request=request, name=template_name, context=payload, status_code=status_code)


@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    if not is_authenticated(request):
        return RedirectResponse(url="/login", status_code=302)
    return RedirectResponse(url="/dashboard", status_code=302)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    if is_authenticated(request):
        return RedirectResponse(url="/dashboard", status_code=302)
    return template_response(request, "login.html", {"title": "Login"})


@app.post("/login", response_class=HTMLResponse)
def login_submit(request: Request, username: str = Form(...), password: str = Form(...)):
    if username == settings.admin_username and password == settings.admin_password:
        request.session["authenticated"] = True
        return RedirectResponse(url="/dashboard", status_code=302)

    return template_response(
        request,
        "login.html",
        {"title": "Login", "error": "Неверный логин или пароль."},
        status_code=401,
    )


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login", status_code=302)


@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request):
    redirect = require_auth(request)
    if redirect:
        return redirect

    summary, backend_error = fetch_with_fallback(
        "/internal/summary",
        default={
            "totals": {
                "users": 0,
                "conversations": 0,
                "messages": 0,
                "user_messages": 0,
                "assistant_messages": 0,
                "llm_requests": 0,
                "failed_llm_requests": 0,
                "active_llm_requests": 0,
            },
            "recent_requests": [],
        },
    )
    return template_response(
        request,
        "dashboard.html",
        {"title": "Dashboard", "summary": summary, "backend_error": backend_error},
    )


@app.get("/users", response_class=HTMLResponse)
def users(request: Request, search: str | None = None):
    redirect = require_auth(request)
    if redirect:
        return redirect
    data, backend_error = fetch_with_fallback(
        "/internal/users",
        default={"items": []},
        params={"search": search} if search else None,
    )
    return template_response(
        request,
        "users.html",
        {
            "title": "Users",
            "items": data["items"],
            "search": search or "",
            "backend_error": backend_error,
        },
    )


@app.get("/users/{user_id}", response_class=HTMLResponse)
def user_detail(request: Request, user_id: int):
    redirect = require_auth(request)
    if redirect:
        return redirect
    data, backend_error = fetch_with_fallback(
        f"/internal/users/{user_id}",
        default={
            "user": None,
            "recent_conversations": [],
            "recent_messages": [],
            "recent_llm_requests": [],
        },
    )
    if backend_error:
        return template_response(
            request,
            "user_detail.html",
            {"title": "User", "backend_error": backend_error, "unavailable": True},
            status_code=503,
        )
    if not data["user"]:
        return template_response(
            request,
            "user_detail.html",
            {"title": "User", "backend_error": backend_error, "not_found": True},
            status_code=404,
        )
    return template_response(
        request,
        "user_detail.html",
        {
            "title": "User",
            "backend_error": backend_error,
            "user": data["user"],
            "recent_conversations": data["recent_conversations"],
            "recent_messages": data["recent_messages"],
            "recent_llm_requests": data["recent_llm_requests"],
        },
    )


@app.get("/conversations", response_class=HTMLResponse)
def conversations(request: Request, active: str | None = None):
    redirect = require_auth(request)
    if redirect:
        return redirect
    params = {"active": active} if active else None
    data, backend_error = fetch_with_fallback("/internal/conversations", default={"items": []}, params=params)
    return template_response(
        request,
        "conversations.html",
        {
            "title": "Conversations",
            "items": data["items"],
            "active": active or "",
            "backend_error": backend_error,
        },
    )


@app.get("/conversations/{conversation_id}", response_class=HTMLResponse)
def conversation_detail(request: Request, conversation_id: int):
    redirect = require_auth(request)
    if redirect:
        return redirect
    data, backend_error = fetch_with_fallback(
        f"/internal/conversations/{conversation_id}",
        default={"conversation": None, "user": None, "messages": [], "llm_requests": []},
    )
    if backend_error:
        return template_response(
            request,
            "conversation_detail.html",
            {"title": "Conversation", "backend_error": backend_error, "unavailable": True},
            status_code=503,
        )
    if not data["conversation"]:
        return template_response(
            request,
            "conversation_detail.html",
            {"title": "Conversation", "backend_error": backend_error, "not_found": True},
            status_code=404,
        )
    return template_response(
        request,
        "conversation_detail.html",
        {
            "title": "Conversation",
            "backend_error": backend_error,
            "conversation": data["conversation"],
            "user": data["user"],
            "messages": data["messages"],
            "llm_requests": data["llm_requests"],
        },
    )


@app.get("/messages", response_class=HTMLResponse)
def messages(request: Request, role: str | None = None):
    redirect = require_auth(request)
    if redirect:
        return redirect
    params = {"role": role} if role else None
    data, backend_error = fetch_with_fallback("/internal/messages", default={"items": []}, params=params)
    return template_response(
        request,
        "messages.html",
        {
            "title": "Messages",
            "items": data["items"],
            "role": role or "",
            "backend_error": backend_error,
        },
    )


@app.get("/messages/{message_id}", response_class=HTMLResponse)
def message_detail(request: Request, message_id: int):
    redirect = require_auth(request)
    if redirect:
        return redirect
    data, backend_error = fetch_with_fallback(
        f"/internal/messages/{message_id}",
        default={"message": None, "user": None, "conversation": None},
    )
    if backend_error:
        return template_response(
            request,
            "message_detail.html",
            {"title": "Message", "backend_error": backend_error, "unavailable": True},
            status_code=503,
        )
    if not data["message"]:
        return template_response(
            request,
            "message_detail.html",
            {"title": "Message", "backend_error": backend_error, "not_found": True},
            status_code=404,
        )
    return template_response(
        request,
        "message_detail.html",
        {
            "title": "Message",
            "backend_error": backend_error,
            "message": data["message"],
            "user": data["user"],
            "conversation": data["conversation"],
        },
    )


@app.get("/llm-requests", response_class=HTMLResponse)
def llm_requests(request: Request, status: str | None = None):
    redirect = require_auth(request)
    if redirect:
        return redirect
    params = {"status": status} if status else None
    data, backend_error = fetch_with_fallback("/internal/llm-requests", default={"items": []}, params=params)
    return template_response(
        request,
        "llm_requests.html",
        {
            "title": "LLM Requests",
            "items": data["items"],
            "status": status or "",
            "backend_error": backend_error,
        },
    )


@app.get("/llm-requests/{request_id}", response_class=HTMLResponse)
def llm_request_detail(request: Request, request_id: int):
    redirect = require_auth(request)
    if redirect:
        return redirect
    data, backend_error = fetch_with_fallback(
        f"/internal/llm-requests/{request_id}",
        default={
            "llm_request": None,
            "conversation": None,
            "user": None,
            "user_message": None,
            "assistant_message": None,
        },
    )
    if backend_error:
        return template_response(
            request,
            "llm_request_detail.html",
            {"title": "LLM Request", "backend_error": backend_error, "unavailable": True},
            status_code=503,
        )
    if not data["llm_request"]:
        return template_response(
            request,
            "llm_request_detail.html",
            {"title": "LLM Request", "backend_error": backend_error, "not_found": True},
            status_code=404,
        )
    return template_response(
        request,
        "llm_request_detail.html",
        {
            "title": "LLM Request",
            "backend_error": backend_error,
            "llm_request": data["llm_request"],
            "conversation": data["conversation"],
            "user": data["user"],
            "user_message": data["user_message"],
            "assistant_message": data["assistant_message"],
        },
    )


@app.get("/errors", response_class=HTMLResponse)
def errors(request: Request):
    redirect = require_auth(request)
    if redirect:
        return redirect
    data, backend_error = fetch_with_fallback("/internal/errors", default={"items": []})
    return template_response(
        request,
        "errors.html",
        {"title": "Errors", "items": data["items"], "backend_error": backend_error},
    )


@app.get("/exports/{export_name}")
def export_proxy(request: Request, export_name: str):
    redirect = require_auth(request)
    if redirect:
        return redirect

    allowed = {
        "users.csv": "/internal/exports/users.csv",
        "conversations.csv": "/internal/exports/conversations.csv",
        "messages.csv": "/internal/exports/messages.csv",
        "llm_requests.csv": "/internal/exports/llm_requests.csv",
    }
    backend_path = allowed.get(export_name)
    if not backend_path:
        return Response(status_code=404)

    try:
        content, content_type = client.fetch_bytes(backend_path)
        return Response(
            content=content,
            media_type=content_type,
            headers={"Content-Disposition": f'attachment; filename=\"{export_name}\"'},
        )
    except BackendUnavailableError:
        return Response(content="Backend is temporarily unavailable.", status_code=503, media_type="text/plain")
