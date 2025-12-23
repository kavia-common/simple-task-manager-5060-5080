#!/bin/bash
cd /tmp/kavia/workspace/code-generation/simple-task-manager-5060-5080/todo_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

