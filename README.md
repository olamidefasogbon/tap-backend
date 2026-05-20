# Tap Backend Engine
A highly scalable, decoupled financial transaction and collection API built with Python. 

## Architecture & Features
- **Asynchronous Task Queue:** Managed through background workers for low-latency transaction flows.
- **Database Lifecycle Management:** Implemented utilizing SQLAlchemy ORM coupled with Alembic for structured schema migrations.
- **Layered Design Pattern:** Strict separation of concerns across Routers, Schemas, Domain Services, and Data Models.
- **Containerized Stack:** Equipped with Docker Compose for uniform infrastructure orchestration.
