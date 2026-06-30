"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { Line, OrbitControls } from "@react-three/drei";
import { Canvas, useThree } from "@react-three/fiber";
import * as THREE from "three";

import {
  computeModelMeshStats,
  normalizeModelObject,
  type ModelMeshStats,
} from "@/lib/geometry-stats";
import type { SeamEdgeInfo, SeamPosition3d } from "@/lib/seam-manifest";
import {
  buildRayFromPointer,
  pickClosestSeamEdge,
  transformSeamSegment,
  type NormalizeTransform,
} from "@/lib/seam-3d-pick";
import { loadModelFromUrl } from "@/lib/model-loader";

const BASE_MESH_COLOR = "#e85d4c";
const HEAT_COLOR = "#ea580c";

type SceneModelProps = {
  url: string;
  onLoaded: (stats: ModelMeshStats) => void;
  onError: (message: string) => void;
  onTransformReady: (transform: NormalizeTransform) => void;
  faceHeat?: Record<string, number> | null;
  showHeatmap?: boolean;
};

function applyFaceHeatmap(
  object: THREE.Object3D,
  faceHeat: Record<string, number>,
): () => void {
  const restored: Array<{ mesh: THREE.Mesh; material: THREE.Material | THREE.Material[] }> =
    [];

  object.traverse((child) => {
    if (!(child instanceof THREE.Mesh) || !child.geometry) {
      return;
    }

    const geometry = child.geometry;
    const position = geometry.attributes.position;
    if (!position) {
      return;
    }

    restored.push({ mesh: child, material: child.material });

    const colors = new Float32Array(position.count * 3);
    const base = new THREE.Color(BASE_MESH_COLOR);
    const hot = new THREE.Color(HEAT_COLOR);
    const faceColor = new THREE.Color();

    const assignVertex = (vertexIndex: number, heat: number) => {
      faceColor.copy(base).lerp(hot, heat);
      colors[vertexIndex * 3] = faceColor.r;
      colors[vertexIndex * 3 + 1] = faceColor.g;
      colors[vertexIndex * 3 + 2] = faceColor.b;
    };

    if (geometry.index) {
      const index = geometry.index.array;
      const faceCount = index.length / 3;
      for (let faceIndex = 0; faceIndex < faceCount; faceIndex += 1) {
        const heat = faceHeat[String(faceIndex)] ?? 0;
        for (let corner = 0; corner < 3; corner += 1) {
          assignVertex(index[faceIndex * 3 + corner], heat);
        }
      }
    } else {
      const faceCount = position.count / 3;
      for (let faceIndex = 0; faceIndex < faceCount; faceIndex += 1) {
        const heat = faceHeat[String(faceIndex)] ?? 0;
        for (let corner = 0; corner < 3; corner += 1) {
          assignVertex(faceIndex * 3 + corner, heat);
        }
      }
    }

    geometry.setAttribute("color", new THREE.BufferAttribute(colors, 3));
    child.material = new THREE.MeshStandardMaterial({
      vertexColors: true,
      metalness: 0.1,
      roughness: 0.65,
    });
  });

  return () => {
    for (const entry of restored) {
      entry.mesh.material = entry.material;
      const colorAttr = entry.mesh.geometry.getAttribute("color");
      if (colorAttr) {
        entry.mesh.geometry.deleteAttribute("color");
      }
    }
  };
}

function SceneModel({
  url,
  onLoaded,
  onError,
  onTransformReady,
  faceHeat,
  showHeatmap = false,
}: SceneModelProps) {
  const [loaded, setLoaded] = useState<{
    url: string;
    object: THREE.Object3D;
  } | null>(null);
  const onLoadedRef = useRef(onLoaded);
  const onErrorRef = useRef(onError);
  const onTransformReadyRef = useRef(onTransformReady);

  useEffect(() => {
    onLoadedRef.current = onLoaded;
    onErrorRef.current = onError;
    onTransformReadyRef.current = onTransformReady;
  }, [onLoaded, onError, onTransformReady]);

  useEffect(() => {
    let cancelled = false;

    loadModelFromUrl(url)
      .then((loaded) => {
        if (cancelled) return;

        loaded.traverse((child) => {
          if (child instanceof THREE.Mesh) {
            child.castShadow = true;
            child.receiveShadow = true;
            if (!child.material) {
              child.material = new THREE.MeshStandardMaterial({
                color: BASE_MESH_COLOR,
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
        setLoaded({ url, object: loaded });
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

  const object = loaded?.url === url ? loaded.object : null;

  useEffect(() => {
    if (!object || !showHeatmap || !faceHeat || Object.keys(faceHeat).length === 0) {
      return;
    }
    return applyFaceHeatmap(object, faceHeat);
  }, [object, showHeatmap, faceHeat]);

  if (!object) return null;

  return <primitive object={object} />;
}

function SeamEdgeHighlight({
  position3d,
  transform,
}: {
  position3d: SeamPosition3d;
  transform: NormalizeTransform;
}) {
  const [start, end] = transformSeamSegment(position3d, transform);
  const points: [number, number, number][] = [
    [start.x, start.y, start.z],
    [end.x, end.y, end.z],
  ];

  return <Line points={points} color="#e85d4c" lineWidth={3} />;
}

function SeamEdgeLayer({
  edges,
  transform,
  selectedMeshEdge,
}: {
  edges: Record<string, SeamEdgeInfo>;
  transform: NormalizeTransform;
  selectedMeshEdge?: string | null;
}) {
  return (
    <>
      {Object.entries(edges).map(([meshEdge, edge]) => {
        if (!edge.position3d) {
          return null;
        }
        const [start, end] = transformSeamSegment(edge.position3d, transform);
        const points: [number, number, number][] = [
          [start.x, start.y, start.z],
          [end.x, end.y, end.z],
        ];
        const isSelected = meshEdge === selectedMeshEdge;
        const color =
          edge.kind === "cut"
            ? isSelected
              ? "#e85d4c"
              : "rgba(232, 93, 76, 0.35)"
            : isSelected
              ? "#2563eb"
              : "rgba(37, 99, 235, 0.35)";

        return (
          <Line
            key={meshEdge}
            points={points}
            color={color}
            lineWidth={isSelected ? 3 : 1.5}
          />
        );
      })}
    </>
  );
}

function SeamClickPicker({
  enabled,
  edges,
  transform,
  onSelect,
}: {
  enabled: boolean;
  edges: Record<string, SeamEdgeInfo>;
  transform: NormalizeTransform | null;
  onSelect?: (meshEdge: string) => void;
}) {
  const { camera, gl } = useThree();
  const pointerDownRef = useRef<{ x: number; y: number } | null>(null);

  useEffect(() => {
    if (!enabled || !transform || !onSelect) {
      return;
    }

    const canvas = gl.domElement;

    const handlePointerDown = (event: PointerEvent) => {
      pointerDownRef.current = { x: event.clientX, y: event.clientY };
    };

    const handlePointerUp = (event: PointerEvent) => {
      const start = pointerDownRef.current;
      pointerDownRef.current = null;
      if (!start) {
        return;
      }

      const moved =
        Math.abs(event.clientX - start.x) + Math.abs(event.clientY - start.y);
      if (moved > 6) {
        return;
      }

      const rect = canvas.getBoundingClientRect();
      const pointer = new THREE.Vector2(
        ((event.clientX - rect.left) / rect.width) * 2 - 1,
        -((event.clientY - rect.top) / rect.height) * 2 + 1,
      );
      const ray = buildRayFromPointer(camera, pointer);
      const meshEdge = pickClosestSeamEdge(ray, edges, transform, 0.12);
      if (meshEdge) {
        onSelect(meshEdge);
      }
    };

    canvas.addEventListener("pointerdown", handlePointerDown);
    canvas.addEventListener("pointerup", handlePointerUp);
    return () => {
      canvas.removeEventListener("pointerdown", handlePointerDown);
      canvas.removeEventListener("pointerup", handlePointerUp);
    };
  }, [enabled, edges, transform, onSelect, camera, gl]);

  return null;
}

type ModelViewerCanvasProps = {
  url: string;
  onLoaded: (stats: ModelMeshStats) => void;
  onError: (message: string) => void;
  seamHighlight?: SeamPosition3d | null;
  seamEdges?: Record<string, SeamEdgeInfo> | null;
  seamPickEnabled?: boolean;
  selectedSeamMeshEdge?: string | null;
  onSeamSelect?: (meshEdge: string) => void;
  faceHeat?: Record<string, number> | null;
  showHeatmap?: boolean;
};

export function ModelViewerCanvas({
  url,
  onLoaded,
  onError,
  seamHighlight = null,
  seamEdges = null,
  seamPickEnabled = false,
  selectedSeamMeshEdge = null,
  onSeamSelect,
  faceHeat = null,
  showHeatmap = false,
}: ModelViewerCanvasProps) {
  const [transformState, setTransformState] = useState<{
    url: string;
    transform: NormalizeTransform;
  } | null>(null);

  const transform = transformState?.url === url ? transformState.transform : null;

  const seamLayerEnabled = seamPickEnabled && seamEdges && transform;

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
          onTransformReady={(nextTransform) =>
            setTransformState({ url, transform: nextTransform })
          }
          faceHeat={faceHeat}
          showHeatmap={showHeatmap}
        />
        {seamLayerEnabled && (
          <SeamEdgeLayer
            edges={seamEdges}
            transform={transform}
            selectedMeshEdge={selectedSeamMeshEdge}
          />
        )}
        {seamHighlight && transform && (
          <SeamEdgeHighlight position3d={seamHighlight} transform={transform} />
        )}
        {seamLayerEnabled && (
          <SeamClickPicker
            enabled
            edges={seamEdges}
            transform={transform}
            onSelect={onSeamSelect}
          />
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
