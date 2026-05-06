# Software Requirements Specification (SRS): Smart PG Management API

## 1. Project Overview
**Project Name:** Smart PG Management API
**Architecture:** Multi-Tenant SaaS (Software as a Service)
**Objective:** A lightweight, highly scalable backend system to automate daily operations, rent tracking, and resident communication for multiple Paying Guest (PG) owners in India.
**Primary Interfaces:** - Frontend App/Web Dashboard (for PG Owners)
- WhatsApp Webhook (for PG Residents)

## 2. Technical Stack
- **Backend Framework:** FastAPI (Python) - For async performance and auto-documentation.
- **Database (Development):** SQLite
- **Database (Production):** PostgreSQL
- **ORM:** SQLAlchemy or SQLModel
- **AI Provider:** Google Gemini API (Text parsing, JSON generation, OCR Vision)
- **Messaging:** Meta WhatsApp Business API or Twilio API
- **Authentication:** OAuth2 with Password Bearer (JWT Tokens)

## 3. Architectural Constraints
- **Multi-Tenancy:** Every database table (except the Owner table) MUST include a `pg_id` (Tenant ID) foreign key. All queries must be filtered by `pg_id` via the logged-in owner's JWT token to ensure absolute data isolation.
- **Statelessness:** The API must remain stateless to support horizontal scaling.
- **Asynchronous Processing:** Webhooks must return a `200 OK` status immediately. Heavy operations (AI parsing, bulk messaging) must be offloaded to FastAPI `BackgroundTasks` or a task queue like Celery.

## 4. Core Functional Requirements (MVP)

### 4.1 Owner Authentication & Provisioning
- API to register a new PG Owner.
- API to log in and generate a secure JWT token.

### 4.2 Property & Resident Management
- APIs to create, read, update, and delete (CRUD) Rooms and set `total_capacity`. 
  - *Note: `available_capacity` is calculated dynamically on the backend (total_capacity - active residents).*
- APIs to onboard residents, link them to specific rooms, track security deposits, and toggle `is_active` status (handling move-in/move-out dates).

### 4.3 Financial Management
- Automated generation of monthly rent invoices per resident.
- APIs to log full or partial payments, including storing the `transaction_ref_id` (e.g., UPI reference number).
- Generation of dynamic UPI deep links (e.g., `upi://pay?...`) for precise rent collection.

### 4.4 Notice Board
- API to broadcast announcements to all active residents of a specific PG via WhatsApp.

## 5. AI & Automation Requirements

### 5.1 Smart Complaint Routing
- **Input:** Unstructured WhatsApp text from resident via webhook.
- **Process:** AI extracts `room_number`, `issue_description`, `category`, and `urgency`.
- **Output:** Saves structured JSON to the database and sends an automated acknowledgment.
- **Fallback:** If AI fails, the raw message is saved with a "Needs Manual Review" status.

### 5.2 ID OCR Onboarding
- **Input:** Image of a resident's government ID (Aadhar, PAN, etc.).
- **Process:** Vision AI extracts name, date of birth, ID number, and address.
- **Output:** Auto-fills the resident registration JSON payload.

### 5.3 Automated Operations
- **Meal Headcount:** Scheduled background task sends a daily poll asking about dinner plans; AI parses replies to log `will_eat_dinner` status into the database for the cook's daily headcount.
- **Rent Reminders:** Scheduled background task triggers on the 1st of the month to automatically message residents with pending balances.

## 6. Database Schema Blueprint
Below are the core entities. All entities (except `pg_owners`) must include `pg_id` for multi-tenant security.

- **pg_owners:** `id`, `pg_name`, `owner_name`, `phone_number`, `hashed_password`
- **rooms:** `id`, `pg_id`, `room_number`, `total_capacity`
- **residents:** `id`, `pg_id`, `room_id`, `name`, `phone_number`, `monthly_rent`, `security_deposit`, `joined_date`, `move_out_date`, `is_active` (Boolean)
- **ledger:** `id`, `pg_id`, `resident_id`, `month_year`, `amount_due`, `amount_paid`, `transaction_ref_id`, `status` (Paid/Pending/Partial)
- **complaints:** `id`, `pg_id`, `resident_id`, `raw_whatsapp_msg`, `parsed_issue`, `category`, `urgency`, `is_resolved` (Boolean)
- **meal_logs:** `id`, `pg_id`, `resident_id`, `date`, `will_eat_dinner` (Boolean), `special_instructions` (String)

## 7. Security & Validation Rules
- Passwords must be hashed using `bcrypt` and `passlib` before storage.
- All API requests/responses must be strictly validated using Pydantic schemas.
- All environment variables and secrets (`DATABASE_URL`, `GEMINI_API_KEY`, `JWT_SECRET_KEY`) must be managed securely via a `.env` file and Pydantic `BaseSettings`. Never hardcode secrets.
