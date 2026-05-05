# About & Contact Pages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an About page (static project info) and Contact page (public form + admin inbox) to HomeGallery.

**Architecture:** About page is a pure frontend component. Contact page has a backend model + API for storing messages, a public form endpoint, and an admin Messages tab in Settings. Both pages get sidebar navigation links.

**Tech Stack:** React 18, FastAPI, SQLAlchemy, Zustand, Playwright E2E, pytest

---

## File Structure

| File | Action | Responsibility |
|------|--------|---------------|
| `frontend/src/pages/AboutPage.jsx` | Create | Static About page component |
| `frontend/src/pages/ContactPage.jsx` | Create | Contact form component |
| `frontend/src/services/contactService.js` | Create | API helper for contact endpoints |
| `backend/app/models/contact.py` | Create | ContactMessage SQLAlchemy model |
| `backend/app/api/contact.py` | Create | Contact API endpoints |
| `frontend/src/App.jsx` | Modify | Add /about and /contact routes |
| `frontend/src/components/Layout/Sidebar.jsx` | Modify | Add About and Contact nav items |
| `frontend/src/pages/SettingsPage.jsx` | Modify | Add "Messages" tab |
| `backend/app/models/__init__.py` | Modify | Export ContactMessage |
| `backend/app/api/__init__.py` | Modify | Register contact router |
| `frontend/src/styles/global.css` | Modify | Add contact/about styles |
| `tests/unit/test_contact_model.py` | Create | Model unit tests |
| `tests/unit/test_contact_api.py` | Create | API unit tests |
| `tests/e2e/about-contact.spec.js` | Create | E2E tests |

---

### Task 1: ContactMessage Model

**Files:**
- Create: `backend/app/models/contact.py`
- Modify: `backend/app/models/__init__.py`

```python
# backend/app/models/contact.py
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime
from sqlalchemy.sql import func
from app.database import Base

class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=func.now())
```

```python
# backend/app/models/__init__.py — add to existing imports
from app.models.contact import ContactMessage

# Add to __all__
__all__ = ["User", "Photo", "Album", "AlbumPhoto", "Person", "FaceDetection", "Task", "PhotoMetadata", "ApiKey", "ContactMessage"]
```

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_contact_model.py
import pytest
from datetime import datetime
from app.models.contact import ContactMessage

class TestContactMessageModel:
    def test_create_contact_message(self, db_session):
        msg = ContactMessage(
            name="John Doe",
            email="john@example.com",
            subject="Test",
            message="Hello World",
        )
        db_session.add(msg)
        db_session.commit()

        retrieved = db_session.query(ContactMessage).first()
        assert retrieved.name == "John Doe"
        assert retrieved.email == "john@example.com"
        assert retrieved.subject == "Test"
        assert retrieved.message == "Hello World"
        assert retrieved.is_read == False
        assert isinstance(retrieved.created_at, datetime)

    def test_default_is_read_is_false(self, db_session):
        msg = ContactMessage(
            name="Jane",
            email="jane@example.com",
            subject="Hi",
            message="Hi there",
        )
        db_session.add(msg)
        db_session.commit()

        retrieved = db_session.query(ContactMessage).first()
        assert retrieved.is_read == False

    def test_mark_as_read(self, db_session):
        msg = ContactMessage(
            name="Bob",
            email="bob@example.com",
            subject="Read me",
            message="Please read",
            is_read=False,
        )
        db_session.add(msg)
        db_session.commit()

        msg.is_read = True
        db_session.commit()

        retrieved = db_session.query(ContactMessage).first()
        assert retrieved.is_read == True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_contact_model.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.models.contact'"

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/models/contact.py` with the model code above.
Add export to `backend/app/models/__init__.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_contact_model.py -v`
Expected: 3/3 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/models/contact.py backend/app/models/__init__.py tests/unit/test_contact_model.py
git commit -m "feat: add ContactMessage model for contact form submissions"
```

---

### Task 2: Contact API Endpoints

**Files:**
- Create: `backend/app/api/contact.py`
- Modify: `backend/app/api/__init__.py`

```python
# backend/app/api/contact.py
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel

from app.database import get_db
from app.models.contact import ContactMessage
from app.utils.security import get_current_admin_user
from app.models.user import User

router = APIRouter(prefix="/contact", tags=["contact"])

# Rate limit tracking (in-memory, resets on server restart)
_contact_submissions = {}

def check_rate_limit(request: Request):
    """Limit to 3 submissions per 15 minutes per IP."""
    ip = request.client.host
    now = datetime.now()
    window = 15 * 60  # 15 minutes in seconds

    if ip in _contact_submissions:
        # Clean old entries
        _contact_submissions[ip] = [
            t for t in _contact_submissions[ip]
            if (now - t).total_seconds() < window
        ]
        if len(_contact_submissions[ip]) >= 3:
            raise HTTPException(
                status_code=429,
                detail="Too many submissions. Please try again later.",
            )

    _contact_submissions.setdefault(ip, []).append(now)

class ContactRequest(BaseModel):
    name: str
    email: str
    subject: str
    message: str

class ContactResponse(BaseModel):
    id: int
    name: str
    email: str
    subject: str
    message: str
    is_read: bool
    created_at: datetime

    class Config:
        from_attributes = True

@router.post("", status_code=status.HTTP_201_CREATED)
def submit_contact(
    data: ContactRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    check_rate_limit(request)

    msg = ContactMessage(
        name=data.name.strip(),
        email=data.email.strip(),
        subject=data.subject.strip(),
        message=data.message.strip(),
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)
    return {"message": "Message sent successfully"}

@router.get("/messages", response_model=List[ContactResponse])
def list_messages(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    messages = db.query(ContactMessage).order_by(
        ContactMessage.created_at.desc()
    ).all()
    return messages

@router.get("/messages/{message_id}", response_model=ContactResponse)
def get_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    msg = db.query(ContactMessage).filter(
        ContactMessage.id == message_id
    ).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    return msg

@router.patch("/messages/{message_id}/read")
def mark_read(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    msg = db.query(ContactMessage).filter(
        ContactMessage.id == message_id
    ).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    msg.is_read = True
    db.commit()
    return {"message": "Message marked as read"}

@router.delete("/messages/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_message(
    message_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user),
):
    msg = db.query(ContactMessage).filter(
        ContactMessage.id == message_id
    ).first()
    if not msg:
        raise HTTPException(status_code=404, detail="Message not found")
    db.delete(msg)
    db.commit()
```

```python
# backend/app/api/__init__.py — add these lines:
from app.api.contact import router as contact_router

# Add at the end, before __all__:
api_router.include_router(contact_router)
```

- [ ] **Step 1: Write the failing test**

```python
# tests/unit/test_contact_api.py
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch
from fastapi import status
from app.main import app

class TestContactApi:
    def test_submit_contact_success(self, db_session):
        """POST /api/contact creates a message."""
        with patch("app.api.contact.get_db", return_value=db_session):
            client = TestClient(app)
            response = client.post("/api/contact", json={
                "name": "Test User",
                "email": "test@example.com",
                "subject": "Hello",
                "message": "This is a test message",
            })
            assert response.status_code == 201
            assert response.json()["message"] == "Message sent successfully"

    def test_submit_contact_validation_error(self):
        """POST /api/contact returns 422 for missing fields."""
        with patch("app.api.contact.get_db", return_value=MagicMock()):
            client = TestClient(app)
            response = client.post("/api/contact", json={
                "name": "",
                "email": "invalid",
                "subject": "Hi",
            })
            assert response.status_code == 422

    def test_list_messages_requires_admin(self):
        """GET /api/contact/messages requires authentication."""
        client = TestClient(app)
        response = client.get("/api/contact/messages")
        assert response.status_code == 401

    def test_delete_message_not_found(self, db_session):
        """DELETE returns 404 for non-existent message."""
        from app.utils.security import get_current_admin_user
        mock_admin = MagicMock()
        mock_admin.is_admin = True

        with patch("app.api.contact.get_db", return_value=db_session):
            with patch("app.api.contact.get_current_admin_user", return_value=mock_admin):
                client = TestClient(app)
                response = client.delete("/api/contact/messages/99999")
                assert response.status_code == 404

    def test_rate_limit_blocks_excess(self):
        """Rate limit blocks after 3 submissions in 15 min."""
        from app.api.contact import _contact_submissions
        _contact_submissions.clear()

        with patch("app.api.contact.get_db", return_value=MagicMock()):
            client = TestClient(app)

            # 3 successful submissions
            for i in range(3):
                response = client.post(
                    "/api/contact",
                    json={"name": f"User{i}", "email": f"user{i}@example.com", "subject": "Hi", "message": "Hello"},
                )
                assert response.status_code == 201

            # 4th should be blocked
            response = client.post(
                "/api/contact",
                json={"name": "User4", "email": "user4@example.com", "subject": "Hi", "message": "Hello"},
            )
            assert response.status_code == 429
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_contact_api.py -v`
Expected: FAIL with "ModuleNotFoundError: No module named 'app.api.contact'"

- [ ] **Step 3: Write minimal implementation**

Create `backend/app/api/contact.py` with the API code above.
Register the router in `backend/app/api/__init__.py`.

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_contact_api.py -v`
Expected: 5/5 PASS

- [ ] **Step 5: Commit**

```bash
git add backend/app/api/contact.py backend/app/api/__init__.py tests/unit/test_contact_api.py
git commit -m "feat: add contact form API with rate limiting and admin endpoints"
```

---

### Task 3: About Page Component

**Files:**
- Create: `frontend/src/pages/AboutPage.jsx`
- Modify: `frontend/src/App.jsx`
- Modify: `frontend/src/components/Layout/Sidebar.jsx`
- Modify: `frontend/src/styles/global.css`

```jsx
// frontend/src/pages/AboutPage.jsx
import { useEffect, useState } from "react";
import api from "../services/api";

const FEATURES = [
  { name: "Smart Metadata", desc: "Automatic EXIF extraction, object detection, color analysis, and tag generation." },
  { name: "Auto-Organization", desc: "Date-based albums, GPS clustering, pHash duplicate detection, best-shot suggestions." },
  { name: "Enhancement", desc: "Histogram analysis, scene-aware presets (portrait, landscape, night), PIL enhancement." },
  { name: "Content Analysis", desc: "Sharpness scoring, exposure analysis, noise detection, quality metrics, composition." },
  { name: "Visual Search", desc: "128-dim feature embeddings, text-to-image search, similarity-based discovery." },
  { name: "MCP Integration", desc: "7 MCP servers for image analysis, agent control, browser automation, docs access." },
];

const TECH_STACK = [
  { category: "Frontend", tech: "React 18 + Vite + Zustand" },
  { category: "Backend", tech: "FastAPI (Python 3.10+)" },
  { category: "Database", tech: "SQLite (default) / PostgreSQL" },
  { category: "Agents", tech: "5 autonomous agents via APScheduler" },
  { category: "Testing", tech: "Playwright E2E + pytest" },
];

export default function AboutPage() {
  const [version, setVersion] = useState(null);

  useEffect(() => {
    api.photos.list({ limit: 1 }).then(() => {}).catch(() => {});
    fetch("/api/health")
      .then((r) => r.json())
      .then((data) => setVersion(data.version))
      .catch(() => setVersion("?"));
  }, []);

  return (
    <div className="about-page">
      <div className="about-hero">
        <h1>HomeGallery</h1>
        <p className="about-tagline">
          AI-powered photo gallery with smart organization, content analysis, and visual search.
        </p>
        {version && <span className="about-version">v{version}</span>}
      </div>

      <section className="about-section">
        <h2>Features</h2>
        <div className="about-features-grid">
          {FEATURES.map((f) => (
            <div key={f.name} className="about-feature-card">
              <h3>{f.name}</h3>
              <p>{f.desc}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="about-section">
        <h2>Tech Stack</h2>
        <table className="about-tech-table">
          <thead>
            <tr><th>Category</th><th>Technology</th></tr>
          </thead>
          <tbody>
            {TECH_STACK.map((t) => (
              <tr key={t.category}>
                <td>{t.category}</td>
                <td>{t.tech}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="about-section">
        <h2>Links</h2>
        <div className="about-links">
          <a href="https://github.com/anomalyco/homeGallery" target="_blank" rel="noopener noreferrer">GitHub Repository</a>
          <a href="https://github.com/anomalyco/homeGallery/blob/main/README.md" target="_blank" rel="noopener noreferrer">Documentation</a>
          <a href="https://github.com/anomalyco/homeGallery/blob/main/LICENSE" target="_blank" rel="noopener noreferrer">License</a>
        </div>
      </section>
    </div>
  );
}
```

```jsx
// frontend/src/App.jsx — add imports and routes:
import AboutPage from "./pages/AboutPage";
import ContactPage from "./pages/ContactPage";

// Add inside <Routes> after /duplicates route and before /404:
<Route
  path="/about"
  element={
    <ProtectedRoute>
      <AppLayout>
        <AboutPage />
      </AppLayout>
    </ProtectedRoute>
  }
/>
<Route
  path="/contact"
  element={
    <ProtectedRoute>
      <AppLayout>
        <ContactPage />
      </AppLayout>
    </ProtectedRoute>
  }
/>
```

```jsx
// frontend/src/components/Layout/Sidebar.jsx — add nav items:
const navItems = [
  { path: "/", label: "Gallery", icon: "\u{1F5BC}" },
  { path: "/albums", label: "Albums", icon: "\u{1F4C1}" },
  { path: "/duplicates", label: "Duplicates", icon: "\u{1F517}" },
  { path: "/faces", label: "Faces", icon: "\u{1F464}" },
  { path: "/dashboard", label: "Dashboard", icon: "\u{1F4CA}" },
  { path: "/about", label: "About", icon: "\u2139" },
  { path: "/contact", label: "Contact", icon: "\u2709" },
  { path: "/settings", label: "Settings", icon: "\u2699" },
];
```

- [ ] **Step 1: Create the About page component**

Create `frontend/src/pages/AboutPage.jsx` with the code above.

- [ ] **Step 2: Add routes to App.jsx**

Add the two route blocks shown above inside the `<Routes>` element.

- [ ] **Step 3: Add sidebar navigation**

Update `Sidebar.jsx` `navItems` array to include About and Contact.

- [ ] **Step 4: Add CSS styles**

Add to `frontend/src/styles/global.css`:

```css
/* About Page */
.about-page { padding: 24px; }
.about-hero { text-align: center; padding: 40px 0; }
.about-hero h1 { font-size: 2.5rem; margin-bottom: 8px; }
.about-tagline { color: var(--text-secondary); font-size: 1.1rem; margin-bottom: 16px; }
.about-version { display: inline-block; background: var(--accent-light); color: var(--accent); padding: 4px 12px; border-radius: 20px; font-size: 0.85rem; }
.about-section { margin: 32px 0; }
.about-section h2 { font-size: 1.5rem; margin-bottom: 16px; padding-bottom: 8px; border-bottom: 1px solid var(--border-color); }
.about-features-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 16px; }
.about-feature-card { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md); padding: 20px; }
.about-feature-card h3 { color: var(--accent); margin-bottom: 8px; }
.about-feature-card p { color: var(--text-secondary); font-size: 0.9rem; }
.about-tech-table { width: 100%; border-collapse: collapse; }
.about-tech-table th, .about-tech-table td { padding: 12px 16px; border-bottom: 1px solid var(--border-color); text-align: left; }
.about-tech-table th { color: var(--text-secondary); }
.about-links { display: flex; gap: 24px; flex-wrap: wrap; }
.about-links a { color: var(--accent); text-decoration: none; }
.about-links a:hover { text-decoration: underline; }
```

- [ ] **Step 5: Build frontend and verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds without errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/AboutPage.jsx frontend/src/App.jsx frontend/src/components/Layout/Sidebar.jsx frontend/src/styles/global.css
git commit -m "feat: add About page with features, tech stack, and links"
```

---

### Task 4: Contact Page Component

**Files:**
- Create: `frontend/src/services/contactService.js`
- Create: `frontend/src/pages/ContactPage.jsx`

```js
// frontend/src/services/contactService.js
import api from "./api";

export const contactService = {
  submit: (data) => api.post("/api/contact", data),
  list: () => api.get("/api/contact/messages"),
  get: (id) => api.get(`/api/contact/messages/${id}`),
  markRead: (id) => api.patch(`/api/contact/messages/${id}/read`),
  delete: (id) => api.delete(`/api/contact/messages/${id}`),
};
```

```jsx
// frontend/src/pages/ContactPage.jsx
import { useState } from "react";
import { contactService } from "../services/contactService";

export default function ContactPage() {
  const [form, setForm] = useState({ name: "", email: "", subject: "", message: "" });
  const [errors, setErrors] = useState({});
  const [status, setStatus] = useState(null); // "success" | "error"
  const [submitting, setSubmitting] = useState(false);

  const validate = () => {
    const e = {};
    if (!form.name.trim()) e.name = "Name is required";
    if (!form.email.trim()) e.email = "Email is required";
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) e.email = "Invalid email format";
    if (!form.subject.trim()) e.subject = "Subject is required";
    if (!form.message.trim()) e.message = "Message is required";
    return e;
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const e2 = validate();
    if (Object.keys(e2).length > 0) { setErrors(e2); return; }
    setSubmitting(true);
    setStatus(null);
    try {
      await contactService.submit(form);
      setStatus("success");
      setForm({ name: "", email: "", subject: "", message: "" });
      setErrors({});
    } catch (err) {
      setStatus("error");
      setErrors({ form: err.response?.data?.detail || "Failed to send message" });
    } finally {
      setSubmitting(false);
    }
  };

  const handleChange = (field) => (e) => {
    setForm((prev) => ({ ...prev, [field]: e.target.value }));
    if (errors[field]) setErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  return (
    <div className="contact-page">
      <h1>Contact</h1>
      <p className="contact-subtitle">Have a question or feedback? Send us a message.</p>

      {status === "success" && (
        <div className="contact-success">✓ Message sent successfully! We will get back to you soon.</div>
      )}
      {status === "error" && (
        <div className="contact-error">✗ {errors.form || "Failed to send message. Please try again."}</div>
      )}

      <form onSubmit={handleSubmit} className="contact-form">
        <div className="form-row">
          <div className="form-group">
            <label>Name</label>
            <input type="text" value={form.name} onChange={handleChange("name")} placeholder="Your name" />
            {errors.name && <span className="field-error">{errors.name}</span>}
          </div>
          <div className="form-group">
            <label>Email</label>
            <input type="email" value={form.email} onChange={handleChange("email")} placeholder="your@email.com" />
            {errors.email && <span className="field-error">{errors.email}</span>}
          </div>
        </div>

        <div className="form-group">
          <label>Subject</label>
          <input type="text" value={form.subject} onChange={handleChange("subject")} placeholder="What is this about?" />
          {errors.subject && <span className="field-error">{errors.subject}</span>}
        </div>

        <div className="form-group">
          <label>Message</label>
          <textarea rows={6} value={form.message} onChange={handleChange("message")} placeholder="Your message..." />
          {errors.message && <span className="field-error">{errors.message}</span>}
        </div>

        <button type="submit" className="btn btn-primary" disabled={submitting}>
          {submitting ? "Sending..." : "Send Message"}
        </button>
      </form>
    </div>
  );
}
```

- [ ] **Step 1: Create the contact service**

Create `frontend/src/services/contactService.js`.

- [ ] **Step 2: Create the Contact page component**

Create `frontend/src/pages/ContactPage.jsx`.

- [ ] **Step 3: Add CSS styles**

Append to `frontend/src/styles/global.css`:

```css
/* Contact Page */
.contact-page { padding: 24px; max-width: 720px; }
.contact-subtitle { color: var(--text-secondary); margin-bottom: 24px; }
.contact-success { background: rgba(76,175,80,0.15); border: 1px solid var(--success); color: var(--success); padding: 12px 16px; border-radius: var(--radius-md); margin-bottom: 20px; }
.contact-error { background: rgba(244,67,54,0.15); border: 1px solid var(--error); color: var(--error); padding: 12px 16px; border-radius: var(--radius-md); margin-bottom: 20px; }
.contact-form { display: flex; flex-direction: column; gap: 20px; }
.form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.contact-form .form-group { display: flex; flex-direction: column; gap: 6px; }
.contact-form label { color: var(--text-secondary); font-size: 0.9rem; }
.contact-form input, .contact-form textarea { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-sm); padding: 10px 14px; color: var(--text-primary); font-size: 1rem; font-family: var(--font-family); }
.contact-form input:focus, .contact-form textarea:focus { outline: none; border-color: var(--accent); }
.contact-form textarea { resize: vertical; }
.field-error { color: var(--error); font-size: 0.85rem; }
.contact-form .btn { align-self: flex-start; }
```

- [ ] **Step 4: Build and verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/services/contactService.js frontend/src/pages/ContactPage.jsx frontend/src/styles/global.css
git commit -m "feat: add Contact page with validated form and submission"
```

---

### Task 5: Admin Messages Tab in Settings

**Files:**
- Modify: `frontend/src/pages/SettingsPage.jsx`
- Modify: `frontend/src/services/api.js` (add contact messages endpoint if not using contactService)

- [ ] **Step 1: Add "Messages" tab to Settings**

In `SettingsPage.jsx`, find the `tabs` array around line 340 and add:

```js
{ id: "messages", label: "Messages" },
```

Add import for contactService at top:
```js
import { contactService } from "../services/contactService";
```

- [ ] **Step 2: Add messages state and loading**

In the SettingsPage component, add state:

```js
const [messages, setMessages] = useState([]);
const [messagesLoading, setMessagesLoading] = useState(false);
const [expandedMessage, setExpandedMessage] = useState(null);
```

- [ ] **Step 3: Add message loading function**

```js
const loadMessages = async () => {
  setMessagesLoading(true);
  try {
    const res = await contactService.list();
    setMessages(res.data);
  } catch (err) {
    setError("Failed to load messages");
  } finally {
    setMessagesLoading(false);
  }
};
```

- [ ] **Step 4: Add Messages tab rendering**

After the api-keys tab block in the JSX, add:

```jsx
{activeTab === "messages" && (
  <div className="settings-section">
    <SettingSection title="Contact Messages">
      <p className="subtitle">Messages submitted through the contact form.</p>
      <button className="btn btn-secondary btn-sm" onClick={loadMessages} disabled={messagesLoading}>
        {messagesLoading ? "Loading..." : "Refresh"}
      </button>

      {messagesLoading && messages.length === 0 && <div className="loading">Loading messages...</div>}
      {!messagesLoading && messages.length === 0 && <div className="empty-messages"><p>No messages yet.</p></div>}

      <div className="messages-list">
        {messages.map((msg) => (
          <div key={msg.id} className={`message-item ${msg.is_read ? "read" : "unread"}`}>
            <div className="message-header" onClick={() => setExpandedMessage(expandedMessage === msg.id ? null : msg.id)}>
              <span className="message-sender">{msg.name}</span>
              <span className="message-email">{msg.email}</span>
              <span className="message-subject">{msg.subject}</span>
              <span className="message-date">{new Date(msg.created_at).toLocaleDateString()}</span>
              {!msg.is_read && <span className="message-unread-badge">New</span>}
            </div>
            {expandedMessage === msg.id && (
              <div className="message-body">
                <p>{msg.message}</p>
                <div className="message-actions">
                  {!msg.is_read && (
                    <button className="btn btn-sm" onClick={() => {
                      contactService.markRead(msg.id).then(() => loadMessages());
                    }}>Mark as Read</button>
                  )}
                  <button className="btn btn-sm btn-danger" onClick={() => {
                    contactService.delete(msg.id).then(() => {
                      setExpandedMessage(null);
                      loadMessages();
                    });
                  }}>Delete</button>
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </SettingSection>
  </div>
)}
```

- [ ] **Step 5: Add CSS for messages**

Append to `frontend/src/styles/global.css`:

```css
/* Messages Tab */
.messages-list { display: flex; flex-direction: column; gap: 8px; margin-top: 16px; }
.message-item { background: var(--bg-card); border: 1px solid var(--border-color); border-radius: var(--radius-md); overflow: hidden; }
.message-item.unread { border-left: 3px solid var(--accent); }
.message-item.read { border-left: 3px solid var(--text-muted); }
.message-header { display: grid; grid-template-columns: 1fr 2fr 2fr 100px auto; gap: 12px; align-items: center; padding: 12px 16px; cursor: pointer; }
.message-header:hover { background: var(--bg-hover); }
.message-sender { font-weight: 600; }
.message-email { color: var(--text-secondary); font-size: 0.9rem; }
.message-subject { font-weight: 500; }
.message-date { color: var(--text-secondary); font-size: 0.85rem; text-align: right; }
.message-unread-badge { background: var(--accent); color: white; font-size: 0.7rem; padding: 2px 8px; border-radius: 10px; }
.message-body { padding: 16px; border-top: 1px solid var(--border-color); }
.message-body p { color: var(--text-secondary); white-space: pre-wrap; margin-bottom: 12px; }
.message-actions { display: flex; gap: 8px; }
.message-actions .btn { font-size: 0.85rem; }
.btn-danger { background: var(--error); border-color: var(--error); color: white; }
.btn-danger:hover { opacity: 0.9; }
.empty-messages { text-align: center; padding: 40px; color: var(--text-muted); }
```

- [ ] **Step 6: Build and verify**

Run: `cd frontend && npm run build`
Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
git add frontend/src/pages/SettingsPage.jsx frontend/src/styles/global.css
git commit -m "feat: add Messages tab to Settings for admin contact inbox"
```

---

### Task 6: E2E Tests

**Files:**
- Create: `tests/e2e/about-contact.spec.js`

```js
// tests/e2e/about-contact.spec.js
const { test, expect } = require("@playwright/test");
const { loginAsAdmin } = require("./fixtures");

test.beforeEach(async ({ page }) => {
  await loginAsAdmin(page);
});

test.describe("About Page", () => {
  test("about page renders with features", async ({ page }) => {
    await page.goto("/about");
    await expect(page.getByRole("heading", { name: "HomeGallery" })).toBeVisible();
    await expect(page.getByText("AI-powered photo gallery")).toBeVisible();
    await expect(page.getByRole("heading", { name: "Features" })).toBeVisible();
    await expect(page.getByText("Smart Metadata")).toBeVisible();
    await expect(page.getByText("Visual Search")).toBeVisible();
  });

  test("about page shows tech stack", async ({ page }) => {
    await page.goto("/about");
    await expect(page.getByRole("heading", { name: "Tech Stack" })).toBeVisible();
    await expect(page.getByText("React 18")).toBeVisible();
    await expect(page.getByText("FastAPI")).toBeVisible();
  });

  test("about page has links", async ({ page }) => {
    await page.goto("/about");
    await expect(page.getByRole("link", { name: "GitHub Repository" })).toBeVisible();
    await expect(page.getByRole("link", { name: "Documentation" })).toBeVisible();
  });
});

test.describe("Contact Page", () => {
  test("contact page renders form", async ({ page }) => {
    await page.goto("/contact");
    await expect(page.getByRole("heading", { name: "Contact" })).toBeVisible();
    await expect(page.getByLabel("Name")).toBeVisible();
    await expect(page.getByLabel("Email")).toBeVisible();
    await expect(page.getByLabel("Subject")).toBeVisible();
    await expect(page.getByLabel("Message")).toBeVisible();
  });

  test("contact form validation shows errors", async ({ page }) => {
    await page.goto("/contact");
    await page.getByRole("button", { name: "Send Message" }).click();
    await expect(page.getByText("Name is required")).toBeVisible();
    await expect(page.getByText("Email is required")).toBeVisible();
  });

  test("contact form submits successfully", async ({ page }) => {
    await page.goto("/contact");
    await page.getByLabel("Name").fill("E2E Tester");
    await page.getByLabel("Email").fill("e2e@test.com");
    await page.getByLabel("Subject").fill("E2E Test");
    await page.getByLabel("Message").fill("This is an automated test message");
    await page.getByRole("button", { name: "Send Message" }).click();
    await expect(page.getByText("Message sent successfully")).toBeVisible();
  });

  test("admin sees messages in Settings", async ({ page }) => {
    // Submit a message first
    await page.goto("/contact");
    await page.getByLabel("Name").fill("E2E Admin Test");
    await page.getByLabel("Email").fill("admin@test.com");
    await page.getByLabel("Subject").fill("Admin View Test");
    await page.getByLabel("Message").fill("Test message for admin view");
    await page.getByRole("button", { name: "Send Message" }).click();
    await expect(page.getByText("Message sent successfully")).toBeVisible();

    // Check in Settings > Messages
    await page.goto("/settings");
    await page.getByRole("button", { name: "Messages" }).click();
    await page.waitForTimeout(500);
    await expect(page.getByText("E2E Admin Test")).toBeVisible();
    await expect(page.getByText("Admin View Test")).toBeVisible();
  });
});

test.describe("Sidebar Navigation", () => {
  test("about link in sidebar", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "About" }).click();
    await expect(page).toHaveURL(/.*\/about/);
  });

  test("contact link in sidebar", async ({ page }) => {
    await page.goto("/");
    await page.getByRole("link", { name: "Contact" }).click();
    await expect(page).toHaveURL(/.*\/contact/);
  });
});
```

- [ ] **Step 1: Create E2E test file**

Create `tests/e2e/about-contact.spec.js` with the test code above.

- [ ] **Step 2: Run E2E tests**

Run: `npx playwright test tests/e2e/about-contact.spec.js --reporter=list`
Expected: All tests pass (or fix any failures).

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/about-contact.spec.js
git commit -m "test: add E2E tests for About and Contact pages"
```

---

## Self-Review Checklist

- [x] **Spec coverage**: About page (Task 3), Contact form (Task 4), Messages API (Task 2), Admin inbox (Task 5), E2E tests (Task 6), Model (Task 1) — all spec items covered
- [x] **Placeholder scan**: No TBD/TODO/fill-in-the-blank patterns found
- [x] **Type consistency**: `contactService` methods match API endpoint paths; `ContactResponse` schema matches `ContactMessage` model fields; all uses of `get_current_admin_user` are consistent
- [x] **DRY**: Contact service reused in both ContactPage and SettingsPage; CSS uses existing CSS variables
- [x] **YAGNI**: No email sending, no pagination, no search in messages — kept minimal
