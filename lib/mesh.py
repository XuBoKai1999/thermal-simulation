"""Build or reuse a Gmsh mesh."""

import hashlib
import json
from pathlib import Path


def ensure_mesh(build_dir, geometry_file, build_geometry):
    build_dir = Path(build_dir)
    mesh_path = build_dir / "mesh.msh"
    tags_path = build_dir / "tags.json"
    manifest_path = build_dir / "build.json"
    fingerprint = hashlib.sha256(Path(geometry_file).read_bytes()).hexdigest()

    if mesh_path.exists() and tags_path.exists() and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if manifest.get("geometry_sha256") == fingerprint:
            print("mesh cache valid, reuse existing mesh")
            return mesh_path

    build_dir.mkdir(parents=True, exist_ok=True)
    tags = build_geometry(mesh_path)
    tags_path.write_text(
        json.dumps(tags, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest_path.write_text(
        json.dumps({"geometry_sha256": fingerprint}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"mesh built: {mesh_path}")
    return mesh_path
