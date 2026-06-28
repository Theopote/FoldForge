import * as THREE from "three";

import type { SeamEdgeInfo, SeamPosition3d } from "@/lib/seam-manifest";

export type NormalizeTransform = {
  center: THREE.Vector3;
  scale: number;
};

export function transformSeamPoint(
  point: [number, number, number],
  transform: NormalizeTransform,
): THREE.Vector3 {
  return new THREE.Vector3(
    (point[0] - transform.center.x) * transform.scale,
    (point[1] - transform.center.y) * transform.scale,
    (point[2] - transform.center.z) * transform.scale,
  );
}

export function transformSeamSegment(
  position3d: SeamPosition3d,
  transform: NormalizeTransform,
): [THREE.Vector3, THREE.Vector3] {
  return [
    transformSeamPoint(position3d.a, transform),
    transformSeamPoint(position3d.b, transform),
  ];
}

/** Shortest distance from a ray to a line segment in world space. */
export function rayToSegmentDistance(
  ray: THREE.Ray,
  segmentStart: THREE.Vector3,
  segmentEnd: THREE.Vector3,
): number {
  const direction = new THREE.Vector3().subVectors(segmentEnd, segmentStart);
  const lengthSq = direction.lengthSq();
  if (lengthSq < 1e-12) {
    return ray.distanceToPoint(segmentStart);
  }

  const originToStart = new THREE.Vector3().subVectors(segmentStart, ray.origin);
  const rayDotDir = ray.direction.dot(direction);
  const denom = ray.direction.lengthSq() * lengthSq - rayDotDir * rayDotDir;
  if (Math.abs(denom) < 1e-12) {
    return Math.min(
      ray.distanceToPoint(segmentStart),
      ray.distanceToPoint(segmentEnd),
    );
  }

  const tRay =
    (originToStart.dot(direction) * rayDotDir -
      originToStart.dot(ray.direction) * lengthSq) /
    denom;
  const tSeg =
    (originToStart.dot(ray.direction) * rayDotDir +
      originToStart.dot(direction) * ray.direction.lengthSq()) /
    denom;

  const clampedSeg = THREE.MathUtils.clamp(tSeg, 0, 1);
  const clampedRay = Math.max(tRay, 0);
  const pointOnRay = ray.origin
    .clone()
    .addScaledVector(ray.direction, clampedRay);
  const pointOnSeg = segmentStart.clone().addScaledVector(direction, clampedSeg);
  return pointOnRay.distanceTo(pointOnSeg);
}

export function pickClosestSeamEdge(
  ray: THREE.Ray,
  edges: Record<string, SeamEdgeInfo>,
  transform: NormalizeTransform,
  maxDistance: number,
): string | null {
  let bestKey: string | null = null;
  let bestDistance = maxDistance;

  for (const [meshEdge, edge] of Object.entries(edges)) {
    if (!edge.position3d) {
      continue;
    }
    const [start, end] = transformSeamSegment(edge.position3d, transform);
    const distance = rayToSegmentDistance(ray, start, end);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestKey = meshEdge;
    }
  }

  return bestKey;
}

export function buildRayFromPointer(
  camera: THREE.Camera,
  pointer: THREE.Vector2,
): THREE.Ray {
  const raycaster = new THREE.Raycaster();
  raycaster.setFromCamera(pointer, camera);
  return raycaster.ray;
}
