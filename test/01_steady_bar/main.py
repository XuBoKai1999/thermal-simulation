from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

import dolfinx
import gmsh
from lib import mesh

import geometry


mesh.ensure_mesh(
    Path(__file__).resolve().parent / "build",
    geometry.__file__,
    geometry.build_geometry,
)
