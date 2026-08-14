<script lang="ts">
  import { onMount } from "svelte";
  import * as THREE from "three";
  import { GLTFLoader } from "three/examples/jsm/loaders/GLTFLoader.js";
  import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

  let container: HTMLDivElement;
  let canvas: HTMLCanvasElement;
  let loading = $state(true);
  let loadError = $state(false);

  let renderer: THREE.WebGLRenderer;
  let scene: THREE.Scene;
  let camera: THREE.PerspectiveCamera;
  let controls: OrbitControls;
  let animFrameId: number;

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
    camera = new THREE.PerspectiveCamera(45, w / h, 0.01, 100);
    camera.position.set(0, 0.15, 0.6);

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
    controls.autoRotateSpeed = 1.4;
    controls.target.set(0, 0, 0);

    const stopAutoRotate = () => {
      controls.autoRotate = false;
      canvas.removeEventListener("pointerdown", stopAutoRotate);
    };
    canvas.addEventListener("pointerdown", stopAutoRotate);

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
        const scale = 0.9 / maxDim;

        model.position.sub(centre.multiplyScalar(scale));
        model.scale.setScalar(scale);
        model.rotation.x = -Math.PI / 2;

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
    const loop = () => {
      animFrameId = requestAnimationFrame(loop);
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
      .add(new THREE.Vector3(0, size * 0.25, size * 0.65));
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
