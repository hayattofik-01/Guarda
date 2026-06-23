"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

const PARTICLE_COUNT = 220;
const CONNECTION_DIST = 120;
const FIELD_W = 1400;
const FIELD_H = 900;
const FIELD_D = 400;

export default function ParticleField() {
  const containerRef = useRef<HTMLDivElement>(null);
  const frameRef = useRef(0);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, el.clientWidth / el.clientHeight, 1, 2000);
    camera.position.z = 600;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(el.clientWidth, el.clientHeight);
    renderer.setClearColor(0x000000, 0);
    el.appendChild(renderer.domElement);

    // Particles
    const positions = new Float32Array(PARTICLE_COUNT * 3);
    const velocities: THREE.Vector3[] = [];
    for (let i = 0; i < PARTICLE_COUNT; i++) {
      positions[i * 3] = (Math.random() - 0.5) * FIELD_W;
      positions[i * 3 + 1] = (Math.random() - 0.5) * FIELD_H;
      positions[i * 3 + 2] = (Math.random() - 0.5) * FIELD_D;
      velocities.push(
        new THREE.Vector3(
          (Math.random() - 0.5) * 0.35,
          (Math.random() - 0.5) * 0.35,
          (Math.random() - 0.5) * 0.15,
        ),
      );
    }

    const particleGeo = new THREE.BufferGeometry();
    particleGeo.setAttribute("position", new THREE.BufferAttribute(positions, 3));

    const particleMat = new THREE.PointsMaterial({
      color: 0x7c5cff,
      size: 3,
      transparent: true,
      opacity: 0.7,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const points = new THREE.Points(particleGeo, particleMat);
    scene.add(points);

    // Connection lines
    const maxLines = PARTICLE_COUNT * 6;
    const linePositions = new Float32Array(maxLines * 6);
    const lineColors = new Float32Array(maxLines * 6);
    const lineGeo = new THREE.BufferGeometry();
    lineGeo.setAttribute("position", new THREE.BufferAttribute(linePositions, 3));
    lineGeo.setAttribute("color", new THREE.BufferAttribute(lineColors, 3));
    lineGeo.setDrawRange(0, 0);

    const lineMat = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.35,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });
    const lines = new THREE.LineSegments(lineGeo, lineMat);
    scene.add(lines);

    // Glowing orbs
    const orbGeo = new THREE.SphereGeometry(4, 16, 16);
    const orbMat = new THREE.MeshBasicMaterial({
      color: 0xa78bfa,
      transparent: true,
      opacity: 0.5,
    });
    const orbs: THREE.Mesh[] = [];
    for (let i = 0; i < 5; i++) {
      const orb = new THREE.Mesh(orbGeo, orbMat.clone());
      orb.position.set(
        (Math.random() - 0.5) * FIELD_W * 0.7,
        (Math.random() - 0.5) * FIELD_H * 0.7,
        (Math.random() - 0.5) * FIELD_D * 0.3,
      );
      scene.add(orb);
      orbs.push(orb);
    }

    // Mouse interaction
    const mouse = new THREE.Vector2(0, 0);
    function onMouseMove(e: MouseEvent) {
      mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
      mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
    }
    window.addEventListener("mousemove", onMouseMove);

    function animate() {
      frameRef.current = requestAnimationFrame(animate);

      // Move particles
      const posArr = particleGeo.attributes.position.array as Float32Array;
      for (let i = 0; i < PARTICLE_COUNT; i++) {
        posArr[i * 3] += velocities[i].x;
        posArr[i * 3 + 1] += velocities[i].y;
        posArr[i * 3 + 2] += velocities[i].z;

        if (Math.abs(posArr[i * 3]) > FIELD_W / 2) velocities[i].x *= -1;
        if (Math.abs(posArr[i * 3 + 1]) > FIELD_H / 2) velocities[i].y *= -1;
        if (Math.abs(posArr[i * 3 + 2]) > FIELD_D / 2) velocities[i].z *= -1;
      }
      particleGeo.attributes.position.needsUpdate = true;

      // Draw connections
      let lineIdx = 0;
      const lp = lineGeo.attributes.position.array as Float32Array;
      const lc = lineGeo.attributes.color.array as Float32Array;
      for (let i = 0; i < PARTICLE_COUNT; i++) {
        for (let j = i + 1; j < PARTICLE_COUNT; j++) {
          if (lineIdx >= maxLines) break;
          const dx = posArr[i * 3] - posArr[j * 3];
          const dy = posArr[i * 3 + 1] - posArr[j * 3 + 1];
          const dz = posArr[i * 3 + 2] - posArr[j * 3 + 2];
          const dist = Math.sqrt(dx * dx + dy * dy + dz * dz);
          if (dist < CONNECTION_DIST) {
            const alpha = 1 - dist / CONNECTION_DIST;
            const r = 0.486 * alpha;
            const g = 0.361 * alpha;
            const b = 1.0 * alpha;
            lp[lineIdx * 6] = posArr[i * 3];
            lp[lineIdx * 6 + 1] = posArr[i * 3 + 1];
            lp[lineIdx * 6 + 2] = posArr[i * 3 + 2];
            lp[lineIdx * 6 + 3] = posArr[j * 3];
            lp[lineIdx * 6 + 4] = posArr[j * 3 + 1];
            lp[lineIdx * 6 + 5] = posArr[j * 3 + 2];
            lc[lineIdx * 6] = r;
            lc[lineIdx * 6 + 1] = g;
            lc[lineIdx * 6 + 2] = b;
            lc[lineIdx * 6 + 3] = r;
            lc[lineIdx * 6 + 4] = g;
            lc[lineIdx * 6 + 5] = b;
            lineIdx++;
          }
        }
      }
      lineGeo.setDrawRange(0, lineIdx * 2);
      lineGeo.attributes.position.needsUpdate = true;
      lineGeo.attributes.color.needsUpdate = true;

      // Animate orbs
      const t = Date.now() * 0.001;
      orbs.forEach((orb, i) => {
        orb.position.x += Math.sin(t + i * 1.5) * 0.4;
        orb.position.y += Math.cos(t + i * 1.2) * 0.3;
        const mat = orb.material as THREE.MeshBasicMaterial;
        mat.opacity = 0.3 + Math.sin(t * 2 + i) * 0.2;
        orb.scale.setScalar(1 + Math.sin(t * 1.5 + i) * 0.3);
      });

      // Camera follow mouse
      camera.position.x += (mouse.x * 60 - camera.position.x) * 0.02;
      camera.position.y += (mouse.y * 40 - camera.position.y) * 0.02;
      camera.lookAt(scene.position);

      renderer.render(scene, camera);
    }
    animate();

    function onResize() {
      if (!el) return;
      camera.aspect = el.clientWidth / el.clientHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(el.clientWidth, el.clientHeight);
    }
    window.addEventListener("resize", onResize);

    return () => {
      cancelAnimationFrame(frameRef.current);
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("resize", onResize);
      renderer.dispose();
      if (el.contains(renderer.domElement)) el.removeChild(renderer.domElement);
    };
  }, []);

  return (
    <div
      ref={containerRef}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 0,
        pointerEvents: "none",
      }}
    />
  );
}
