import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import type { Network, Result } from "./types";

const colors = {
  supplier: 0x70d9b1,
  plant: 0xf2bb68,
  dc: 0x73aaf2,
  customer: 0x8795ac,
};
export default function NetworkMap({
  network,
  result,
  day,
  onSelect,
}: {
  network: Network;
  result?: Result;
  day: number;
  onSelect: (id: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const [unsupported, setUnsupported] = useState(false);
  useEffect(() => {
    const host = ref.current!;
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch {
      setUnsupported(true);
      return;
    }
    renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
    host.appendChild(renderer.domElement);
    renderer.domElement.setAttribute(
      "aria-label",
      "Geographic supply network. Use the node list to inspect a facility.",
    );
    const scene = new THREE.Scene();
    const camera = new THREE.OrthographicCamera(
      -190,
      190,
      100,
      -100,
      0.1,
      1000,
    );
    camera.position.z = 300;
    const project = (lon: number, lat: number) =>
      new THREE.Vector3(lon, lat * 1.5, 0);
    const positions = Object.fromEntries(
      network.nodes.map((n) => [n.id, project(n.longitude, n.latitude)]),
    );
    const geometries: THREE.BufferGeometry[] = [];
    const materials: THREE.Material[] = [];
    function line(points: THREE.Vector3[], color: number, opacity: number) {
      const g = new THREE.BufferGeometry().setFromPoints(points);
      const m = new THREE.LineBasicMaterial({
        color,
        transparent: true,
        opacity,
      });
      geometries.push(g);
      materials.push(m);
      scene.add(new THREE.Line(g, m));
    }
    for (let lon = -180; lon <= 180; lon += 30)
      line([project(lon, -60), project(lon, 70)], 0x516078, 0.16);
    for (let lat = -60; lat <= 70; lat += 20)
      line([project(-180, lat), project(180, lat)], 0x516078, 0.16);
    const dots: {
      mesh: THREE.Mesh;
      curve: THREE.QuadraticBezierCurve3;
      phase: number;
    }[] = [];
    const flow = new Map(
      result?.flows
        .filter((f) => f.day === day)
        .map((f) => [f.lane_id, f.units]),
    );
    network.lanes.forEach((lane, index) => {
      const a = positions[lane.source],
        b = positions[lane.target];
      const mid = a.clone().add(b).multiplyScalar(0.5);
      mid.y += a.distanceTo(b) * 0.12;
      const curve = new THREE.QuadraticBezierCurve3(a, mid, b);
      const units = flow.get(lane.id) || 0;
      const color = units > 0 ? 0x61cda4 : 0x45536b;
      line(curve.getPoints(36), color, units > 0 ? 0.42 : 0.2);
      if (units > 0) {
        for (let p = 0; p < Math.min(5, Math.ceil(units / 130)); p++) {
          const g = new THREE.SphereGeometry(0.65, 6, 6),
            m = new THREE.MeshBasicMaterial({ color: 0xa3f2cd });
          geometries.push(g);
          materials.push(m);
          const mesh = new THREE.Mesh(g, m);
          scene.add(mesh);
          dots.push({ mesh, curve, phase: p / 5 + index * 0.137 });
        }
      }
    });
    const clickable: THREE.Mesh[] = [];
    network.nodes.forEach((n) => {
      const g = new THREE.CircleGeometry(n.kind === "customer" ? 1.3 : 2.7, 20),
        m = new THREE.MeshBasicMaterial({ color: colors[n.kind] });
      geometries.push(g);
      materials.push(m);
      const mesh = new THREE.Mesh(g, m);
      mesh.position.copy(positions[n.id]);
      mesh.position.z = 2;
      mesh.userData.id = n.id;
      scene.add(mesh);
      clickable.push(mesh);
    });
    const raycaster = new THREE.Raycaster();
    const click = (event: MouseEvent) => {
      const r = renderer.domElement.getBoundingClientRect();
      raycaster.setFromCamera(
        new THREE.Vector2(
          ((event.clientX - r.left) / r.width) * 2 - 1,
          (-(event.clientY - r.top) / r.height) * 2 + 1,
        ),
        camera,
      );
      const hits = raycaster.intersectObjects(clickable);
      if (hits[0]) onSelect(hits[0].object.userData.id);
    };
    renderer.domElement.addEventListener("click", click);
    const resize = () => {
      const { width, height } = host.getBoundingClientRect();
      renderer.setSize(width, height);
      const aspect = width / height;
      camera.left = -190;
      camera.right = 190;
      camera.top = 190 / aspect;
      camera.bottom = -190 / aspect;
      camera.updateProjectionMatrix();
    };
    const observer = new ResizeObserver(resize);
    observer.observe(host);
    resize();
    const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
    let frame = 0;
    function animate(t: number) {
      dots.forEach((d) =>
        d.mesh.position.copy(
          d.curve.getPoint(((reduced ? 0 : t * 0.00009) + d.phase) % 1),
        ),
      );
      renderer.render(scene, camera);
      frame = requestAnimationFrame(animate);
    }
    frame = requestAnimationFrame(animate);
    return () => {
      cancelAnimationFrame(frame);
      observer.disconnect();
      renderer.domElement.removeEventListener("click", click);
      geometries.forEach((g) => g.dispose());
      materials.forEach((m) => m.dispose());
      renderer.dispose();
      renderer.domElement.remove();
    };
  }, [network, result, day, onSelect]);
  return (
    <div className="map-host" ref={ref}>
      {unsupported && (
        <div className="empty">
          WebGL is unavailable. All network data and facility details remain
          available below.
        </div>
      )}
    </div>
  );
}
