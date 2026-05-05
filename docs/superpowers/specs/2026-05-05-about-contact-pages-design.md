# Design Spec: About & Contact Pages

**Date**: 2026-05-05
**Status**: Draft
**Author**: Agent-driven

## Overview

Two new pages: an **About** page (static project info) and a **Contact** page (message form with admin inbox). Both accessible from the sidebar navigation.

## Feature 1: About Page

### Route
- Frontend: `/about`
- No backend endpoint needed

### Content Sections

1. **Hero**: App name "HomeGallery", tagline, version badge
2. **Features Grid**: 6 cards — Smart Metadata, Auto-Organization, Enhancement, Content Analysis, Visual Search, MCP Integration
3. **Tech Stack Table**: Frontend, Backend, Database, Agents, Testing
4. **Links**: GitHub repo, Documentation, License

### Files Created
- `frontend/src/pages/AboutPage.jsx`

### Files Modified
- `frontend/src/App.jsx` — Add `<Route path="/about" element={<AboutPage />} />`
- `frontend/src/components/Layout/Sidebar.jsx` — Add "ℹ️ About" link

## Feature 2: Contact Page

### Frontend Route
- `/contact`
- Form with fields: Name (required), Email (required, validated), Subject (required), Message (required, textarea)
- POST to `/api/contact`, show success/error feedback
- Reset form on success
- Sidebar link: "✉️ Contact"

### Backend Model

**File**: `backend/app/models/contact.py`

```python
class ContactMessage(Base):
    __tablename__ = "contact_messages"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    subject = Column(String(500), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
```

### Backend API

**File**: `backend/app/api/contact.py`

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/contact` | Public (rate limited) | Submit contact form |
| GET | `/contact/messages` | Admin only | List all messages |
| GET | `/contact/messages/{id}` | Admin only | Get single message |
| PATCH | `/contact/messages/{id}/read` | Admin only | Mark as read |
| DELETE | `/contact/messages/{id}` | Admin only | Delete message |

**Rate Limiting**: 3 submissions per 15 minutes per IP (using same pattern as login rate limiting).

### Admin UI

- New "Messages" tab in Settings page (`SettingsPage.jsx`)
- List of messages with: sender name, email, subject, date, read/unread badge
- Click to expand full message content
- Mark as read / delete buttons per message
- Empty state: "No messages yet"

### Files Created
1. `backend/app/models/contact.py`
2. `backend/app/api/contact.py`
3. `frontend/src/pages/ContactPage.jsx`
4. `frontend/src/services/contactService.js` — API helper
5. `tests/unit/test_contact_model.py`
6. `tests/unit/test_contact_api.py`

### Files Modified
1. `frontend/src/App.jsx` — Add routes for `/about` and `/contact`
2. `frontend/src/components/Layout/Sidebar.jsx` — Add About and Contact links
3. `frontend/src/pages/SettingsPage.jsx` — Add "Messages" tab
4. `backend/app/models/__init__.py` — Export ContactMessage
5. `backend/app/api/__init__.py` — Register contact router
6. `frontend/src/styles/global.css` — Add styles for contact form, messages list

## Testing

### Unit Tests
- `ContactMessage` model creation and fields
- POST `/contact` — success, validation errors, rate limiting
- GET `/contact/messages` — admin only, returns messages
- PATCH read, DELETE — admin only

### E2E Tests
- Contact form submission
- Admin messages tab view
- About page renders correctly

## Security

- Contact form is public but rate limited (3/15min per IP)
- Input sanitization on all form fields (prevent XSS)
- Messages admin-only via `get_current_admin_user`
- No email sending — messages stored locally only
- Email field validated for format but not verified
