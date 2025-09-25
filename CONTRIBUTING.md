# Contributing to BisonGuard

First off, thank you for considering contributing to BisonGuard! It's people like you that make BisonGuard such a great tool for wildlife conservation.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code. Please report unacceptable behavior to bisonguard@example.com.

## How Can I Contribute?

### Reporting Bugs

Before creating bug reports, please check existing issues as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* **Use a clear and descriptive title**
* **Describe the exact steps to reproduce the problem**
* **Provide specific examples to demonstrate the steps**
* **Describe the behavior you observed and what behavior you expected**
* **Include screenshots and animated GIFs if possible**
* **Include your environment details** (OS, Python version, GPU model, etc.)

### Suggesting Enhancements

Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* **Use a clear and descriptive title**
* **Provide a step-by-step description of the suggested enhancement**
* **Provide specific examples to demonstrate the steps**
* **Describe the current behavior and explain the expected behavior**
* **Explain why this enhancement would be useful**

### Pull Requests

1. Fork the repo and create your branch from `main`
2. If you've added code that should be tested, add tests
3. If you've changed APIs, update the documentation
4. Ensure the test suite passes
5. Make sure your code follows the existing code style
6. Issue that pull request!

## Development Setup

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/BisonGuard.git
   cd BisonGuard
   ```

2. **Set up Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt  # Development dependencies
   ```

4. **Run Tests**
   ```bash
   python test_analytics.py
   ```

## Coding Standards

### Python Style Guide

We follow PEP 8 with the following additions:
* Line length: 100 characters
* Use type hints where possible
* Document all functions with docstrings

### JavaScript Style Guide

* Use ES6+ features
* Semicolons are required
* 2 spaces for indentation
* Use `const` and `let`, avoid `var`

### Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line

Example:
```
Add real-time herd clustering analysis

- Implement DBSCAN clustering for herd grouping
- Add visualization for cluster boundaries
- Update analytics engine with cluster metrics

Fixes #123
```

## Project Structure

```
BisonGuard/
├── flask_dashboard.py      # Main Flask application
├── analytics_engine.py     # Analytics processing
├── track.py               # Video processing
├── rtsp_bison_tracker_2.py # RTSP stream handler
├── templates/             # HTML templates
├── static/               # CSS, JS, images
├── tests/               # Test files
└── docs/               # Documentation
```

## Testing

### Running Tests
```bash
# Run all tests
python test_analytics.py

# Run specific test
python -m unittest test_analytics.TestBisonDetection

# Run with coverage
coverage run test_analytics.py
coverage report
```

### Writing Tests
* Write tests for any new functionality
* Maintain test coverage above 80%
* Use meaningful test names that describe what is being tested
* Include both positive and negative test cases

## Documentation

* Update README.md if you change functionality
* Update API_DOCUMENTATION.md for API changes
* Add docstrings to all new functions
* Include inline comments for complex logic

## Review Process

1. **Automated checks** run on all PRs (tests, linting)
2. **Code review** by at least one maintainer
3. **Testing** in development environment
4. **Approval and merge** by maintainer

## Recognition

Contributors will be recognized in:
* The README.md file
* Release notes
* Project website (when available)

## Questions?

Feel free to open an issue with the tag "question" or reach out to the maintainers directly.

Thank you for contributing to wildlife conservation through technology!
