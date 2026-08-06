# red-id

[![Backend CI](https://github.com/Kasarch/red-id/actions/workflows/backend-ci.yml/badge.svg?branch=master)](https://github.com/Kasarch/red-id/actions/workflows/backend-ci.yml)
[![Coverage](https://raw.githubusercontent.com/Kasarch/red-id/badges/coverage.svg)](https://github.com/Kasarch/red-id/actions/workflows/backend-ci.yml)

Backend CI checks formatting, linting, static types, PostgreSQL migrations, tests, and production-code coverage.

Run the same coverage command locally from `app/backend`:

```bash
pytest --junitxml=test-results.xml --cov=src --cov-report=term-missing --cov-report=xml:coverage.xml
```
