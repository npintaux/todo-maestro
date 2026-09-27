#!/usr/bin/env bash
# Smoke test script for TaskFlow container and WSGI application
set -euo pipefail

BASE_URL="${1:-http://localhost:8080}"
echo "=================================================="
echo "▶ Running TaskFlow Production Smoke Tests on $BASE_URL"
echo "=================================================="

# 1. Health check probe
echo "1. Checking health endpoint (/healthz)..."
HEALTH_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/healthz" || true)
if [ "$HEALTH_STATUS" = "200" ]; then
    echo "   ✅ Health check passed (200 OK)"
else
    echo "   ❌ Health check failed with status $HEALTH_STATUS"
    exit 1
fi

# 2. Root redirect
echo "2. Checking root redirect (/ -> /tasks)..."
REDIRECT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/" || true)
if [ "$REDIRECT_STATUS" = "302" ]; then
    echo "   ✅ Root redirect passed (302 Found)"
else
    echo "   ❌ Root redirect failed with status $REDIRECT_STATUS"
    exit 1
fi

# 3. Tasks UI Dashboard
echo "3. Checking UI dashboard (/tasks)..."
UI_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/tasks" || true)
if [ "$UI_STATUS" = "200" ]; then
    echo "   ✅ UI dashboard passed (200 OK)"
else
    echo "   ❌ UI dashboard failed with status $UI_STATUS"
    exit 1
fi

# 4. REST Task creation and listing
echo "4. Checking REST Task API (/v1/tasks)..."
CREATE_RESP=$(curl -s -X POST "$BASE_URL/v1/tasks" \
    -H "Content-Type: application/json" \
    -H "X-User-Id: smoke_test_user" \
    -d '{"title": "Smoke Test Task", "priority": "high"}')
echo "   Create response: $CREATE_RESP"

TASK_ID=$(echo "$CREATE_RESP" | grep -o '"id": *"[^"]*"' | head -n1 | cut -d'"' -f4)
if [ -n "$TASK_ID" ]; then
    echo "   ✅ Task creation passed (ID: $TASK_ID)"
else
    echo "   ❌ Task creation failed"
    exit 1
fi

# 5. Audit Service API
echo "5. Checking Audit Service REST API (/v1/audit/events)..."
AUDIT_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/v1/audit/events" \
    -H "X-User-Id: smoke_test_user" \
    -H "X-User-Role: auditor" || true)
if [ "$AUDIT_STATUS" = "200" ]; then
    echo "   ✅ Audit search passed (200 OK)"
else
    echo "   ❌ Audit search failed with status $AUDIT_STATUS"
    exit 1
fi

echo "=================================================="
echo "🎉 ALL SMOKE TESTS PASSED SUCCESSFULLY!"
echo "=================================================="
