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

```bash
# Dashboard for the authenticated user
gh-stats

# Dashboard for a specific user
gh-stats --user octocat

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

### Example Output

```
┌─── 👤 Profile ──────────────────────────────────────────┐
│  John Doe (@jlaportebot)                                 │
│  Full-stack developer & open-source enthusiast           │
│                                                          │
│  📦 Repos:    42                                         │
│  ⭐ Followers: 150                                        │
│  👥 Following: 30                                        │
│  🔥 Contributions (this year): 847                       │
└──────────────────────────────────────────────────────────┘

┌─── 📊 Contribution Heatmap ─────────────────────────────┐
│       Jan  Feb  Mar  Apr  May  Jun  Jul  Aug  Sep  ...  │
│ Sun  ░░▒▒▓▓██▒▒░░▓▓▒▒██░░▒▒▓▓░░░░▒▒▓▓██▒▒░░▒▒▓▓░░...│
│ Mon  ░░▒▒▓▓██▒▒░░▓▓▒▒██░░▒▒▓▓░░░░▒▒▓▓██▒▒░░▒▒▓▓░░...│
│ ...                                                      │
│                                                          │
│  Less ░▒▓█ More                                          │
└──────────────────────────────────────────────────────────┘

┌─── 📈 Activity Summary ─────────────────────────────────┐
│  ⬆ Pushes: 45  🔀 PRs: 12  ❗ Issues: 8  👁 Reviews: 3  │
└──────────────────────────────────────────────────────────┘
```

## ⌨️ Command Line Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--user` | `-u` | GitHub username | Authenticated user |
| `--year` | `-y` | Year for heatmap | Current year |
| `--limit` | `-l` | Activity entries to show | 20 |
| `--repos` | | Show top repositories | off |
| `--no-heatmap` | | Skip contribution heatmap | off |
| `--no-activity` | | Skip activity timeline | off |
| `--version` | | Show version | — |
| `--help` | | Show help | — |

## 🏗 Architecture

```
gh-stats/
├── gh_stats/
│   ├── __init__.py    # Package metadata
│   ├── cli.py         # Click CLI entry point & orchestration
│   ├── api.py         # GitHub API client (REST + GraphQL)
│   ├── activity.py    # Event parsing & analysis logic
│   └── ui.py          # Rich terminal rendering components
├── tests/
│   ├── test_api.py    # API client tests
│   ├── test_activity.py # Activity analysis tests
│   └── test_ui.py     # UI rendering tests
├── pyproject.toml     # Project config, deps, entry points
├── LICENSE            # MIT license
└── README.md          # This file
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
