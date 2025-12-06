# Contributing to Series

## Development Setup

1. **Clone the repository**
   ```bash
   git clone <repo-url>
   cd Series
   ```

2. **Set up Python environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

4. **Set up database**
   - Run migrations in `migrations/` folder in order
   - See `PROJECT_STRUCTURE.md` for migration order

5. **Run tests**
   ```bash
   python -m pytest tests/
   ```

## Code Style

- Follow PEP 8 for Python
- Use async/await for I/O operations
- Add docstrings to functions
- Type hints where helpful

## Pull Request Process

1. Create a feature branch
2. Make your changes
3. Add tests if applicable
4. Update documentation
5. Submit PR with description

## Project Structure

See `PROJECT_STRUCTURE.md` for detailed organization.

