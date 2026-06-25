# 📊 gh-stats

> A beautiful terminal dashboard for your GitHub activity — contribution heatmaps, activity timelines, and repo stats at a glance.

![Python](https://img.shields.io/badge/Python-3.9%2B-blue)
![License](https://img.shields.io/badge/License-MIT-green)
![Version](https://img.shields.io/badge/Version-0.1.0-orange)

## ✨ Features

- **📊 Contribution Heatmap** — GitHub-style contribution graph rendered right in your terminal with Unicode blocks and color gradients
- **🕐 Activity Timeline** — See your recent pushes, PRs, issues, reviews, releases, and more in a clean table
- **🔤 Language Chart** — Horizontal bar chart of your language distribution across repositories
- **🏆 Top Repositories** — Table of your most-starred repos with descriptions
- **📈 Activity Summary** — Quick count of activities by type
- **👤 Profile Card** — At-a-glance profile with follower count and yearly contributions
- **🔍 Side-by-Side Comparison** — Compare two users or two organizations
- **⏰ Time-Period Comparison** — Compare the same user/org across different years
- **👥 Team Analytics** — Organization-wide analytics: contributor rankings, bus factor, repo health, collaboration network, code review metrics, activity trends
- **📤 Export** — JSON and HTML export for both single targets and comparisons/team analytics

## 🚀 Installation

```bash
# Install from PyPI (once published)
pip install gh-stats

# Or install from source
git clone https://github.com/jlaportebot/gh-stats.git
cd gh-stats
pip install -e .
```

### Prerequisites

- Python 3.9+
- GitHub authentication via one of:
  - [GitHub CLI (`gh`)](https://cli.github.com/) — install and run `gh auth login`
  - `GH_TOKEN` or `GITHUB_TOKEN` environment variable

## 📖 Usage

### Single User/Org Dashboard

```bash
# Dashboard for the authenticated user
gh-stats

# Dashboard for a specific user
gh-stats --user octocat

# Dashboard for an organization
gh-stats --org github

# Contribution heatmap for a specific year
gh-stats --year 2025

# Show top repositories table
gh-stats --repos

# Limit activity timeline entries
gh-stats --limit 10

# Skip specific sections
gh-stats --no-heatmap
gh-stats --no-activity
```

### Compare Two Users/Orgs

```bash
# Compare two users
gh-stats compare --user-a octocat --user-b torvalds

# Compare two organizations
gh-stats compare --org-a github --org-b microsoft

# Compare same user across years (time-period comparison)
gh-stats compare --user-a octocat --year-a 2023 --year-b 2024

# Compare same org across years
gh-stats compare --org-a github --year-a 2023 --year-b 2024
```

### Team/Organization Analytics

```bash
# Team analytics for an organization
gh-stats team --org github

# Limit repositories analyzed
gh-stats team --org github --repo-limit 50

# Limit contributors shown
gh-stats team --org github --contributors 30

# Skip specific sections
gh-stats team --org github --no-health --no-bus-factor --no-collab --no-reviews

# Analyze specific year
gh-stats team --org github --year 2024
```

### Export

```bash
# Export single dashboard as JSON
gh-stats --output dashboard.json

# Export single dashboard as HTML
gh-stats --output dashboard.html --format html

# Export comparison as JSON
gh-stats compare --user-a octocat --user-b torvalds --output compare.json

# Export comparison as HTML
gh-stats compare --user-a octocat --user-b torvalds --output compare.html --format html

# Export team analytics as JSON
gh-stats team --org github --output team.json

# Export team analytics as HTML
gh-stats team --org github --output team.html --format html
```

## ⌨️ Command Line Options

### `gh-stats` (single target)

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--user` | `-u` | GitHub username | Authenticated user |
| `--org` | `-o` | GitHub organization name | — |
| `--year` | `-y` | Year for heatmap | Current year |
| `--limit` | `-l` | Activity entries to show | 20 |
| `--repos` | | Show top repositories | off |
| `--no-heatmap` | | Skip contribution heatmap | off |
| `--no-activity` | | Skip activity timeline | off |
| `--no-streaks` | | Skip contribution streaks | off |
| `--output` | | Export to file | — |
| `--format` | | Export format (json/html) | json |

### `gh-stats compare` (two targets)

| Option | Description | Default |
|--------|-------------|---------|
| `--user-a` / `--user-b` | Two users to compare | — |
| `--org-a` / `--org-b` | Two organizations to compare | — |
| `--year-a` / `--year-b` | Years for time-period comparison | Current year |
| `--limit` | Activity entries to show | 20 |
| `--repos` | Show top repositories table | off |
| `--no-heatmap` | Skip heatmap | off |
| `--no-activity` | Skip activity timeline | off |
| `--no-streaks` | Skip streaks | off |
| `--output` | Export to file | — |
| `--format` | Export format (json/html) | json |

### `gh-stats team` (organization analytics)

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--org` | `-o` | GitHub organization name | Required |
| `--year` | `-y` | Year for analysis | Current year |
| `--repo-limit` | | Repositories to analyze | 20 |
| `--contributors` | | Top contributors to show | 20 |
| `--no-health` | | Skip repository health matrix | off |
| `--no-bus-factor` | | Skip bus factor analysis | off |
| `--no-collab` | | Skip collaboration network | off |
| `--no-reviews` | | Skip code review analytics | off |
| `--output` | | Export to file | — |
| `--format` | | Export format (json/html) | json |

## 🏗 Architecture

```
gh-stats/
├── gh_stats/
│   ├── __init__.py         # Package metadata
│   ├── cli.py              # Click CLI entry point & orchestration
│   ├── api.py              # GitHub API client (REST + GraphQL)
│   ├── activity.py         # Event parsing & analysis logic
│   ├── ui.py               # Rich terminal rendering components
│   ├── team.py             # Team analytics (contributors, bus factor, health, collaboration, reviews)
│   ├── team_trends.py      # Team activity trend computation
│   ├── team_ui.py          # Team dashboard rendering
│   ├── team_trends_ui.py   # Team trends rendering
│   ├── html_export.py      # HTML report generation
│   └── comparison.py       # Side-by-side & time-period comparison logic
├── tests/
│   ├── test_api.py         # API client tests
│   ├── test_activity.py    # Activity analysis tests
│   ├── test_ui.py          # UI rendering tests
│   ├── test_cli.py         # CLI tests
│   ├── test_comparison.py  # Comparison tests
│   ├── test_team.py        # Team analytics tests
│   └── test_html_export.py # HTML export tests
├── pyproject.toml          # Project config, deps, entry points
├── LICENSE                 # MIT license
└── README.md               # This file
```

## 🛠 Development

```bash
# Clone and set up
git clone https://github.com/jlaportebot/gh-stats.git
cd gh-stats

# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check .

# Format code
ruff format .
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'feat: add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Commit Convention

This project follows [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` — New features
- `fix:` — Bug fixes
- `docs:` — Documentation changes
- `refactor:` — Code refactoring
- `test:` — Test additions/changes
- `chore:` — Build/maintenance changes

## 📝 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [Rich](https://github.com/Textualize/rich) — Beautiful terminal formatting
- [Click](https://github.com/pallets/click) — Command-line interface creation
- [httpx](https://github.com/encode/httpx) — Modern HTTP client for Python
- [GitHub CLI](https://cli.github.com/) — Seamless auth integration

---

**gh-stats** — Built with 🦞 by Mister Lobster