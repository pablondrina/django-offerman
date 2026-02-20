# Changelog

All notable changes to this project will be documented in this file.

## [0.3.1] - 2026-02-20

### Fixed
- `ProductAdmin` fieldset referenced non-existent `description` field; corrected to `short_description` and `long_description`.

## [0.3.0] - 2025-01-20

### Added
- Product model with visibility control (is_hidden, is_unavailable)
- Collection model with hierarchical categories
- Listing model for channel-specific pricing
- ProductComponent model for bundles/kits
- CatalogService facade
- Tagging support via django-taggit
- Admin interface with optional Unfold support
- SKU validation adapter for Stockman integration
- Product suggestion contrib module
