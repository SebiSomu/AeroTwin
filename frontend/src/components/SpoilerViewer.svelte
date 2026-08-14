<script lang="ts">
  import { onMount } from "svelte";
  import * as THREE from "three";
  import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
  import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

  let { angle = 4 }: { angle?: number } = $props();
  let container: HTMLDivElement;
  let canvas: HTMLCanvasElement;
  let loading = $state(true);
  let loadError = $state(false);

  let renderer: THREE.WebGLRenderer;
  let scene: THREE.Scene;
  let camera: THREE.PerspectiveCamera;
  let controls: OrbitControls;
  let animFrameId: number;

  const STREAMLINE_COUNT = 80;
  const POINTS_PER_LINE = 40;
  const TOTAL_VERTICES = STREAMLINE_COUNT * (POINTS_PER_LINE - 1) * 2;

  let lineSegmentsMesh: THREE.LineSegments;
  let linePositions: Float32Array;
  let lineColors: Float32Array;
  const PARTICLE_COUNT = 500;
  let particlePoints: THREE.Points;
  let particlePositions: Float32Array;
  let particleColors: Float32Array;
  let particleProgress: Float32Array;
  let particleStreamId: Int32Array;

  interface StreamSeed {
    x: number;
    y: number;
    speedOffset: number;
  }
  let seeds: StreamSeed[] = [];
  const COLOR_BLUE = new THREE.Color("#0033FF");
  const COLOR_CYAN = new THREE.Color("#00E5FF");
  const COLOR_GREEN = new THREE.Color("#00FF66");
  const COLOR_YELLOW = new THREE.Color("#FFDD00");
  const COLOR_RED = new THREE.Color("#FF1100");
  let currentAoA = $derived(angle);
  let flowTime = 0;

  let wingCenter = new THREE.Vector3(0, 0, 0);
  let wingSize = new THREE.Vector3(0.9, 0.4, 0.4);

  onMount(() => {
    renderer = new THREE.WebGLRenderer({
      canvas,
      antialias: true,
      alpha: true,
    });
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.1;
    renderer.setClearColor(0x000000, 0);

    scene = new THREE.Scene();

    const { clientWidth: w, clientHeight: h } = container;
    camera = new THREE.PerspectiveCamera(40, w / h, 0.01, 100);
    camera.position.set(0.65, 0.22, 0.55);

    const ambient = new THREE.AmbientLight(0xc7d2da, 1.4);
    scene.add(ambient);

    const key = new THREE.DirectionalLight(0x7fa6b3, 2.2);
    key.position.set(2, 3, 2);
    scene.add(key);

    const fill = new THREE.DirectionalLight(0xfff5e6, 0.7);
    fill.position.set(-2, 1, -1);
    scene.add(fill);

    const rim = new THREE.DirectionalLight(0xc9a15f, 0.5);
    rim.position.set(0, -1, -2);
    scene.add(rim);

    controls = new OrbitControls(camera, canvas);
    controls.enableDamping = true;
    controls.dampingFactor = 0.07;
    controls.enablePan = false;
    controls.minDistance = 0.2;
    controls.maxDistance = 2.5;
    controls.autoRotate = true;
    controls.autoRotateSpeed = 1.0;
    controls.target.set(0, 0, 0);

    const stopAutoRotate = () => {
      controls.autoRotate = false;
      canvas.removeEventListener("pointerdown", stopAutoRotate);
    };
    canvas.addEventListener("pointerdown", stopAutoRotate);

    initWindStreamlines();

    const loader = new GLTFLoader();
    loader.load(
      "/models/porsche_gt3rs_spoiler.glb",
      (gltf) => {
        const model = gltf.scene;

        const box = new THREE.Box3().setFromObject(model);
        const centre = new THREE.Vector3();
        box.getCenter(centre);
        const size = box.getSize(new THREE.Vector3());
        const maxDim = Math.max(size.x, size.y, size.z);
        const scale = 0.85 / maxDim;

        model.position.sub(centre.multiplyScalar(scale));
        model.scale.setScalar(scale);
        model.rotation.set(0, Math.PI, 0);

        const worldBox = new THREE.Box3().setFromObject(model);
        worldBox.getCenter(wingCenter);
        worldBox.getSize(wingSize);

        model.traverse((child) => {
          if ((child as THREE.Mesh).isMesh) {
            const mesh = child as THREE.Mesh;
            const materials = Array.isArray(mesh.material)
              ? mesh.material
              : [mesh.material];
            materials.forEach((mat) => {
              if (mat instanceof THREE.MeshStandardMaterial) {
                mat.envMapIntensity = 0.8;
              }
            });
            mesh.castShadow = true;
            mesh.receiveShadow = true;
          }
        });

        scene.add(model);
        loading = false;
        fitCamera(model);
      },
      undefined,
      (_err) => {
        loading = false;
        loadError = true;
      },
    );

    const ro = new ResizeObserver(() => resize());
    ro.observe(container);
    resize();

    const clock = new THREE.Clock();
    const loop = () => {
      animFrameId = requestAnimationFrame(loop);
      const delta = clock.getDelta();
      flowTime += delta;
      updateWindStreamlines(delta);
      controls.update();
      renderer.render(scene, camera);
    };
    loop();

    return () => {
      ro.disconnect();
      cancelAnimationFrame(animFrameId);
      controls.dispose();
      renderer.dispose();
    };
  });

  function getF1CFDColor(
    velocityRatio: number,
    isStalled: boolean,
    inWake: boolean,
  ): THREE.Color {
    if (isStalled && inWake) {
      return COLOR_RED;
    }
    if (velocityRatio < 0.82) {
      const t = Math.max(0, velocityRatio / 0.82);
      return new THREE.Color().lerpColors(COLOR_BLUE, COLOR_CYAN, t);
    } else if (velocityRatio < 1.05) {
      const t = (velocityRatio - 0.82) / 0.23;
      return new THREE.Color().lerpColors(COLOR_CYAN, COLOR_GREEN, t);
    } else if (velocityRatio < 1.35) {
      const t = (velocityRatio - 1.05) / 0.3;
      return new THREE.Color().lerpColors(COLOR_GREEN, COLOR_YELLOW, t);
    } else {
      const t = Math.min(1, (velocityRatio - 1.35) / 0.35);
      return new THREE.Color().lerpColors(COLOR_YELLOW, COLOR_RED, t);
    }
  }

  function initWindStreamlines() {
    seeds = [];
    const cols = 10;
    const rows = 8;
    for (let r = 0; r < rows; r++) {
      for (let c = 0; c < cols; c++) {
        const x = -0.45 + (c / (cols - 1)) * 0.9;
        const y = -0.16 + (r / (rows - 1)) * 0.32;
        seeds.push({
          x,
          y,
          speedOffset: Math.random() * 0.2,
        });
      }
    }

    const lineGeo = new THREE.BufferGeometry();
    linePositions = new Float32Array(TOTAL_VERTICES * 3);
    lineColors = new Float32Array(TOTAL_VERTICES * 3);

    lineGeo.setAttribute(
      "position",
      new THREE.BufferAttribute(linePositions, 3),
    );
    lineGeo.setAttribute("color", new THREE.BufferAttribute(lineColors, 3));

    const lineMat = new THREE.LineBasicMaterial({
      vertexColors: true,
      transparent: true,
      opacity: 0.65,
      linewidth: 1.5,
      blending: THREE.AdditiveBlending,
    });

    lineSegmentsMesh = new THREE.LineSegments(lineGeo, lineMat);
    scene.add(lineSegmentsMesh);

    const pGeo = new THREE.BufferGeometry();
    particlePositions = new Float32Array(PARTICLE_COUNT * 3);
    particleColors = new Float32Array(PARTICLE_COUNT * 3);
    particleProgress = new Float32Array(PARTICLE_COUNT);
    particleStreamId = new Int32Array(PARTICLE_COUNT);

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      particleStreamId[i] = Math.floor(Math.random() * STREAMLINE_COUNT);
      particleProgress[i] = Math.random();
    }

    pGeo.setAttribute(
      "position",
      new THREE.BufferAttribute(particlePositions, 3),
    );
    pGeo.setAttribute("color", new THREE.BufferAttribute(particleColors, 3));

    const pMat = new THREE.PointsMaterial({
      size: 0.011,
      vertexColors: true,
      transparent: true,
      opacity: 0.92,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    particlePoints = new THREE.Points(pGeo, pMat);
    scene.add(particlePoints);
  }

  function updateWindStreamlines(dt: number) {
    if (!lineSegmentsMesh || seeds.length === 0) return;

    const radAoA = (currentAoA * Math.PI) / 180;
    const isStalled = currentAoA >= 15;
    const isNearStall = currentAoA >= 12;

    const baseVelocity = 0.65;
    const startZ = -0.55;
    const endZ = 0.55;
    const zStep = (endZ - startZ) / (POINTS_PER_LINE - 1);

    let segIdx = 0;

    const streamCurves: THREE.Vector3[][] = [];
    const streamColors: THREE.Color[][] = [];

    const wingY = wingCenter.y + 0.02;

    for (let s = 0; s < STREAMLINE_COUNT; s++) {
      const seed = seeds[s];
      let currentX = seed.x;
      let seedY = seed.y;

      const curvePoints: THREE.Vector3[] = [];
      const curveColors: THREE.Color[] = [];

      for (let p = 0; p < POINTS_PER_LINE; p++) {
        const currentZ = startZ + p * zStep;

        const relZ = currentZ - wingCenter.z;
        const relY = seedY - wingY;
        const distTotal = Math.sqrt(
          currentX * currentX + relY * relY + relZ * relZ,
        );

        let localVel = baseVelocity;
        let dy = 0;
        let dx = 0;

        if (distTotal < 0.35) {
          const influence = Math.max(0, 1 - distTotal / 0.35);
          const chordPhase = Math.sin((relZ + 0.15) * Math.PI * 2.5);
          if (relY < 0) {
            dy -=
              influence *
              0.1 *
              Math.max(0, chordPhase) *
              Math.cos(radAoA * 0.5);
            localVel +=
              baseVelocity * influence * 0.58 * Math.max(0.1, Math.cos(radAoA));
          } else {
            dy += influence * 0.06 * Math.max(0, chordPhase);
            localVel -= baseVelocity * influence * 0.28;
          }
          if (relZ > 0.05) {
            dy -= Math.sin(radAoA * 0.75) * influence * 0.22 * (relZ - 0.05);
            if (Math.abs(currentX) > 0.35) {
              const tipSign = Math.sign(currentX);
              const vortexAngle = flowTime * 10 + relZ * 15;
              dx += tipSign * Math.sin(vortexAngle) * 0.03 * influence;
              dy += Math.cos(vortexAngle) * 0.03 * influence;
              localVel += baseVelocity * 0.25 * influence;
            }

            if (isStalled) {
              const phase = flowTime * 9 + s * 0.4 + p * 0.25;
              dy += Math.sin(phase) * 0.07 * influence;
              dx += Math.cos(phase * 1.4) * 0.06 * influence;
              localVel *= 0.6;
            } else if (isNearStall) {
              dy += Math.sin(flowTime * 5 + p) * 0.02 * influence;
            }
          }
        }

        const ptX = currentX + dx;
        const ptY = seedY + dy;
        const ptZ = currentZ;

        const pt = new THREE.Vector3(ptX, ptY, ptZ);
        curvePoints.push(pt);

        const velocityRatio = localVel / baseVelocity;
        const inWake = relZ > 0.05 && distTotal < 0.35;
        const col = getF1CFDColor(velocityRatio, isStalled, inWake);
        curveColors.push(col);
      }

      streamCurves.push(curvePoints);
      streamColors.push(curveColors);

      for (let p = 0; p < POINTS_PER_LINE - 1; p++) {
        const p1 = curvePoints[p];
        const p2 = curvePoints[p + 1];
        const c1 = curveColors[p];
        const c2 = curveColors[p + 1];

        const v3 = segIdx * 3;
        linePositions[v3] = p1.x;
        linePositions[v3 + 1] = p1.y;
        linePositions[v3 + 2] = p1.z;

        lineColors[v3] = c1.r;
        lineColors[v3 + 1] = c1.g;
        lineColors[v3 + 2] = c1.b;

        const v3_next = (segIdx + 1) * 3;
        linePositions[v3_next] = p2.x;
        linePositions[v3_next + 1] = p2.y;
        linePositions[v3_next + 2] = p2.z;

        lineColors[v3_next] = c2.r;
        lineColors[v3_next + 1] = c2.g;
        lineColors[v3_next + 2] = c2.b;

        segIdx += 2;
      }
    }

    lineSegmentsMesh.geometry.attributes.position.needsUpdate = true;
    lineSegmentsMesh.geometry.attributes.color.needsUpdate = true;

    for (let i = 0; i < PARTICLE_COUNT; i++) {
      const sId = particleStreamId[i];
      let prog = particleProgress[i] + dt * (0.5 + seeds[sId].speedOffset);
      if (prog >= 1) {
        prog = 0;
        particleStreamId[i] = Math.floor(Math.random() * STREAMLINE_COUNT);
      }
      particleProgress[i] = prog;

      const curve = streamCurves[sId];
      const cols = streamColors[sId];

      if (curve && curve.length > 0) {
        const exactIdx = prog * (POINTS_PER_LINE - 1);
        const idx0 = Math.floor(exactIdx);
        const idx1 = Math.min(POINTS_PER_LINE - 1, idx0 + 1);
        const alpha = exactIdx - idx0;

        const p0 = curve[idx0];
        const p1 = curve[idx1];
        const c0 = cols[idx0];
        const c1 = cols[idx1];

        const pi3 = i * 3;
        particlePositions[pi3] = THREE.MathUtils.lerp(p0.x, p1.x, alpha);
        particlePositions[pi3 + 1] = THREE.MathUtils.lerp(p0.y, p1.y, alpha);
        particlePositions[pi3 + 2] = THREE.MathUtils.lerp(p0.z, p1.z, alpha);

        particleColors[pi3] = THREE.MathUtils.lerp(c0.r, c1.r, alpha);
        particleColors[pi3 + 1] = THREE.MathUtils.lerp(c0.g, c1.g, alpha);
        particleColors[pi3 + 2] = THREE.MathUtils.lerp(c0.b, c1.b, alpha);
      }
    }

    particlePoints.geometry.attributes.position.needsUpdate = true;
    particlePoints.geometry.attributes.color.needsUpdate = true;
  }

  function resize() {
    if (!container || !renderer || !camera) return;
    const w = container.clientWidth;
    const h = container.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }

  function fitCamera(model: THREE.Object3D) {
    const box = new THREE.Box3().setFromObject(model);
    const size = box.getSize(new THREE.Vector3()).length();
    const centre = box.getCenter(new THREE.Vector3());
    controls.target.copy(centre);
    camera.near = size / 100;
    camera.far = size * 100;
    camera.position
      .copy(centre)
      .add(new THREE.Vector3(0.55, size * 0.22, size * 0.65));
    camera.updateProjectionMatrix();
    controls.update();
  }
</script>

<!-- Canvas only — no decorative text above/below -->
<div bind:this={container} class="spoiler-canvas-wrap">
  <canvas bind:this={canvas}></canvas>

  {#if loading}
    <div class="spoiler-overlay">
      <span class="spoiler-spinner"></span>
      <span class="spoiler-overlay-text">LOADING MODEL…</span>
    </div>
  {/if}

  {#if loadError}
    <div class="spoiler-overlay">
      <span class="spoiler-overlay-text" style="color: #D9584F;"
        >MODEL ERROR</span
      >
    </div>
  {/if}

  <!-- Corner accents -->
  <span class="sv-corner sv-tl"></span>
  <span class="sv-corner sv-tr"></span>
  <span class="sv-corner sv-bl"></span>
  <span class="sv-corner sv-br"></span>
</div>

<style>
  .spoiler-canvas-wrap {
    position: relative;
    width: min(800px, 92vw);
    height: 420px;
    border: 1px solid rgba(127, 166, 179, 0.3);
    background: rgba(10, 13, 17, 0.03);
    overflow: hidden;
  }

  @media (min-width: 640px) {
    .spoiler-canvas-wrap {
      height: 480px;
    }
  }

  .spoiler-canvas-wrap canvas {
    display: block;
    width: 100%;
    height: 100%;
  }

  /* ── Loading / error overlay ── */
  .spoiler-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 10px;
    background: rgba(244, 246, 248, 0.6);
    backdrop-filter: blur(4px);
  }

  .spoiler-overlay-text {
    font-family: "IBM Plex Mono", monospace;
    font-size: 10px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: rgba(10, 13, 17, 0.45);
  }

  .spoiler-spinner {
    display: block;
    width: 20px;
    height: 20px;
    border: 1.5px solid rgba(127, 166, 179, 0.25);
    border-top-color: #7fa6b3;
    border-radius: 50%;
    animation: sv-spin 0.8s linear infinite;
  }

  @keyframes sv-spin {
    to {
      transform: rotate(360deg);
    }
  }

  /* ── Corner accents ── */
  .sv-corner {
    position: absolute;
    width: 10px;
    height: 10px;
    border: 1px solid rgba(127, 166, 179, 0.45);
  }
  .sv-tl {
    top: 0;
    left: 0;
    border-right: none;
    border-bottom: none;
  }
  .sv-tr {
    top: 0;
    right: 0;
    border-left: none;
    border-bottom: none;
  }
  .sv-bl {
    bottom: 0;
    left: 0;
    border-right: none;
    border-top: none;
  }
  .sv-br {
    bottom: 0;
    right: 0;
    border-left: none;
    border-top: none;
  }
</style>
