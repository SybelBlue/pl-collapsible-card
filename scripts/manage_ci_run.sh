#!/usr/bin/env bash

set -euo pipefail

root=$(git rev-parse --show-toplevel)

github_repository_from_origin() {
    local origin repository
    if ! origin=$(git -C "$root" remote get-url origin 2>/dev/null); then
        echo "No origin remote is configured; add a GitHub origin or set CI_REPOSITORY." >&2
        return 2
    fi

    case "$origin" in
        https://github.com/*) repository=${origin#https://github.com/} ;;
        git@github.com:*) repository=${origin#git@github.com:} ;;
        ssh://git@github.com/*) repository=${origin#ssh://git@github.com/} ;;
        *)
            echo "Origin is not a supported GitHub URL; set CI_REPOSITORY explicitly." >&2
            return 2
            ;;
    esac
    repository=${repository%.git}
    if [[ ! "$repository" =~ ^[^/]+/[^/]+$ ]]; then
        echo "Could not derive owner/repository from origin: $origin" >&2
        return 2
    fi
    printf '%s' "$repository"
}

repository=${CI_REPOSITORY:-$(github_repository_from_origin)}
workflow=${CI_WORKFLOW:-CI}
branch=${CI_BRANCH:-$(git branch --show-current)}
requested_run_id=${CI_RUN_ID:-}

if [[ -z "$branch" ]]; then
    echo "Cannot infer a branch from detached HEAD; pass BRANCH=<branch>." >&2
    exit 2
fi

run_data() {
    if [[ -n "$requested_run_id" ]]; then
        gh run view "$requested_run_id" \
            --repo "$repository" \
            --json databaseId,status,conclusion,url \
            --jq '[.databaseId, .status, (.conclusion // ""), .url] | join("|")'
        return
    fi

    gh run list \
        --repo "$repository" \
        --workflow "$workflow" \
        --branch "$branch" \
        --limit 1 \
        --json databaseId,status,conclusion,url \
        --jq 'if length == 0 then empty else .[0] | [.databaseId, .status, (.conclusion // ""), .url] | join("|") end'
}

load_run() {
    local data
    data=$(run_data)
    if [[ -z "$data" ]]; then
        echo "No $workflow run found for branch $branch." >&2
        exit 1
    fi
    IFS='|' read -r run_id run_status run_conclusion run_url <<<"$data"
}

case "${1:-}" in
    run)
        gh workflow run "$workflow" --repo "$repository" --ref "$branch"
        echo "Triggered $workflow on $branch. Use 'make ci-watch' to follow it."
        ;;
    retry)
        load_run
        case "$run_status" in
            queued|in_progress|requested|waiting|pending)
                echo "Run $run_id is already $run_status; no retry is needed."
                echo "$run_url"
                exit 0
                ;;
        esac

        case "$run_conclusion" in
            failure)
                gh run rerun "$run_id" --repo "$repository" --failed
                ;;
            cancelled|timed_out|startup_failure|stale|action_required)
                gh run rerun "$run_id" --repo "$repository"
                ;;
            success)
                echo "Run $run_id already succeeded; use 'make ci-run' for a fresh run." >&2
                exit 2
                ;;
            *)
                echo "Run $run_id is not retryable (status=$run_status, conclusion=$run_conclusion)." >&2
                exit 2
                ;;
        esac
        echo "Retried run $run_id. Use 'make ci-watch RUN_ID=$run_id' to follow it."
        echo "$run_url"
        ;;
    watch)
        load_run
        echo "$run_url"
        gh run watch "$run_id" --repo "$repository" --compact --exit-status
        ;;
    *)
        echo "Usage: $0 {run|retry|watch}" >&2
        exit 2
        ;;
esac
