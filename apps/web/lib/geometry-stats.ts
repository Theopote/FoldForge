import * as THREE from "three";

export type ModelMeshStats = {
  faces: number;
  vertices: number;
  edges: number;
  widthMm: number;
  heightMm: number;
  depthMm: number;
};

/**
 * Traverse a loaded object and aggregate mesh geometry statistics.
 */
export function computeModelMeshStats(object: THREE.Object3D): ModelMeshStats {
  let faces = 0;
  let vertices = 0;
  const edgeSet = new Set<string>();

  object.updateMatrixWorld(true);

  object.traverse((child) => {
    if (!(child instanceof THREE.Mesh)) return;

    const geometry = child.geometry;
    if (!geometry) return;

    const position = geometry.attributes.position;
    if (!position) return;

    vertices += position.count;

    if (geometry.index) {
      const index = geometry.index.array;
      faces += index.length / 3;

      for (let i = 0; i < index.length; i += 3) {
        const a = index[i];
        const b = index[i + 1];
        const c = index[i + 2];
        edgeSet.add(edgeKey(a, b));
        edgeSet.add(edgeKey(b, c));
        edgeSet.add(edgeKey(c, a));
      }
    } else {
      faces += position.count / 3;
      for (let i = 0; i < position.count; i += 3) {
        const a = i;
        const b = i + 1;
        const c = i + 2;
        edgeSet.add(edgeKey(a, b));
        edgeSet.add(edgeKey(b, c));
        edgeSet.add(edgeKey(c, a));
      }
    }
  });

  const box = new THREE.Box3().setFromObject(object);
  const size = box.getSize(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z);
  const unitScale = maxDim > 0 && maxDim < 10 ? 1000 : 1;

  return {
    faces: Math.round(faces),
    vertices: Math.round(vertices),
    edges: edgeSet.size,
    widthMm: roundMm(size.x * unitScale),
    heightMm: roundMm(size.y * unitScale),
    depthMm: roundMm(size.z * unitScale),
  };
}

function edgeKey(a: number, b: number): string {
  return a < b ? `${a}-${b}` : `${b}-${a}`;
}

function roundMm(value: number): number {
  return Math.round(value * 10) / 10;
}

/**
 * Center and uniformly scale an object to fit a target size in scene units.
 */
export function normalizeModelObject(
  object: THREE.Object3D,
  targetSize = 2,
): THREE.Object3D {
  const box = new THREE.Box3().setFromObject(object);
  const center = box.getCenter(new THREE.Vector3());
  const size = box.getSize(new THREE.Vector3());

  object.position.sub(center);

  const maxDim = Math.max(size.x, size.y, size.z);
  if (maxDim > 0) {
    const scale = targetSize / maxDim;
    object.scale.setScalar(scale);
  }

  return object;
}
