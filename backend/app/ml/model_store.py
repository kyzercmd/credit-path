"""
Model Store (B12).

Handles saving and loading of trained models and metadata.
Models are saved to disk with joblib, and their training metadata
(version, training timestamp, cutoff date, performance metrics) are saved as JSON.
Loaded at startup to ensure fast request-time evaluation.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import joblib

DEFAULT_MODEL_DIR = Path(__file__).resolve().parent.parent.parent / "trained_models"
DEFAULT_DATA_AS_OF = "2025-12-31"


class ModelStore:
    """Model storage manager for persisting and loading trained estimators and metadata."""

    def __init__(self, model_dir: Path | str | None = None) -> None:
        self.model_dir = Path(model_dir) if model_dir is not None else DEFAULT_MODEL_DIR
        self.model_dir.mkdir(parents=True, exist_ok=True)

    def save(
        self,
        model: Any,
        name: str,
        metadata: dict[str, Any] | None = None,
    ) -> Path:
        """
        Save model to joblib file and write metadata to <name>_meta.json.

        Parameters
        ----------
        model : Any
            Trained estimator or model object.
        name : str
            Base identifier name (e.g. 'forecaster', 'risk_model').
        metadata : dict[str, Any] | None
            Dictionary containing model version, metrics, training date, etc.

        Returns
        -------
        Path
            Path to the saved model file.
        """
        self.model_dir.mkdir(parents=True, exist_ok=True)
        model_path = self.model_dir / f"{name}.joblib"
        meta_path = self.model_dir / f"{name}_meta.json"

        # Ensure default metadata fields
        meta = {
            "name": name,
            "version": "v1.0.0",
            "data_as_of": DEFAULT_DATA_AS_OF,
        }
        if metadata:
            meta.update(metadata)

        joblib.dump(model, model_path)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2, default=str)

        return model_path

    def load(self, name: str) -> tuple[Any, dict[str, Any]]:
        """
        Load model and its metadata JSON.

        Parameters
        ----------
        name : str
            Base identifier name (e.g. 'forecaster', 'risk_model').

        Returns
        -------
        tuple[Any, dict[str, Any]]
            Tuple of (loaded_model, metadata_dict).
        """
        model_path = self.model_dir / f"{name}.joblib"
        meta_path = self.model_dir / f"{name}_meta.json"

        if not model_path.exists():
            raise FileNotFoundError(f"Model file not found at {model_path}")

        model = joblib.load(model_path)
        metadata: dict[str, Any] = {}
        if meta_path.exists():
            with open(meta_path, "r", encoding="utf-8") as f:
                metadata = json.load(f)

        return model, metadata

    def get_version(self, name: str = "forecaster") -> str:
        """Return model version string, default 'v1.0.0'."""
        meta_path = self.model_dir / f"{name}_meta.json"
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    return str(meta.get("version", "v1.0.0"))
            except Exception:
                return "v1.0.0"
        return "v1.0.0"

    def get_data_as_of(self, name: str = "forecaster") -> str:
        """Return data cutoff timestamp/date string, default '2025-12-31'."""
        meta_path = self.model_dir / f"{name}_meta.json"
        if meta_path.exists():
            try:
                with open(meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
                    return str(meta.get("data_as_of", DEFAULT_DATA_AS_OF))
            except Exception:
                return DEFAULT_DATA_AS_OF
        return DEFAULT_DATA_AS_OF


_default_store = ModelStore()


def save_model(
    model: Any,
    name: str,
    metadata: dict[str, Any] | None = None,
    model_dir: Path | str | None = None,
) -> Path:
    """Save model and metadata using either specified model_dir or default store."""
    store = ModelStore(model_dir=model_dir) if model_dir is not None else _default_store
    return store.save(model, name, metadata)


def load_model(
    name: str,
    model_dir: Path | str | None = None,
) -> tuple[Any, dict[str, Any]]:
    """Load model and metadata from specified model_dir or default store."""
    store = ModelStore(model_dir=model_dir) if model_dir is not None else _default_store
    return store.load(name)


def get_model_version(
    name: str = "forecaster",
    model_dir: Path | str | None = None,
) -> str:
    """Get model version from metadata."""
    store = ModelStore(model_dir=model_dir) if model_dir is not None else _default_store
    return store.get_version(name)


def get_data_as_of(
    model_dir: Path | str | None = None,
) -> str:
    """Get data cutoff date from metadata."""
    store = ModelStore(model_dir=model_dir) if model_dir is not None else _default_store
    return store.get_data_as_of()
