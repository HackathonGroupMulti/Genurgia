"use client";

import { useEffect, useRef, useState } from "react";

export function SimulationFieldViewer({ reference }: { reference: string | null }) {
  const host = useRef<HTMLDivElement>(null);
  const [message, setMessage] = useState(
    reference ? "Loading browser-readable VTK field…" : "No VTK field was published for this pose.",
  );

  useEffect(() => {
    const element = host.current;
    if (!element || !reference) return;
    const container = element;
    let disposed = false;
    let cleanup = () => {};

    async function renderField() {
      try {
        const THREE = await import("three");
        const { VTKLoader } = await import("three/examples/jsm/loaders/VTKLoader.js");
        const response = await fetch(`/api/knee-twin${reference}`, { cache: "no-store" });
        if (!response.ok) throw new Error(`VTK artifact returned HTTP ${response.status}.`);
        const geometry = new VTKLoader().parse(await response.arrayBuffer(), "");
        geometry.computeVertexNormals();
        geometry.center();
        const scene = new THREE.Scene();
        scene.background = new THREE.Color(0xf8f7f1);
        const camera = new THREE.PerspectiveCamera(35, 1, 0.01, 10000);
        camera.position.set(0, 0, 120);
        const renderer = new THREE.WebGLRenderer({ antialias: true });
        renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
        const material = new THREE.MeshNormalMaterial({ side: THREE.DoubleSide });
        const mesh = new THREE.Mesh(geometry, material);
        scene.add(mesh);
        const box = new THREE.Box3().setFromObject(mesh);
        const sphere = box.getBoundingSphere(new THREE.Sphere());
        camera.position.z = Math.max(sphere.radius * 3, 1);
        camera.near = Math.max(sphere.radius / 100, 0.001);
        camera.far = Math.max(sphere.radius * 20, 10);
        camera.updateProjectionMatrix();
        container.replaceChildren(renderer.domElement);
        const resize = () => {
          const width = container.clientWidth || 640;
          const height = Math.max(320, Math.round(width * 0.56));
          renderer.setSize(width, height, false);
          camera.aspect = width / height;
          camera.updateProjectionMatrix();
        };
        resize();
        window.addEventListener("resize", resize);
        let frame = 0;
        const animate = () => {
          if (disposed) return;
          mesh.rotation.y += 0.003;
          renderer.render(scene, camera);
          frame = requestAnimationFrame(animate);
        };
        animate();
        cleanup = () => {
          cancelAnimationFrame(frame);
          window.removeEventListener("resize", resize);
          geometry.dispose();
          material.dispose();
          renderer.dispose();
        };
        setMessage("Presentation view of the published VTK field geometry.");
      } catch (error) {
        if (!disposed) {
          setMessage(error instanceof Error ? error.message : "VTK field could not be rendered.");
        }
      }
    }

    void renderField();
    return () => {
      disposed = true;
      cleanup();
    };
  }, [reference]);

  return (
    <figure className="simulation-field">
      <div ref={host} className="simulation-field-canvas" />
      <figcaption>{message} This view is simulated and is not anatomical ground truth.</figcaption>
    </figure>
  );
}
