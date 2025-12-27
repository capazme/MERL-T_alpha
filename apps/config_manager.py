"""
Configuration Manager for Expert Debugger
==========================================

Gestisce caricamento, modifica e snapshot delle configurazioni YAML.
Permette version tracking delle configurazioni con ogni run.
"""

import yaml
import json
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field, asdict
from copy import deepcopy


# Configurazioni YAML rilevanti per l'expert system
CONFIG_FILES = {
    "retriever": "merlt/config/retriever_weights.yaml",
    "experts": "merlt/experts/config/experts.yaml",
    "weights": "merlt/weights/config/weights.yaml",
}


@dataclass
class ConfigSnapshot:
    """Snapshot di tutte le configurazioni al momento della run."""
    timestamp: str
    config_hash: str
    trace_id: str
    configs: Dict[str, Any] = field(default_factory=dict)
    overrides: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConfigSnapshot":
        return cls(**data)


class ConfigManager:
    """
    Gestisce le configurazioni YAML per l'expert system.

    Features:
    - Carica configurazioni da file YAML
    - Permette override runtime
    - Crea snapshot per ogni run
    - Calcola hash per version tracking
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path(__file__).parent.parent
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._runtime_overrides: Dict[str, Dict[str, Any]] = {}
        self._load_all_configs()

    def _load_all_configs(self):
        """Carica tutte le configurazioni YAML."""
        for name, rel_path in CONFIG_FILES.items():
            full_path = self.project_root / rel_path
            if full_path.exists():
                with open(full_path, 'r') as f:
                    self._configs[name] = yaml.safe_load(f)
            else:
                self._configs[name] = {}

    def reload(self):
        """Ricarica tutte le configurazioni da file."""
        self._load_all_configs()

    def get_config(self, name: str) -> Dict[str, Any]:
        """
        Ottiene configurazione con eventuali override runtime.

        Args:
            name: Nome configurazione (retriever, experts, weights)

        Returns:
            Configurazione merged con override
        """
        base = deepcopy(self._configs.get(name, {}))
        overrides = self._runtime_overrides.get(name, {})
        return self._deep_merge(base, overrides)

    def set_override(self, config_name: str, key_path: str, value: Any):
        """
        Imposta override runtime per una configurazione.

        Args:
            config_name: Nome config (retriever, experts, weights)
            key_path: Percorso chiave (es. "retrieval.alpha")
            value: Nuovo valore
        """
        if config_name not in self._runtime_overrides:
            self._runtime_overrides[config_name] = {}

        # Naviga nel path e imposta il valore
        keys = key_path.split(".")
        current = self._runtime_overrides[config_name]
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[keys[-1]] = value

    def clear_overrides(self):
        """Rimuove tutti gli override runtime."""
        self._runtime_overrides = {}

    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """Ottiene tutte le configurazioni merged."""
        return {
            name: self.get_config(name)
            for name in CONFIG_FILES.keys()
        }

    def compute_hash(self) -> str:
        """Calcola hash di tutte le configurazioni (per version tracking)."""
        all_configs = self.get_all_configs()
        config_str = json.dumps(all_configs, sort_keys=True, default=str)
        return hashlib.sha256(config_str.encode()).hexdigest()[:12]

    def create_snapshot(self, trace_id: str) -> ConfigSnapshot:
        """
        Crea snapshot delle configurazioni per una run.

        Args:
            trace_id: ID del trace associato

        Returns:
            ConfigSnapshot con tutte le configurazioni
        """
        return ConfigSnapshot(
            timestamp=datetime.now().isoformat(),
            config_hash=self.compute_hash(),
            trace_id=trace_id,
            configs=self.get_all_configs(),
            overrides=deepcopy(self._runtime_overrides)
        )

    def save_snapshot(self, snapshot: ConfigSnapshot, output_dir: Path) -> Path:
        """
        Salva snapshot su file.

        Args:
            snapshot: Snapshot da salvare
            output_dir: Directory di output

        Returns:
            Path del file salvato
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        filename = f"config_{snapshot.config_hash}_{snapshot.timestamp[:19].replace(':', '-')}.json"
        output_path = output_dir / filename

        with open(output_path, 'w') as f:
            json.dump(snapshot.to_dict(), f, indent=2, default=str)

        return output_path

    def load_snapshot(self, snapshot_path: Path) -> ConfigSnapshot:
        """Carica snapshot da file."""
        with open(snapshot_path, 'r') as f:
            data = json.load(f)
        return ConfigSnapshot.from_dict(data)

    def apply_snapshot(self, snapshot: ConfigSnapshot):
        """Applica override da snapshot."""
        self._runtime_overrides = deepcopy(snapshot.overrides)

    def list_snapshots(self, output_dir: Path) -> List[Path]:
        """Lista tutti gli snapshot salvati."""
        if not output_dir.exists():
            return []
        return sorted(output_dir.glob("config_*.json"), reverse=True)

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Merge profondo di due dizionari."""
        result = deepcopy(base)
        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = deepcopy(value)
        return result

    # === Metodi helper per parametri specifici ===

    def get_retrieval_alpha(self) -> float:
        """Ottiene alpha per hybrid retrieval."""
        config = self.get_config("weights")
        return config.get("retrieval", {}).get("alpha", {}).get("default", 0.7)

    def get_expert_model(self, expert_type: str) -> str:
        """Ottiene modello per expert."""
        config = self.get_config("experts")
        expert_key = expert_type.lower().replace("expert", "")
        return config.get("experts", {}).get(expert_key, {}).get("model", "google/gemini-2.5-flash")

    def get_expert_temperature(self, expert_type: str) -> float:
        """Ottiene temperature per expert."""
        config = self.get_config("experts")
        expert_key = expert_type.lower().replace("expert", "")
        return config.get("experts", {}).get(expert_key, {}).get("temperature", 0.3)

    def get_traversal_weights(self, expert_type: str) -> Dict[str, float]:
        """Ottiene traversal weights per expert."""
        config = self.get_config("weights")
        expert_weights = config.get("expert_traversal", {}).get(expert_type, {})
        # Estrai solo i valori default
        return {
            k: v.get("default", 0.5) if isinstance(v, dict) else v
            for k, v in expert_weights.items()
        }

    def get_gating_weights(self) -> Dict[str, float]:
        """Ottiene gating weights per expert routing."""
        config = self.get_config("weights")
        priors = config.get("gating", {}).get("expert_priors", {})
        return {
            k: v.get("default", 0.25) if isinstance(v, dict) else v
            for k, v in priors.items()
        }


# === UI Helper Functions ===

def render_config_sidebar(config_manager: ConfigManager, st) -> Dict[str, Any]:
    """
    Render sidebar per editing configurazioni in Streamlit.

    Args:
        config_manager: ConfigManager instance
        st: Streamlit module

    Returns:
        Dict con le modifiche applicate
    """
    st.sidebar.markdown("---")
    st.sidebar.subheader("Configuration")

    changes = {}

    # Retrieval Settings
    with st.sidebar.expander("Retrieval Settings", expanded=False):
        alpha = st.slider(
            "Alpha (semantic vs graph)",
            min_value=0.3,
            max_value=0.9,
            value=config_manager.get_retrieval_alpha(),
            step=0.05,
            help="0.7 = 70% semantic, 30% graph"
        )
        if alpha != config_manager.get_retrieval_alpha():
            config_manager.set_override("weights", "retrieval.alpha.default", alpha)
            changes["retrieval.alpha"] = alpha

        weights_config = config_manager.get_config("weights")
        max_hops = st.slider(
            "Max Graph Hops",
            min_value=1,
            max_value=5,
            value=weights_config.get("retrieval", {}).get("max_graph_hops", 3),
            help="Maximum path length in graph"
        )

    # Expert Settings
    with st.sidebar.expander("Expert Settings", expanded=False):
        experts_config = config_manager.get_config("experts")
        defaults = experts_config.get("defaults", {})

        model = st.selectbox(
            "LLM Model",
            options=[
                "google/gemini-2.5-flash",
                "google/gemini-2.5-pro",
                "anthropic/claude-3.5-sonnet",
                "openai/gpt-4o"
            ],
            index=0,
            help="Model for all experts"
        )

        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=1.0,
            value=defaults.get("temperature", 0.3),
            step=0.1,
            help="Lower = more deterministic"
        )

    # Gating Weights
    with st.sidebar.expander("Expert Gating Weights", expanded=False):
        gating = config_manager.get_gating_weights()

        col1, col2 = st.columns(2)
        with col1:
            literal_w = st.slider("Literal", 0.0, 1.0, gating.get("LiteralExpert", 0.25), 0.05)
            systemic_w = st.slider("Systemic", 0.0, 1.0, gating.get("SystemicExpert", 0.25), 0.05)
        with col2:
            principles_w = st.slider("Principles", 0.0, 1.0, gating.get("PrinciplesExpert", 0.25), 0.05)
            precedent_w = st.slider("Precedent", 0.0, 1.0, gating.get("PrecedentExpert", 0.25), 0.05)

        total = literal_w + systemic_w + principles_w + precedent_w
        if abs(total - 1.0) > 0.01:
            st.warning(f"Weights sum to {total:.2f}, should be 1.0")

    # Config Hash
    config_hash = config_manager.compute_hash()
    st.sidebar.caption(f"Config hash: `{config_hash}`")

    return changes


def render_config_viewer(config_manager: ConfigManager, st):
    """
    Render tab per visualizzare configurazioni complete.

    Args:
        config_manager: ConfigManager instance
        st: Streamlit module
    """
    st.subheader("Current Configuration")

    tabs = st.tabs(["Retriever", "Experts", "Weights", "Raw YAML"])

    with tabs[0]:
        st.json(config_manager.get_config("retriever"))

    with tabs[1]:
        st.json(config_manager.get_config("experts"))

    with tabs[2]:
        st.json(config_manager.get_config("weights"))

    with tabs[3]:
        for name, rel_path in CONFIG_FILES.items():
            with st.expander(f"{name} ({rel_path})"):
                full_path = config_manager.project_root / rel_path
                if full_path.exists():
                    st.code(full_path.read_text(), language="yaml")
                else:
                    st.warning(f"File not found: {rel_path}")
