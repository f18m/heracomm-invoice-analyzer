# AGENTS.md

## Purpose
This file defines the operating permissions for automated agents working on this repository.

## General authorization
Agents are authorized to run all Python file validation commands in this project without asking for confirmation.

This authorization covers static checks, import checks, bytecode compilation, and non-destructive execution checks.

## Authorized Python validation commands
The following commands are always authorized:

- `python -m py_compile <file.py>`
- `python -m compileall .`
- `python -m pip install -e .`
- `python -m pip check`
- `python -c "import <module>; print(<module>.__version__)"`
- `python <script.py> --help`

Equivalent commands with the same validation purpose are also authorized, as long as they do not modify user data or system configuration.

## Limits and safety
The following are not automatically authorized:

- destructive commands (for example, mass deletions or hard resets)
- commands requiring credentials or secrets
- commands that modify external infrastructure

If there is any doubt about impact or destructiveness, the agent must stop and ask for confirmation.
