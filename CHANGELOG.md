# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-03-25

### Added
- New `dirty_repos` MCP tool — scans all repos for uncommitted changes, sorted by urgency score (file count + recency of dirty files). No time window — only shrinks by committing.
- boot_up now scans all project directories for dirty git state in parallel
- Dirty repos bypass session age filters — uncommitted work doesn't age out
- Repo dirty urgency score flows into boot_up session scoring
- Ready-to-paste `resume_cmd` in every boot_up session row
- Last user message extraction for sessions with no cached summary
- Noise filtering — suppresses blank home directory sessions
- Negative space scan report (repos scanned/dirty/clean)

### Changed
- Replaced RRF scoring with BM25 summary-first search
- Renamed package from claude_resume to resume_resume
- Origin-aware session summaries

## [0.1.9] - 2026-03-22

### Fixed
- Replaced `claude -p` window summaries with no-LLM adapter (faster, no API dependency)

## [0.1.8] - 2026-03-22

### Fixed
- Fixed image URLs to absolute raw GitHub paths for PyPI rendering
- Re-processed screenshots without quantize (was destroying text quality)

### Changed
- Renamed 'Claude Resume' to 'resume-resume' across all references
- Replaced example screenshots with new Gemini images (watermark-free)
- Compressed logo: 7MB PNG to 333KB
- Removed mcp-self-report dependency, switched to PyPI-ready deps
- Added LICENSE file

## [0.1.0] - 2026-03-20

### Added
- Initial release
- Post-crash Claude Code session recovery TUI
- Session discovery, caching, and classification
- MCP server for agent-driven session recovery
