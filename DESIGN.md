# Software Interface & Workflow Design

## 1. Objective
Provide one departmental portal for UG/PG activity requests, faculty/HOD approval, and project allocation.

## 2. Actors and permissions

| Actor | Main permissions |
|---|---|
| Student | Submit requests, view own requests, browse eligible projects, allocate an open project |
| Faculty | Submit requests, review requests, publish projects |
| HOD | Final decision on faculty-forwarded requests, publish projects, create users |
| Admin | Review workflow, publish projects, create users |

## 3. Request state model

```text
[Student/Faculty submits]
          |
          v
[Pending Faculty Review]
     |       |       |
  Forward  Changes  Reject
     |       |       |
     v       v       v
[Pending HOD] [Faculty Changes Requested] [Rejected]
     |
     +---- Approve ----> [Approved]
     |
     +---- Changes ----> [HOD Changes Requested]
     |
     +---- Reject -----> [Rejected]
```

Faculty can review newly submitted requests and requests returned for faculty changes. HOD can decide only on requests in `Pending HOD Approval`. Request state and comments are recorded with timestamps.

## 4. Core data model
- **User**: name, email, password hash, role, UG/PG program.
- **Request**: title, category, description, program, submitter, faculty reviewer, status, comments, created/updated timestamps.
- **Project**: title, description, program, supervisor, seats (prototype currently allocates one student per project), status.
- **ActivityLog**: actor, entity type/id, action, note, timestamp.

## 5. Interface design
- **Login**: clear email/password form and demo-account hints.
- **Dashboard**: high-level counts, latest requests, project list.
- **Requests**: filter-free list with status, submitter, program, date, and detail links.
- **Request detail**: status, request text, faculty/HOD comments, review actions for authorized roles.
- **Projects**: open/allocated states, supervisor and programme shown; students can allocate matching open projects.
- **Users**: HOD/Admin-only user creation and directory.
- **Workflow**: visual state progression and role summary.

## 6. Validation and security controls in this prototype
- Passwords are stored as Werkzeug hashes.
- SQL statements use parameterized queries.
- Role decorators protect privileged routes.
- Students may only view their own request details.
- Project programme is checked against the student's programme.
- Production requirements: CSRF protection, HTTPS, secure secret management, SSO/MFA, backups, audit retention and tests.
