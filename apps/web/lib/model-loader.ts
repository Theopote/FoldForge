import * as THREE from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { OBJLoader } from "three/addons/loaders/OBJLoader.js";
import { STLLoader } from "three/addons/loaders/STLLoader.js";

import { withStorageAuth } from "@/lib/api-auth";

export type ModelFormat = "glb" | "gltf" | "obj" | "stl";

export function getModelFormat(url: string): ModelFormat | null {
  const extension = url.split("?")[0].split(".").pop()?.toLowerCase();
  if (
    extension === "glb" ||
    extension === "gltf" ||
    extension === "obj" ||
    extension === "stl"
  ) {
    return extension;
  }
  return null;
}

/**
 * Load a 3D model from URL using the appropriate Three.js loader.
 */
export async function loadModelFromUrl(url: string): Promise<THREE.Object3D> {
  const authenticatedUrl = withStorageAuth(url);
  const format = getModelFormat(authenticatedUrl);
  if (!format) {
    throw new Error(`Unsupported model format for URL: ${url}`);
  }

  switch (format) {
    case "glb":
    case "gltf": {
      const loader = new GLTFLoader();
      const gltf = await loader.loadAsync(authenticatedUrl);
      return gltf.scene;
    }
    case "obj": {
      const loader = new OBJLoader();
      return loader.loadAsync(authenticatedUrl);
    }
    case "stl": {
      const loader = new STLLoader();
      const geometry = await loader.loadAsync(authenticatedUrl);
      const material = new THREE.MeshStandardMaterial({
        color: "#e85d4c",
        metalness: 0.1,
        roughness: 0.65,
      });
      return new THREE.Mesh(geometry, material);
    }
    default:
      throw new Error(`Unsupported format: ${format}`);
  }
}
