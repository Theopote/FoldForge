"""Procedural low-poly mesh generation from text prompts (offline demo provider)."""

import hashlib
import re

import numpy as np
import trimesh

from app.schemas.model import Style


def generate_procedural_mesh(prompt: str, style: Style) -> trimesh.Trimesh:
    """
    Create a stylized low-poly mesh from prompt keywords.

    Uses keyword heuristics + deterministic variation from prompt hash.
    Replace with real text-to-3D API in production.
    """
    text = prompt.lower()
    seed = int(hashlib.md5(prompt.encode()).hexdigest()[:8], 16)
    rng = np.random.default_rng(seed)

    subdivisions = _subdivisions_for_style(style)
    meshes: list[trimesh.Trimesh] = []

    if _matches(text, ("cat", "fox", "dog", "animal", "pet", "bunny", "rabbit")):
        meshes.append(_animal_mesh(subdivisions, rng))
    elif _matches(text, ("robot", "mech", "android", "droid")):
        meshes.append(_robot_mesh(rng))
    elif _matches(text, ("castle", "tower", "house", "building", "architecture")):
        meshes.append(_building_mesh(rng))
    elif _matches(text, ("car", "vehicle", "truck", "plane", "ship")):
        meshes.append(_vehicle_mesh(text, rng))
    elif _matches(text, ("tree", "plant", "flower")):
        meshes.append(_tree_mesh(subdivisions, rng))
    else:
        meshes.append(_abstract_mesh(subdivisions, rng))

    combined = trimesh.util.concatenate(meshes)
    combined.merge_vertices()
    return combined


def _matches(text: str, keywords: tuple[str, ...]) -> bool:
    return any(re.search(rf"\b{re.escape(word)}\b", text) for word in keywords)


def _subdivisions_for_style(style: Style) -> int:
    if style == Style.LOW_POLY:
        return 1
    if style == Style.CUTE:
        return 2
    return 2


def _animal_mesh(subdivisions: int, rng: np.random.Generator) -> trimesh.Trimesh:
    body = trimesh.creation.icosphere(subdivisions=subdivisions, radius=0.8)
    body.apply_translation([0, 0.3, 0])

    ear_left = trimesh.creation.cone(radius=0.18, height=0.35, sections=4)
    ear_left.apply_transform(trimesh.transformations.rotation_matrix(np.pi * 0.1, [0, 0, 1]))
    ear_left.apply_translation([-0.35, 0.95, 0.15])

    ear_right = ear_left.copy()
    ear_right.apply_transform(trimesh.transformations.reflection_matrix([0, 0, 0], [1, 0, 0]))

    snout = trimesh.creation.icosphere(subdivisions=1, radius=0.22)
    snout.apply_translation([0, 0.15, 0.65])

    tail = trimesh.creation.capsule(radius=0.08, height=0.45, count=[8, 8])
    tail.apply_transform(trimesh.transformations.rotation_matrix(-np.pi / 3, [1, 0, 0]))
    tail.apply_translation([0, 0.45, -0.65 - rng.uniform(0, 0.1)])

    return trimesh.util.concatenate([body, ear_left, ear_right, snout, tail])


def _robot_mesh(rng: np.random.Generator) -> trimesh.Trimesh:
    body = trimesh.creation.box(extents=[0.9, 1.1, 0.55])
    body.apply_translation([0, 0.55, 0])

    head = trimesh.creation.box(extents=[0.55, 0.45, 0.45])
    head.apply_translation([0, 1.25, 0])

    parts = [body, head]
    for side in (-1, 1):
        arm = trimesh.creation.box(extents=[0.22, 0.75, 0.22])
        arm.apply_translation([side * 0.65, 0.65, 0])
        leg = trimesh.creation.box(extents=[0.25, 0.55, 0.25])
        leg.apply_translation([side * 0.28, 0.05, 0])
        parts.extend([arm, leg])

    antenna = trimesh.creation.cylinder(radius=0.04, height=0.25, sections=6)
    antenna.apply_translation([0, 1.55 + rng.uniform(0, 0.05), 0])
    parts.append(antenna)

    return trimesh.util.concatenate(parts)


def _building_mesh(rng: np.random.Generator) -> trimesh.Trimesh:
    base = trimesh.creation.box(extents=[1.2, 0.35, 1.0])
    tower = trimesh.creation.box(extents=[0.55, 1.0 + rng.uniform(0, 0.2), 0.55])
    tower.apply_translation([0, 0.675, 0])
    roof = trimesh.creation.cone(radius=0.42, height=0.35, sections=4)
    roof.apply_translation([0, 1.35, 0])
    return trimesh.util.concatenate([base, tower, roof])


def _vehicle_mesh(text: str, rng: np.random.Generator) -> trimesh.Trimesh:
    if "plane" in text or "ship" in text:
        body = trimesh.creation.capsule(radius=0.25, height=1.4, count=[8, 8])
        body.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [0, 0, 1]))
        wing = trimesh.creation.box(extents=[1.6, 0.06, 0.35])
        wing.apply_translation([0, 0.15, 0])
        return trimesh.util.concatenate([body, wing])

    body = trimesh.creation.box(extents=[1.3, 0.4, 0.65])
    body.apply_translation([0, 0.35, 0])
    cabin = trimesh.creation.box(extents=[0.55, 0.28, 0.55])
    cabin.apply_translation([-0.15, 0.62, 0])
    wheels = []
    for x, z in [(-0.4, 0.35), (0.4, 0.35), (-0.4, -0.35), (0.4, -0.35)]:
        wheel = trimesh.creation.cylinder(radius=0.16, height=0.12, sections=8)
        wheel.apply_transform(trimesh.transformations.rotation_matrix(np.pi / 2, [1, 0, 0]))
        wheel.apply_translation([x, 0.16, z])
        wheels.append(wheel)
    return trimesh.util.concatenate([body, cabin, *wheels])


def _tree_mesh(subdivisions: int, rng: np.random.Generator) -> trimesh.Trimesh:
    trunk = trimesh.creation.cylinder(radius=0.12, height=0.55, sections=6)
    trunk.apply_translation([0, 0.27, 0])
    crown = trimesh.creation.icosphere(subdivisions=subdivisions, radius=0.55 + rng.uniform(0, 0.1))
    crown.apply_translation([0, 0.85, 0])
    return trimesh.util.concatenate([trunk, crown])


def _abstract_mesh(subdivisions: int, rng: np.random.Generator) -> trimesh.Trimesh:
    """Fallback abstract sculpture from prompt hash."""
    base = trimesh.creation.icosphere(subdivisions=subdivisions, radius=0.75)
    spike_count = 2 + int(rng.integers(0, 3))
    parts = [base]
    for i in range(spike_count):
        spike = trimesh.creation.cone(radius=0.15, height=0.5 + rng.uniform(0, 0.3), sections=4)
        angle = (2 * np.pi * i) / spike_count + rng.uniform(-0.2, 0.2)
        spike.apply_transform(trimesh.transformations.rotation_matrix(angle, [0, 1, 0]))
        spike.apply_translation([
            float(rng.uniform(-0.3, 0.3)),
            0.55,
            float(rng.uniform(-0.3, 0.3)),
        ])
        parts.append(spike)
    return trimesh.util.concatenate(parts)
