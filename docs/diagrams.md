# Smart PG Management API — Diagrams

Both diagrams use [Mermaid](https://mermaid.js.org/) and render natively on
GitHub. They are derived from `requirements.md` and the module layout in
`README.md`.

## 1. Requirements Diagram

SysML-style decomposition of the SRS into functional, AI, and
non-functional requirements with their inter-dependencies.

```mermaid
requirementDiagram

requirement SRS {
  id: 1
  text: "Smart PG Management API - multi-tenant SaaS backend"
  risk: medium
  verifymethod: test
}

%% --- Functional ---
functionalRequirement Auth {
  id: 4.1
  text: "PG owner registration and JWT login"
  risk: high
  verifymethod: test
}

functionalRequirement PropertyMgmt {
  id: 4.2.1
  text: "CRUD rooms with dynamic available_capacity"
  risk: low
  verifymethod: test
}

functionalRequirement ResidentMgmt {
  id: 4.2.2
  text: "Onboard residents, deposits, move-in/move-out"
  risk: medium
  verifymethod: test
}

functionalRequirement Finance {
  id: 4.3
  text: "Monthly invoices, payments, UPI deep links"
  risk: high
  verifymethod: test
}

functionalRequirement Notices {
  id: 4.4
  text: "Broadcast announcements via WhatsApp"
  risk: low
  verifymethod: test
}

%% --- AI / Automation ---
functionalRequirement ComplaintRouting {
  id: 5.1
  text: "AI parses WhatsApp complaints into structured JSON"
  risk: high
  verifymethod: test
}

functionalRequirement IDOcr {
  id: 5.2
  text: "Vision AI extracts ID fields for resident onboarding"
  risk: medium
  verifymethod: test
}

functionalRequirement MealPoll {
  id: 5.3.1
  text: "Daily meal poll, AI-parsed replies, headcount log"
  risk: medium
  verifymethod: test
}

functionalRequirement RentReminders {
  id: 5.3.2
  text: "Monthly auto-reminders for pending balances"
  risk: medium
  verifymethod: test
}

%% --- Non-functional ---
performanceRequirement WebhookFast {
  id: 3.3
  text: "Webhook returns 200 OK before heavy work"
  risk: high
  verifymethod: test
}

performanceRequirement Stateless {
  id: 3.2
  text: "Stateless API to allow horizontal scaling"
  risk: low
  verifymethod: inspection
}

interfaceRequirement MultiTenant {
  id: 3.1
  text: "Every non-owner row scoped by pg_id from JWT"
  risk: high
  verifymethod: test
}

interfaceRequirement ProviderAgnostic {
  id: 3.4
  text: "AI and WhatsApp accessed via Protocol abstractions"
  risk: low
  verifymethod: inspection
}

functionalRequirement Security {
  id: 7
  text: "bcrypt hashing, Pydantic validation, secrets via env"
  risk: high
  verifymethod: test
}

%% --- Relationships ---
SRS - contains -> Auth
SRS - contains -> PropertyMgmt
SRS - contains -> ResidentMgmt
SRS - contains -> Finance
SRS - contains -> Notices
SRS - contains -> ComplaintRouting
SRS - contains -> IDOcr
SRS - contains -> MealPoll
SRS - contains -> RentReminders
SRS - contains -> WebhookFast
SRS - contains -> Stateless
SRS - contains -> MultiTenant
SRS - contains -> ProviderAgnostic
SRS - contains -> Security

ResidentMgmt - derives -> IDOcr
Finance - derives -> RentReminders
Notices - derives -> MealPoll
ComplaintRouting - derives -> WebhookFast
PropertyMgmt - traces -> MultiTenant
ResidentMgmt - traces -> MultiTenant
Finance - traces -> MultiTenant
Auth - traces -> Security
```

## 2. Use-Case Diagram

Mermaid has no native use-case diagram, so this is a flowchart styled to
read like one. Actors are on the left and right; ellipses are use cases;
the rounded box is the system boundary.

```mermaid
flowchart LR
  %% Actors
  Owner(["👤 PG Owner"])
  Resident(["👤 PG Resident"])
  Scheduler(["⏰ Celery Beat"])
  AI(["🤖 Gemini AI"])
  WA(["💬 WhatsApp API"])

  subgraph System["Smart PG Management API"]
    direction TB

    UC_Register(("Register / Login"))
    UC_Profile(("Update profile / UPI VPA"))
    UC_Rooms(("Manage rooms"))
    UC_Residents(("Manage residents"))
    UC_Onboard(("Onboard via ID OCR"))
    UC_Invoices(("Generate monthly invoices"))
    UC_Payments(("Log payments"))
    UC_UPILink(("Get UPI deep link"))
    UC_Notice(("Broadcast notice"))
    UC_ViewComplaints(("View / resolve complaints"))
    UC_Headcount(("View meal headcount"))

    UC_SendMsg(("Send WhatsApp message"))
    UC_Complaint(("Raise complaint"))
    UC_MealReply(("Reply to meal poll"))

    UC_Webhook(("Inbound webhook dispatch"))
    UC_DailyPoll(("Daily meal poll job"))
    UC_RentReminder(("Monthly rent reminder job"))

    UC_ParseText(("Parse text → structured JSON"))
    UC_ParseID(("OCR ID image"))
  end

  %% Owner ↔ system
  Owner --> UC_Register
  Owner --> UC_Profile
  Owner --> UC_Rooms
  Owner --> UC_Residents
  Owner --> UC_Onboard
  Owner --> UC_Invoices
  Owner --> UC_Payments
  Owner --> UC_UPILink
  Owner --> UC_Notice
  Owner --> UC_ViewComplaints
  Owner --> UC_Headcount

  %% Resident ↔ system (via WhatsApp)
  Resident --> UC_SendMsg
  UC_SendMsg --> WA
  WA --> UC_Webhook
  UC_Webhook -.includes.-> UC_Complaint
  UC_Webhook -.includes.-> UC_MealReply

  %% Scheduler-driven jobs
  Scheduler --> UC_DailyPoll
  Scheduler --> UC_RentReminder
  UC_DailyPoll --> WA
  UC_RentReminder --> WA
  UC_Notice --> WA

  %% AI involvement
  UC_Complaint -.includes.-> UC_ParseText
  UC_MealReply -.includes.-> UC_ParseText
  UC_Onboard  -.includes.-> UC_ParseID
  UC_ParseText --> AI
  UC_ParseID --> AI

  %% Styling
  classDef actor fill:#fff,stroke:#333,stroke-width:1.5px;
  classDef system fill:#f5f7fa,stroke:#888,stroke-dasharray:3 3;
  class Owner,Resident,Scheduler,AI,WA actor;
  class System system;
```

### Legend

- **Solid arrow** — actor initiates / participates in a use case.
- **Dotted `includes`** — child use case is always invoked by the parent
  (UML `<<include>>`).
- **System boundary** — the dashed rounded box; everything inside is
  delivered by this API.
