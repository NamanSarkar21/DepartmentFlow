# DepartmentFlow — Departmental Activity & Approval Management

A workflow-based web application for managing UG/PG departmental requests, faculty review, HOD approvals, project listings/allocation, and user administration.

## Features
- Role-based access: Student, Faculty, HOD, Admin.
- UG/PG activity requests with a review workflow.
- Faculty review: forward to HOD, request changes, or reject.
- HOD decision: approve, request changes, or reject.
- Project publication and one-student project allocation.
- User creation by HOD/Admin.
- Activity log for request workflow decisions.
- SQLite database created automatically on first run.
- Responsive interface with dashboard cards and status labels.

## Tech stack
Python 3, Flask, SQLite, HTML, CSS, Jinja templates.

## Run locally (Windows / VS Code / PowerShell)

```powershell
cd department_workflow_system
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
py app.py
```

Open http://127.0.0.1:5000

If PowerShell blocks activation, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` in that terminal, then activate again.

## Demo accounts
All demo accounts use local-only sample data. Change passwords and the Flask secret before deployment.

| Role | Email | Password |
|---|---|---|
| Admin | admin@dept.local | Admin123! |
| HOD | hod@dept.local | Hod123! |
| Faculty | faculty@dept.local | Faculty123! |
| UG Student | student@dept.local | Student123! |
| PG Student | pgstudent@dept.local | Student123! |

## Workflow

1. Student/faculty submits a departmental request.
2. Request enters **Pending Faculty Review**.
3. Faculty forwards it to the HOD, requests changes, or rejects it.
4. HOD approves, requests changes, or rejects a request forwarded for approval.
5. The submitter can track status and comments.
6. Faculty/HOD/Admin publishes projects. A matching UG/PG student can allocate an open project.

## Main routes
- `/login`, `/logout`
- `/dashboard`
- `/requests`, `/requests/new`, `/requests/<id>`
- `/projects`, `/projects/new`
- `/users` (HOD/Admin)
- `/workflow`

## Project structure
```text
department_workflow_system/
├── app.py
├── requirements.txt
├── README.md
├── DESIGN.md
├── department.db             # created at runtime
├── templates/
│   ├── base.html
│   ├── login.html
│   ├── dashboard.html
│   ├── requests.html
│   ├── request_form.html
│   ├── request_detail.html
│   ├── projects.html
│   ├── project_form.html
│   ├── users.html
│   ├── workflow.html
│   └── error.html
└── static/
    └── style.css
```

## Notes before real deployment
This is a functional academic prototype, not a production-hardened institutional system. Before deployment, use HTTPS, a strong environment-based secret key, CSRF protection, rate limiting, institutional SSO, backups, audit-log protections, and formal data-retention/access policies. Add migrations and automated tests for production use. Do not use the demo credentials outside a local demo.
