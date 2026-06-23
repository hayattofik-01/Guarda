"use client";

import { useEffect, useRef } from "react";
import * as THREE from "three";

const RING_COUNT = 4;
const PACKETS_PER_RING = 12;
const DEBRIS_COUNT = 60;

export default function ParticleField() {
  const containerRef = useRef<HTMLDivElement>(null);
  const frameRef = useRef(0);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(55, el.clientWidth / el.clientHeight, 1, 2000);
    camera.position.z = 500;

    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setSize(el.clientWidth, el.clientHeight);
    renderer.setClearColor(0x000000, 0);
    el.appendChild(renderer.domElement);

    // Central rotating icosahedron "shield core"
    const coreGeo = new THREE.IcosahedronGeometry(38, 1);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0x7c5cff,
      wireframe: true,
      transparent: true,
      opacity: 0.35,
    });
    const core = new THREE.Mesh(coreGeo, coreMat);
    scene.add(core);

    // Inner glow sphere
    const glowGeo = new THREE.SphereGeometry(28, 32, 32);
    const glowMat = new THREE.MeshBasicMaterial({
      color: 0xa78bfa,
      transparent: true,
      opacity: 0.08,
      blending: THREE.AdditiveBlending,
    });
    const glow = new THREE.Mesh(glowGeo, glowMat);
    scene.add(glow);

    // Orbital rings — tilted at different angles, each carrying "data packets"
    const rings: {
      group: THREE.Group;
      radius: number;
      speed: number;
      packets: THREE.Mesh[];
    }[] = [];

    const ringRadii = [90, 140, 200, 280];
    const ringTilts = [
      { x: 0.3, z: 0.1 },
      { x: -0.5, z: 0.8 },
      { x: 0.9, z: -0.3 },
      { x: -0.2, z: 1.2 },
    ];
    const ringSpeeds = [0.4, -0.28, 0.18, -0.12];
    const packetColors = [0x7c5cff, 0x06b6d4, 0xa78bfa, 0x22d3ee];

    for (let r = 0; r < RING_COUNT; r++) {
      const group = new THREE.Group();
      group.rotation.x = ringTilts[r].x;
      group.rotation.z = ringTilts[r].z;
      scene.add(group);

      // Visible ring path
      const curve = new THREE.EllipseCurve(0, 0, ringRadii[r], ringRadii[r], 0, Math.PI * 2, false, 0);
      const points = curve.getPoints(80);
      const ringLineGeo = new THREE.BufferGeometry().setFromPoints(
        points.map((p) => new THREE.Vector3(p.x, p.y, 0)),
      );
      const ringLineMat = new THREE.LineBasicMaterial({
        color: packetColors[r],
        transparent: true,
        opacity: 0.08,
        blending: THREE.AdditiveBlending,
      });
      group.add(new THREE.Line(ringLineGeo, ringLineMat));

      // Data packets on each ring
      const packets: THREE.Mesh[] = [];
      const geos = [
        new THREE.BoxGeometry(5, 5, 5),
        new THREE.OctahedronGeometry(4),
        new THREE.TetrahedronGeometry(5),
      ];
      for (let p = 0; p < PACKETS_PER_RING; p++) {
        const geo = geos[p % geos.length];
        const mat = new THREE.MeshBasicMaterial({
          color: packetColors[r],
          transparent: true,
          opacity: 0.6,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        });
        const mesh = new THREE.Mesh(geo, mat);
        group.add(mesh);
        packets.push(mesh);
      }

      rings.push({ group, radius: ringRadii[r], speed: ringSpeeds[r], packets });
    }

    // Floating debris — small geometric shards drifting in space
    const debris: { mesh: THREE.Mesh; vel: THREE.Vector3; rotSpeed: THREE.Vector3 }[] = [];
    const debrisGeos = [
      new THREE.TetrahedronGeometry(2),
      new THREE.OctahedronGeometry(1.5),
      new THREE.BoxGeometry(2, 2, 2),
    ];
    for (let i = 0; i < DEBRIS_COUNT; i++) {
      const geo = debrisGeos[i % debrisGeos.length];
      const mat = new THREE.MeshBasicMaterial({
        color: i % 3 === 0 ? 0x06b6d4 : 0x7c5cff,
        transparent: true,
        opacity: 0.3 + Math.random() * 0.3,
        blending: THREE.AdditiveBlending,
        depthWrite: false,
      });
      const mesh = new THREE.Mesh(geo, mat);
      mesh.position.set(
        (Math.random() - 0.5) * 1200,
        (Math.random() - 0.5) * 800,
        (Math.random() - 0.5) * 400,
      );
      scene.add(mesh);
      debris.push({
        mesh,
        vel: new THREE.Vector3(
          (Math.random() - 0.5) * 0.2,
          (Math.random() - 0.5) * 0.2,
          (Math.random() - 0.5) * 0.1,
        ),
        rotSpeed: new THREE.Vector3(
          Math.random() * 0.02,
          Math.random() * 0.02,
          Math.random() * 0.01,
        ),
      });
    }

    // Pulse waves — expanding rings from center
    const pulses: THREE.Mesh[] = [];
    const pulseGeo = new THREE.RingGeometry(1, 3, 64);
    let lastPulse = 0;

    // Mouse interaction
    const mouse = new THREE.Vector2(0, 0);
    function onMouseMove(e: MouseEvent) {
      mouse.x = (e.clientX / window.innerWidth) * 2 - 1;
      mouse.y = -(e.clientY / window.innerHeight) * 2 + 1;
    }
    window.addEventListener("mousemove", onMouseMove);

    function animate() {
      frameRef.current = requestAnimationFrame(animate);
      const t = Date.now() * 0.001;

      // Rotate core
      core.rotation.x = t * 0.15;
      core.rotation.y = t * 0.2;
      const corePulse = 0.3 + Math.sin(t * 1.5) * 0.08;
      (core.material as THREE.MeshBasicMaterial).opacity = corePulse;
      const glowScale = 1 + Math.sin(t * 2) * 0.15;
      glow.scale.setScalar(glowScale);

      // Animate orbital packets
      rings.forEach((ring) => {
        ring.packets.forEach((pkt, i) => {
          const angle = t * ring.speed + (i / PACKETS_PER_RING) * Math.PI * 2;
          pkt.position.x = Math.cos(angle) * ring.radius;
          pkt.position.y = Math.sin(angle) * ring.radius;
          pkt.position.z = Math.sin(angle * 2) * 15;
          pkt.rotation.x = t * 1.5 + i;
          pkt.rotation.y = t * 1.2 + i * 0.5;
          const mat = pkt.material as THREE.MeshBasicMaterial;
          mat.opacity = 0.35 + Math.sin(t * 3 + i * 0.7) * 0.25;
          const s = 0.7 + Math.sin(t * 2 + i) * 0.3;
          pkt.scale.setScalar(s);
        });
      });

      // Animate debris
      debris.forEach((d) => {
        d.mesh.position.add(d.vel);
        d.mesh.rotation.x += d.rotSpeed.x;
        d.mesh.rotation.y += d.rotSpeed.y;
        if (Math.abs(d.mesh.position.x) > 600) d.vel.x *= -1;
        if (Math.abs(d.mesh.position.y) > 400) d.vel.y *= -1;
        if (Math.abs(d.mesh.position.z) > 200) d.vel.z *= -1;
      });

      // Spawn pulse waves periodically
      if (t - lastPulse > 3) {
        lastPulse = t;
        const pulseMat = new THREE.MeshBasicMaterial({
          color: 0x7c5cff,
          transparent: true,
          opacity: 0.3,
          side: THREE.DoubleSide,
          blending: THREE.AdditiveBlending,
          depthWrite: false,
        });
        const pulse = new THREE.Mesh(pulseGeo, pulseMat);
        pulse.userData.born = t;
        scene.add(pulse);
        pulses.push(pulse);
      }

      // Animate pulses
      for (let i = pulses.length - 1; i >= 0; i--) {
        const p = pulses[i];
        const age = t - p.userData.born;
        const scale = 1 + age * 80;
        p.scale.setScalar(scale);
        (p.material as THREE.MeshBasicMaterial).opacity = Math.max(0, 0.3 - age * 0.1);
        if (age > 3) {
          scene.remove(p);
          pulses.splice(i, 1);
        }
      }

      // Camera follows mouse with gentle sway
      camera.position.x += (mouse.x * 80 - camera.position.x) * 0.015;
      camera.position.y += (mouse.y * 50 - camera.position.y) * 0.015;
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
