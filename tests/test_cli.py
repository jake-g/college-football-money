"""Tests for CLI helpers."""

from __future__ import annotations

import pathlib

from cfbmoney import cli
from cfbmoney import config


def test_prune_removes_only_unreferenced_figures(tmp_path, monkeypatch):
  """Orphaned PNGs are deleted; the current run's figures survive."""
  monkeypatch.setattr(config, 'FIGURES_DIR', tmp_path)
  keep = tmp_path / 'keep.png'
  stale = tmp_path / 'stale.png'
  keep.write_bytes(b'keep')
  stale.write_bytes(b'stale')

  removed = cli._prune_stale_figures([keep])

  assert removed == ['stale.png']
  assert keep.exists()
  assert not stale.exists()


def test_prune_ignores_non_png_files(tmp_path, monkeypatch):
  """Only PNGs are managed; data files in the folder are left alone."""
  monkeypatch.setattr(config, 'FIGURES_DIR', tmp_path)
  notes = tmp_path / 'notes.md'
  notes.write_text('keep me')

  assert cli._prune_stale_figures([]) == []
  assert notes.exists()


def test_prune_handles_a_missing_directory(tmp_path, monkeypatch):
  """A first run with no figures directory must not explode."""
  monkeypatch.setattr(config, 'FIGURES_DIR', tmp_path / 'nope')
  assert cli._prune_stale_figures([]) == []


def test_prune_matches_paths_regardless_of_form(tmp_path, monkeypatch):
  """Relative and absolute references to the same file are one file."""
  monkeypatch.setattr(config, 'FIGURES_DIR', tmp_path)
  figure = tmp_path / 'chart.png'
  figure.write_bytes(b'x')

  removed = cli._prune_stale_figures([pathlib.Path(str(figure))])

  assert removed == []
  assert figure.exists()
