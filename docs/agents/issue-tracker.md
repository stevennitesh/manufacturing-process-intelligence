# Issue tracker: GitHub

Issues and specifications live in GitHub Issues for
https://github.com/stevennitesh/manufacturing-process-intelligence.
Use this guide for tracker-backed work.

## Configuration

**PRs as a request surface:** no.

**Close implemented items:** yes.

**Parent / child mode:** native sub-issues.

**Dependency mode:** native dependencies.

GitHub Issues is enabled. Direct coding does not require an issue, and this
configuration does not start or authorize tracker work by itself.

## Operations

Resolve the exact repository and target type before acting. Prefer an available
GitHub connector; otherwise use the installed CLI or documented API. Check current
operation support and a read-back method before mutation.

Read the issue body, comments, labels, state, assignee, and relevant relationships.
Publish, comment, label, claim, or close only within the authorized task. Close an
implemented item only after the consuming workflow has established completion.

## Representation

- Content lives in issue bodies and comments.
- Category and state use [the label mapping](triage-labels.md).
- Parent, child, and blocking links use the configured native relationships.
- An active claim uses the assignee when the workflow requires claiming.

Preserve relationship representation during an operation. A closed blocker does
not establish readiness if other dependencies remain unresolved.

## Mutation read-back

Refetch the target and affected relationships after a mutation and verify the
fields that changed. After an uncertain result, inspect actual state before retrying
to avoid duplicate issues, comments, or other effects. Report any partial result
and remaining gap.
