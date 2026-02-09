# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Cloud browser UI for rclone remotes and folders with lazy-loaded tree view.
- Download dialog with rclone progress, elapsed time, and Finder shortcut.
- Single-instance guard test coverage for activation message path.
- README banner image and rclone prerequisites.

### Changed
- Setup instructions now reference `scripts/setup-initial-dev-environment.sh`.
- README updated with new features and usage notes.

### Fixed
- Single-instance activation now keeps client socket alive and cleans stale server state.
