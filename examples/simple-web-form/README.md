# Simple Web Form Example

A 7-state graph modeling a typical web application with login, dashboard, settings, and profile editing.

## States

| State | Description | Anchors |
|-------|-------------|---------|
| landing_page | Home page with login button | "Welcome to Our App", #hero-banner |
| login_form | Email/password form | "Sign In", input[name='email'] |
| dashboard | Authenticated main page | "Dashboard", #dashboard-nav |
| settings | Account settings form | "Account Settings", #settings-form |
| profile_edit | Profile editor | "Edit Profile", #profile-avatar-upload |
| confirmation | Toast confirmation (wait state) | "Changes Saved" |
| error_page | Error fallback | "Something went wrong" |

## Transitions

11 transitions total: 7 deterministic (clicks, navigation), 4 vision-required (form submissions).

## Usage

```bash
# Validate the graph
python scripts/schema_validator.py examples/simple-web-form/graph.json

# Get graph summary
python scripts/graph_utils.py --graph examples/simple-web-form/graph.json summary

# Find path from login to settings
python scripts/pathfind.py --graph examples/simple-web-form/graph.json --from login_form --to settings

# Find path preferring deterministic transitions
python scripts/pathfind.py --graph examples/simple-web-form/graph.json --from landing_page --to profile_edit --prefer deterministic
```
