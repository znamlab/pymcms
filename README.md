# pymcms

[![Python uv CI](https://github.com/znamlab/pymcms/actions/workflows/python-uv-ci.yml/badge.svg?branch=main)](https://github.com/znamlab/pymcms/actions/workflows/python-uv-ci.yml)
[![Private PyPI](https://github.com/znamlab/pymcms/actions/workflows/gitlab-pypi-publish.yml/badge.svg)](https://github.com/znamlab/pymcms/actions/workflows/gitlab-pypi-publish.yml)

Wrapper to interact with MCMS API

API is documented there: https://crick-uat.colonymanagement.org/api/swagger-ui/index.html

The current version provides only access to `get_animal` and `get_procedures`

## Development

Install the locked development environment and run the checks with [uv](https://docs.astral.sh/uv/):

```shell
uv sync --group dev
uv run ruff check .
uv run ruff format --check .
uv run ty check
uv run pytest
```
