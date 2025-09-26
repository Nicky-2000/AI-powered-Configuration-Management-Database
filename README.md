
# AI-Powered Configuration Management Database

A lightweight CMDB with an **AI-powered natural-language -> SQL** interface and a simple Streamlit client.


## How to Run

### Start the FastAPI server
**FastAPI** was chosen because it makes it easy to develop something of this complexity level in such a short time frame.

```bash
./run_server.sh
```
This script will install dependencies and then run the app/main.py and serves on http://127.0.0.1:8000.
**Note:** On startup we load in a NL -> SQL model from hugging face which might take a minute or two (depending on internet speed). It is a small model, but I prefer to have the model run locally becuase this makes the code more portable because we don't need to deal with inference API tokens. We cache the model in `hf-cache` so we only need to do the network load one time.

### Start the Streamlit client
```bash
./run_client.sh
```

### How to use the client interface to interact with the server
On the main page

This starts a lightweight web interface that enables easy interaction with the server.

## How the Server Works
In short, the server, creates DB tables, loads the small text-to-SQL model, and registers routers.
| Endpoint   | Method | Purpose                                                          |
| ---------- | ------ | ---------------------------------------------------------------- |
| `/ingest`  | POST   | Bulk-load users, devices, apps, and user-app links.              |
| `/users`   | GET    | List users with optional filters (`status`, `mfa`, `app`, etc.). |
| `/devices` | GET    | List devices with optional filters (`status`, `location`, …).    |
| `/apps`    | GET    | List apps, name search supported.                                |
| `/ci/{id}` | GET    | Fetch any configuration item (user/device/app) by ID.            |
| `/ask`     | POST   | Natural language -> SQL -> JSON rows.                            |
| `/healthz` | GET    | Health check and model readiness.                                |

### File Flow
routers/ingest.py -> validates and normalizes incoming JSON and updates or inserts rows.
routers/read.py -> implements /users, /devices, /apps, /ci/{id}.
routers/ask.py -> calls the local Hugging Face model (loaded via app/nl/model_loader.py) to translate a question into a safe SQL query, executes it, and returns the rows.


### Data Model
Implemented with SQLAlchemy (app/models.py):

- User: (user_id, name, email, mfa_enabled, status, etc.)
- App: (app_id (auto-increment), name, owner, type)
- Device (device_id, hostname, assigned_user (stores the user_id string), encryption, location, etc.)
- UserApp: (many-to-many link table (user_id, app_name))
[ Miro diagram placeholder: ERD of tables and relationships ]

### Why SQL (vs NoSQL/Graph)
- Strong schema & joins: Users, Devices, and Apps map naturally to relational tables. Constraints catch bad data early and LLMs can safely generate SELECT queries.
- Easy to migrate to a more scalable system like Postgres
- Easier to guardrail one clean schema than free-form NoSQL or graph queries.

### Future Directions
- Graph export for relationship queries
- Nightly job to dump the SQL DB into a graph store (Neo4j/Memgraph) for questions that require more hops between tables
- Redis/Valkey cache: Cache hot /ask and /read queries.
- Better NL->SQL: Put in a bigger model!! We are using a super small one right now: "NumbersStation/nsql-350M"
- AI normalizer: Plug an LLM into the NormalizerPipeline to auto-clean names, OS strings, etc.

## Testing
pytest was chosen for its simplicity and code coverage functionality

#### Run all the tests
```bash
pytest -q
```

#### Run all the tests with coverage
```bash
pytest --cov=app --cov-report=term-missing
```

Currently there is "72%" test coverage

#### Where the tests live:

| File                      | What it tests                          |
| ------------------------- | -------------------------------------- |
| `test_ingest_endpoint.py` | POST /ingest end-to-end                |
| `test_read_endpoints.py`  | GET /users, /devices, /apps, /ci/{id}` |
| `test_ask_endpoint.py`    | Natural-language queries -> SQL        |
| `test_sql_sanitizer.py`   | Unit tests for the SQL guardrails      |


## Full Project Structure: 
AI-powered-Configuration-Management-Database/
├─ app/
│  ├─ main.py               # FastAPI entry point
│  ├─ db.py                 # DB engine & session
│  ├─ models.py             # SQLAlchemy models
│  ├─ routers/
│  │   ├─ ingest.py
│  │   ├─ read.py
│  │   └─ ask.py
│  └─ nl/
│      ├─ model_loader.py
│      └─ naturalsql_local.py
├─ client/                  # Streamlit UI
├─ tests/                   # Pytest suite (integration + unit)
└─ hf-cache/                # Hugging Face model cache (ignored in git)
