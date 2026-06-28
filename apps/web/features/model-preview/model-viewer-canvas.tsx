"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { Center, Line, OrbitControls } from "@react-three/drei";
import { Canvas } from "@react-three/fiber";
import * as THREE from "three";

import {
  computeModelMeshStats,
  normalizeModelObject,
  type ModelMeshStats,
} from "@/lib/geometry-stats";
import type { SeamPosition3d } from "@/lib/seam-manifest";
import { loadModelFromUrl } from "@/lib/model-loader";

type NormalizeTransform = {
  center: THREE.Vector3;
  scale: number;
};

type SceneModelProps = {
  url: string;
  onLoaded: (stats: ModelMeshStats) => void;
  onError: (message: string) => void;
  onTransformReady: (transform: NormalizeTransform) => void;
};

function SceneModel({ url, onLoaded, onError, onTransformReady }: SceneModelProps) {
  const [object, setObject] = useState<THREE.Object3D | null>(null);
  const onLoadedRef = useRef(onLoaded);
  const onErrorRef = useRef(onError);
  const onTransformReadyRef = useRef(onTransformReady);

  onLoadedRef.current = onLoaded;
  onErrorRef.current = onError;
  onTransformReadyRef.current = onTransformReady;

  useEffect(() => {
    let cancelled = false;
    setObject(null);

    loadModelFromUrl(url)
      .then((loaded) => {
        if (cancelled) return;

        loaded.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            child.castShadow = true;
            child.receiveShadow = true;
            if (!child.material) {
              child.material = new THREE.MeshStandardMaterial({
                color: "#e85d4c",
                metalness: 0.1,
                roughness: 0.65,
              });
            }
          }
        });

        const box = new THREE.Box3().setFromObject(loaded);
        const center = box.getCenter(new THREE.Vector3());
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale = maxDim > 0 ? 2 / maxDim : 1;

        normalizeModelObject(loaded);
        onTransformReadyRef.current({ center, scale });

        const stats = computeModelMeshStats(loaded);
        setObject(loaded);
        onLoadedRef.current(stats);
      })
      .catch((error) => {
        if (!cancelled) {
          onErrorRef.current(
            error instanceof Error ? error.message : "Failed to load model.",
          );
        }
      });

    return () => {
      cancelled = true;
    };
  }, [url]);

  if (!object) return null;

  return (
    <Center>
      <primitive object={object} />
    </Center>
  );
}

function SeamEdgeHighlight({
  position3d,
  transform,
}: {
  position3d: SeamPosition3d;
  transform: NormalizeTransform;
}) {
  const points = [position3d.a, position3d.b].map(
    ([x, y, z]) =>
      [
        (x - transform.center.x) * transform.scale,
        (y - transform.center.y) * transform.scale,
        (z - transform.center.z) * transform.scale,
      ] as [number, number, number],
  );

  return <Line points={points} color="#e85d4c" lineWidth={3} />;
}

type ModelViewerCanvasProps = {
  url: string;
  onLoaded: (stats: ModelMeshStats) => void;
  onError: (message: string) => void;
  seamHighlight?: SeamPosition3d | null;
};

export function ModelViewerCanvas({
  url,
  onLoaded,
  onError,
  seamHighlight = null,
}: ModelViewerCanvasProps) {
  const [transform, setTransform] = useState<NormalizeTransform | null>(null);

  useEffect(() => {
    setTransform(null);
  }, [url]);

  return (
    <Canvas
      shadows
      camera={{ position: [2.5, 2, 2.5], fov: 45, near: 0.01, far: 100 }}
      className="h-full w-full"
    >
      <color attach="background" args={["#f8fafc"]} />
      <ambientLight intensity={0.55} />
      <directionalLight
        position={[4, 6, 3]}
        intensity={1.1}
        castShadow
        shadow-mapSize-width={1024}
        shadow-mapSize-height={1024}
      />
      <directionalLight position={[-3, 2, -2]} intensity={0.35} />
      <Suspense fallback={null}>
        <SceneModel
          url={url}
          onLoaded={onLoaded}
          onError={onError}
          onTransformReady={setTransform}
        />
        {seamHighlight && transform && (
          <SeamEdgeHighlight position3d={seamHighlight} transform={transform} />
        )}
      </Suspense>
      <OrbitControls
        makeDefault
        enableDamping
        dampingFactor={0.08}
        minDistance={1}
        maxDistance={12}
      />
      <gridHelper args={[6, 12, "#e2e8f0", "#f1f5f9"]} position={[0, -1, 0]} />
    </Canvas>
  );
}
