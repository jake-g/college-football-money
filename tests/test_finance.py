"""Tests for joining federal finance filings onto ESPN teams."""

from __future__ import annotations

import pytest

from cfbmoney import finance
from cfbmoney import names


def test_report_year_falls_back_when_filing_not_published(monkeypatch):
  """An unpublished year degrades to the newest filing instead of failing."""
  monkeypatch.setattr(finance, 'available_eada_years', lambda: [2025, 2024])
  # 2026 would want report year 2027, which does not exist yet.
  assert finance.resolve_report_year(2026) == 2025


def test_report_year_uses_the_exact_filing_when_available(monkeypatch):
  """No fallback happens when the wanted year is on disk."""
  monkeypatch.setattr(finance, 'available_eada_years', lambda: [2025, 2024])
  assert finance.resolve_report_year(2023) == 2024


def test_explicit_report_year_must_exist(monkeypatch):
  """An override for a missing year is an error, not a silent fallback."""
  monkeypatch.setattr(finance, 'available_eada_years', lambda: [2025])
  with pytest.raises(FileNotFoundError):
    finance.resolve_report_year(2026, prefer=2019)


def test_missing_eada_download_raises(monkeypatch):
  """A helpful error is raised before anything else is attempted."""
  monkeypatch.setattr(finance, 'available_eada_years', lambda: [])
  with pytest.raises(FileNotFoundError, match='No EADA files'):
    finance.resolve_report_year(2026)


def test_money_columns_cover_both_directions_of_cash_flow():
  """The schema must carry money in and money out, not just revenue."""
  assert 'football_revenue' in finance.MONEY_COLUMNS
  assert 'football_expenses' in finance.MONEY_COLUMNS
  assert 'dept_total_revenue' in finance.MONEY_COLUMNS


def test_service_academies_are_known_to_be_exempt():
  """Air Force, Army and Navy legitimately have no federal filing."""
  assert set(names.EADA_EXEMPT) == {'Air Force', 'Army', 'Navy'}
  # Each carries a human-readable reason for the report.
  assert all(reason for reason in names.EADA_EXEMPT.values())
