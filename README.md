## Project Structure

```
link-server/
├── mess-user/          # User & authentication service
├── mess-message/       # Messaging service
├── mess/               # Kong API Gateway configuration
├── pyproject.toml      # Poetry dependency management
├── poetry.lock         # Locked dependency versions
├── dev.ps1             # PowerShell development script (Windows)
└── Makefile            # Make commands (Unix/WSL)
```

## Setup

### Prerequisites

- Python 3.14+
- Poetry (install via: `pip install poetry`)
- Poetry export plugin: `poetry self add poetry-plugin-export`
- Make (optional, for convenience commands)

### Installation

```bash
# Install all dependencies
poetry install

# Generate requirements.txt for each service (needed for Docker builds)
make requirements

# Or use make for both steps
make install-all
```

## Dependency Management

This project uses **Poetry** for local development and generates per-service `requirements.txt` files for Docker builds.

### How it works

1. **Core dependencies** (shared by all services) are in `[tool.poetry.dependencies]`
2. **Service-specific dependencies** are in `[tool.poetry.group.mess-<service>.dependencies]`
3. Run `make requirements` to generate `mess-*/requirements.txt` files with:
   - All core dependencies
   - Service-specific dependencies
   - All transitive dependencies (automatically resolved)

### Adding dependencies

```bash
# Add a core dependency (used by all services)
poetry add <package>

# Add a service-specific dependency
poetry add --group mess-user <package>

# Update poetry.lock and regenerate requirements.txt
poetry lock
make requirements
```

The Makefile uses pattern rules to regenerate `requirements.txt` only when `pyproject.toml` or `poetry.lock` changes.

## Development

### Running Services Locally

```bash
# Using make
make user      # Runs on port 8002
make message   # Runs on port 8003

# Or manually with Poetry
cd mess-user && poetry run uvicorn mess_user.main:app --reload --port 8002
cd mess-message && poetry run uvicorn mess_message.main:app --reload --port 8003
```

### Managing Dependencies

All dependencies are managed through Poetry in the root `pyproject.toml`.

#### Adding a New Dependency
```bash
# Add a dependency for all services
poetry add <package-name>

# Add a dev dependency
poetry add --group dev <package-name>

# After adding dependencies, regenerate requirements.txt files
poetry run python generate_requirements.py
```

#### Updating Dependencies
```bash
# Update all dependencies
poetry update

# Regenerate requirements.txt after updates
poetry run python generate_requirements.py
```

### Code Quality

```bash
# Using make
make format    # Format code with Black and Ruff
make lint      # Check code with linters
make clean     # Remove cache files

# Or manually with Poetry
poetry run black .
poetry run ruff check --fix .
```

## Service-Specific Requirements

Each service has its own `requirements.txt` file generated from the main Poetry configuration:

- **mess-user**: User & auth dependencies (FastAPI, SQLAlchemy, python-jose, passlib)
- **mess-message**: Messaging dependencies (FastAPI, SQLAlchemy, httpx, redis)

These files are used by Docker for containerized deployments while Poetry is used for local development.

## Docker Deployment

Each service has a Dockerfile that uses its respective `requirements.txt`:

```bash
docker build -t mess-user ./mess-user
docker build -t mess-message ./mess-message
```

## Database Migrations

Each service has its own Alembic configuration for database migrations:

```bash
# Run migrations for a specific service
cd mess-user && poetry run alembic upgrade head
cd mess-message && poetry run alembic upgrade head
```

## Available Commands

### Make Commands (Cross-platform)
- `make install` - Install dependencies
- `make install-all` - Install and generate requirements
- `make requirements` - Generate requirements.txt files
- `make user/message` - Start services
- `make lint` - Run linters
- `make format` - Format code
- `make clean` - Clean cache

### Manual Commands
```bash
poetry install                              # Install dependencies
poetry run python generate_requirements.py  # Generate requirements.txt
poetry run uvicorn <service>.main:app --reload  # Run a service
poetry run black .                          # Format code
poetry run ruff check .                     # Lint code
```

## Debugging

Since all dependencies are installed via Poetry, you can debug any service directly in your IDE:

1. Set up your IDE to use the Poetry virtual environment
2. Set the working directory to the service folder (e.g., `mess-user`)
3. Run the service's main module (e.g., `mess_user.main:app`)

### Getting the Poetry Virtual Environment Path
```bash
poetry env info --path
```

## Architecture

The platform consists of two microservices:

1. **mess-user**: Manages user registration, authentication, token management, and profile queries
2. **mess-message**: Handles real-time messaging and chat functionality

All services communicate through a Kong API Gateway (configured in `mess/`).
