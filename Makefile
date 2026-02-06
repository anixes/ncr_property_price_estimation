.PHONY: ingest ingest-test clean help

# Default target
help:
	@echo "MagicBricks Production Scraper - Makefile"
	@echo "=========================================="
	@echo ""
	@echo "Available targets:"
	@echo "  make ingest          - Run full scraper (all cities)"
	@echo "  make ingest-test     - Test scraper (Noida, 10 pages)"
	@echo "  make ingest-gurgaon  - Scrape only Gurgaon"
	@echo "  make clean           - Remove output files"
	@echo ""

# Run full scraper
ingest:
	python ncr_property_price_estimation/data/ingest.py

# Test run (single city, limited pages)
ingest-test:
	python ncr_property_price_estimation/data/ingest.py --city noida --max-pages 10

# Single city targets
ingest-gurgaon:
	python ncr_property_price_estimation/data/ingest.py --city gurgaon

ingest-noida:
	python ncr_property_price_estimation/data/ingest.py --city noida

ingest-delhi:
	python ncr_property_price_estimation/data/ingest.py --city delhi

# Clean output files
clean:
	rm -f data/raw/magicbricks_production.parquet
	rm -f data/raw/checkpoint_production.json
	@echo "Cleaned output files"
