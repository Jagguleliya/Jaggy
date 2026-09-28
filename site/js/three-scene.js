// ==========================================================================
// JAGY 3D WebGL Background Scene (Three.js)
// Dynamic Particle Matrix with Mouse Reaction & Gyroscopic Sway
// ==========================================================================

(function initThreeBackground() {
  const canvas = document.getElementById('three-bg');
  if (!canvas || !window.THREE) return;

  const renderer = new THREE.WebGLRenderer({
    canvas: canvas,
    alpha: true,
    antialias: true,
    powerPreference: 'high-performance'
  });

  renderer.setSize(window.innerWidth, window.innerHeight);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(55, window.innerWidth / window.innerHeight, 0.1, 1000);
  camera.position.z = 45;

  // Particle Constellation Geometry
  const particleCount = 750;
  const geometry = new THREE.BufferGeometry();
  const positions = new Float32Array(particleCount * 3);
  const colors = new Float32Array(particleCount * 3);
  const scales = new Float32Array(particleCount);

  // High-Tech Palette: Indigo, Electric Cyan, Hot Pink
  const palette = [
    new THREE.Color('#6366f1'),
    new THREE.Color('#06b6d4'),
    new THREE.Color('#ec4899'),
    new THREE.Color('#3b82f6'),
  ];

  for (let i = 0; i < particleCount; i++) {
    positions[i * 3]     = (Math.random() - 0.5) * 110;
    positions[i * 3 + 1] = (Math.random() - 0.5) * 110;
    positions[i * 3 + 2] = (Math.random() - 0.5) * 70;

    const chosenColor = palette[Math.floor(Math.random() * palette.length)];
    colors[i * 3]     = chosenColor.r;
    colors[i * 3 + 1] = chosenColor.g;
    colors[i * 3 + 2] = chosenColor.b;

    scales[i] = Math.random() * 2.2 + 0.6;
  }

  geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
  geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  geometry.setAttribute('scale', new THREE.BufferAttribute(scales, 1));

  // Particle Shader/Material
  const material = new THREE.PointsMaterial({
    size: 1.6,
    vertexColors: true,
    transparent: true,
    opacity: 0.55,
    blending: THREE.AdditiveBlending,
    sizeAttenuation: true
  });

  const particles = new THREE.Points(geometry, material);
  scene.add(particles);

  // Subtle Wireframe Core Geometry (Torus Knot)
  const knotGeo = new THREE.TorusKnotGeometry(12, 2.5, 90, 16);
  const knotMat = new THREE.MeshBasicMaterial({
    color: 0x6366f1,
    wireframe: true,
    transparent: true,
    opacity: 0.04
  });
  const torusKnot = new THREE.Mesh(knotGeo, knotMat);
  torusKnot.position.set(0, -2, -10);
  scene.add(torusKnot);

  // Mouse Tracking with Smooth Damping
  let mouseX = 0;
  let mouseY = 0;
  let targetX = 0;
  let targetY = 0;

  window.addEventListener('mousemove', (e) => {
    targetX = (e.clientX / window.innerWidth - 0.5) * 2;
    targetY = (e.clientY / window.innerHeight - 0.5) * 2;
  });

  // Render Loop
  let clock = new THREE.Clock();

  function animate() {
    requestAnimationFrame(animate);
    const elapsedTime = clock.getElapsedTime();

    // Damping mouse response
    mouseX += (targetX - mouseX) * 0.04;
    mouseY += (targetY - mouseY) * 0.04;

    particles.rotation.y = elapsedTime * 0.03 + mouseX * 0.25;
    particles.rotation.x = elapsedTime * 0.015 - mouseY * 0.25;

    torusKnot.rotation.x = elapsedTime * 0.08 + mouseY * 0.4;
    torusKnot.rotation.y = elapsedTime * 0.12 + mouseX * 0.4;

    camera.position.x = mouseX * 4;
    camera.position.y = -mouseY * 4;
    camera.lookAt(scene.position);

    renderer.render(scene, camera);
  }

  animate();

  // Resize Handler
  window.addEventListener('resize', () => {
    camera.aspect = window.innerWidth / window.innerHeight;
    camera.updateProjectionMatrix();
    renderer.setSize(window.innerWidth, window.innerHeight);
  });
})();
