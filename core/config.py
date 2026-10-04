"""Typed project configuration."""
from dataclasses import dataclass
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[1]
@dataclass(frozen=True)
class Config:
    raw: dict
    root: Path=ROOT
    @property
    def seed(self): return int(self.raw['seed'])
    @property
    def db_path(self): return self.root/self.raw['paths']['db']
    @property
    def artifacts(self): return self.root/self.raw['paths']['artifacts']
    @property
    def domain(self): return self.raw['domain']
    @property
    def model(self): return self.raw['model']
def load_config(path: Path|None=None)->Config:
    p=path or ROOT/'config.yaml'
    return Config(yaml.safe_load(p.read_text()), p.parent)
