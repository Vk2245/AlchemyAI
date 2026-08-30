"use client";
/**
 * FILE: AlchemyJar3D.tsx
 * PURPOSE: Loads the Blender-exported .glb jar model and renders it
 *          with scroll-driven rotation. Colors are force-applied in code.
 * USED BY: page.tsx (homepage hero)
 * USES: three, @react-three/fiber, @react-three/drei, framer-motion
 */
import React, { useRef, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { useGLTF, Environment } from "@react-three/drei";
import * as THREE from "three";
import { useScroll } from "framer-motion";

// ──────────────────────────────────────────────
// 3D Model Loader + Material Override
// ──────────────────────────────────────────────
function Model() {
  const group = useRef<THREE.Group>(null);
  const { scene } = useGLTF("/alchemyai copy.glb");
  const { scrollYProgress } = useScroll();

  // Force exact logo colors onto every mesh
  useEffect(() => {
    scene.traverse((child: any) => {
      if (!child.isMesh) return;
      const name = child.name.toLowerCase();

      // HIDE the bounding box for smoke
      if (name.includes("smoke") || name.includes("volume")) {
        child.visible = false;
        return;
      }

      if (name.includes("flaskbody") || name.includes("neck")) {
        // Dark crystal body — visible against #030303
        child.material = new THREE.MeshPhysicalMaterial({
          color: new THREE.Color(0x1a0e3e),
          emissive: new THREE.Color(0x3d1d80),
          emissiveIntensity: 0.6,
          metalness: 0.4,
          roughness: 0.08,
          transparent: true,
          opacity: 0.75,
          side: THREE.DoubleSide,
        });
      } else if (name.includes("innercore")) {
        // Violet/Blue glowing core
        child.material = new THREE.MeshBasicMaterial({
          color: new THREE.Color(0x8b5cf6),
          transparent: true,
          opacity: 0.9,
          side: THREE.DoubleSide,
        });
      } else if (name.includes("stopper")) {
        // Dark stopper with glow
        child.material = new THREE.MeshStandardMaterial({
          color: new THREE.Color(0x2d1b69),
          emissive: new THREE.Color(0x5b2ea0),
          emissiveIntensity: 2.0,
          metalness: 0.5,
          roughness: 0.12,
        });
      } else if (name.includes("text")) {
        // 3D Text (Alchemy / AI)
        child.material = new THREE.MeshStandardMaterial({
          color: new THREE.Color(0xc0c5dd),
          emissive: new THREE.Color(0x3b82f6),
          emissiveIntensity: 1.0,
          metalness: 1.0,
          roughness: 0.1,
        });
      } else {
        // Fallback — Dark crystal
        child.material = new THREE.MeshPhysicalMaterial({
          color: new THREE.Color(0x1a0e3e),
          emissive: new THREE.Color(0x3d1d80),
          emissiveIntensity: 0.6,
          metalness: 0.4,
          roughness: 0.08,
          transparent: true,
          opacity: 0.75,
          side: THREE.DoubleSide,
        });
      }
    });
  }, [scene]);

  // Scroll + idle rotation
  useFrame((state) => {
    if (group.current) {
      const scrollTwist = scrollYProgress.get() * Math.PI * 4;
      const idleRotation = state.clock.elapsedTime * 0.3;
      group.current.rotation.y = scrollTwist + idleRotation;
      group.current.rotation.x = Math.sin(state.clock.elapsedTime * 0.5) * 0.08;
      group.current.rotation.z = Math.cos(state.clock.elapsedTime * 0.5) * 0.04;
      group.current.position.y = Math.sin(state.clock.elapsedTime * 0.8) * 0.15;
    }
  });

  return (
    <group ref={group} dispose={null} scale={0.9} position={[0, -0.8, 0]}>
      <primitive object={scene} />
    </group>
  );
}

// ──────────────────────────────────────────────
// EXPORT: 3D Jar Canvas (transparent background)
// ──────────────────────────────────────────────
export default function AlchemyJar3D() {
  return (
    <Canvas
      camera={{ position: [0, 0, 7], fov: 45 }}
      gl={{ alpha: true }}
      style={{ background: "transparent" }}
    >
      <ambientLight intensity={0.6} />
      <directionalLight position={[-8, 5, 5]} intensity={5} color="#8b5cf6" />
      <directionalLight position={[8, 5, 5]} intensity={5} color="#3b82f6" />
      <directionalLight position={[0, -5, 5]} intensity={1.5} color="#ffffff" />
      <pointLight position={[0, 0, 0]} intensity={4} color="#8b5cf6" distance={8} />
      <pointLight position={[0, 1, 0]} intensity={3} color="#3b82f6" distance={6} />
      <Environment preset="night" />
      <React.Suspense fallback={null}>
        <Model />
      </React.Suspense>
    </Canvas>
  );
}

useGLTF.preload("/alchemyai copy.glb");
