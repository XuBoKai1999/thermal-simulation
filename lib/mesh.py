"""Build or reuse a Gmsh mesh."""

import hashlib
import json
from pathlib import Path
from uuid import uuid4

import gmsh as gmsh_api
import numpy as np
from dolfinx.io import gmsh as gmsh_io
from mpi4py import MPI


def ensure_mesh(build_dir, geometry_file, build_geometry):
    build_dir = Path(build_dir)
    mesh_path = build_dir / "mesh.msh"
    tags_path = build_dir / "tags.json"
    manifest_path = build_dir / "build.json"
    fingerprint = hashlib.sha256(Path(geometry_file).read_bytes()).hexdigest()

    if mesh_path.exists() and tags_path.exists() and manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (
            manifest.get("geometry_sha256") == fingerprint
            and manifest.get("mesh_id")
        ):
            if MPI.COMM_WORLD.rank == 0:
                print("mesh cache valid, reuse existing mesh")
            return mesh_path

    build_dir.mkdir(parents=True, exist_ok=True)
    tags = build_geometry(mesh_path)
    tags_path.write_text(
        json.dumps(tags, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    manifest_path.write_text(
        json.dumps(
            {"geometry_sha256": fingerprint, "mesh_id": uuid4().hex}, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"mesh built: {mesh_path}")
    return mesh_path


def load_mesh(mesh_path):
    return gmsh_io.read_from_msh(str(mesh_path), MPI.COMM_WORLD, rank=0, gdim=3)


def map_cell_ids(mesh_path, domain):
    if domain.comm.size != 1:
        raise NotImplementedError("Dump v1 cell mapping supports serial runs only")

    def signature(points):
        return tuple(sorted(map(tuple, np.round(points, decimals=12))))

    gmsh_api.initialize()
    try:
        gmsh_api.open(str(mesh_path))
        node_tags, coordinates, _ = gmsh_api.model.mesh.getNodes()
        coordinates = coordinates.reshape((-1, 3))
        node_coordinates = dict(zip(map(int, node_tags), coordinates))
        gmsh_cells = {}
        element_types, element_tags, element_nodes = gmsh_api.model.mesh.getElements(3)
        for element_type, tags, nodes in zip(
            element_types, element_tags, element_nodes
        ):
            properties = gmsh_api.model.mesh.getElementProperties(element_type)
            nodes_per_element = properties[3]
            primary_nodes = properties[5]
            nodes = nodes.reshape((-1, nodes_per_element))[:, :primary_nodes]
            for tag, cell_nodes in zip(tags, nodes):
                points = np.array(
                    [node_coordinates[int(node)] for node in cell_nodes]
                )
                gmsh_cells[signature(points)] = (int(tag), points.mean(axis=0))
    finally:
        gmsh_api.finalize()

    geometry_dofmap = domain.geometry.dofmap
    cell_count = domain.topology.index_map(domain.topology.dim).size_local
    cell_ids = np.empty(cell_count, dtype=np.int64)
    mesh_centroids = {}
    for cell in range(cell_count):
        points = domain.geometry.x[geometry_dofmap[cell]]
        match = gmsh_cells.get(signature(points))
        if match is None:
            raise RuntimeError(f"Cannot map FEniCSx cell {cell} to mesh.msh")
        cell_id, centroid = match
        cell_ids[cell] = cell_id
        mesh_centroids[cell_id] = centroid
    if len(set(cell_ids)) != cell_count:
        raise RuntimeError("Mapped cell_ID values are not unique")
    return cell_ids, mesh_centroids
