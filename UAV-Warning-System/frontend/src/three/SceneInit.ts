import * as THREE from "three";
import { OrbitControls } from "three/examples/jsm/controls/OrbitControls.js";

export class SceneInit {
  public readonly scene: THREE.Scene;
  private readonly camera: THREE.PerspectiveCamera;
  private readonly renderer: THREE.WebGLRenderer;
  private readonly controls: OrbitControls;
  private readonly container: HTMLElement;
  private readonly raycaster = new THREE.Raycaster();
  private readonly ndc = new THREE.Vector2();
  private readonly groundPlane = new THREE.Plane(new THREE.Vector3(0, 0, 1), 0);
  private groundClickHandler: ((point: { x: number; y: number }) => void) | null = null;
  private autoFocusTarget: THREE.Vector3 | null = null;

  constructor(container: HTMLElement) {
    this.container = container;

    // Use Z-up world to align with backend [x, y, z]
    THREE.Object3D.DEFAULT_UP.set(0, 0, 1);

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0xcfd8e3);
    this.scene.fog = new THREE.Fog(0xcfd8e3, 180, 380);

    this.camera = new THREE.PerspectiveCamera(
      46,
      container.clientWidth / Math.max(1, container.clientHeight),
      1,
      600
    );
    this.camera.up.set(0, 0, 1);
    this.camera.position.set(74, -68, 54);
    this.camera.lookAt(0, 0, 10);

    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(container.clientWidth, Math.max(1, container.clientHeight));
    this.renderer.shadowMap.enabled = false;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(this.renderer.domElement);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enabled = true;
    this.controls.enablePan = true;
    this.controls.enableRotate = true;
    this.controls.enableZoom = true;
    this.controls.enableDamping = true;
    this.controls.dampingFactor = 0.08;
    this.controls.minDistance = 34;
    this.controls.maxDistance = 180;
    this.controls.minPolarAngle = 0.25;
    this.controls.maxPolarAngle = Math.PI / 2 - 0.06;
    this.controls.target.set(0, 0, 10);

    this.setupLights();
    this.handleResize = this.handleResize.bind(this);
    this.handlePointerDown = this.handlePointerDown.bind(this);

    window.addEventListener("resize", this.handleResize);
    this.renderer.domElement.addEventListener("pointerdown", this.handlePointerDown);
  }

  setGroundClickHandler(handler: ((point: { x: number; y: number }) => void) | null): void {
    this.groundClickHandler = handler;
  }

  setNavigationEnabled(enabled: boolean): void {
    this.controls.enabled = enabled;
  }

  setAutoFocusPoints(points: Array<[number, number, number]>): void {
    if (points.length === 0) {
      this.autoFocusTarget = null;
      return;
    }
    let sumX = 0;
    let sumY = 0;
    let sumZ = 0;
    for (const [x, y, z] of points) {
      sumX += x;
      sumY += y;
      sumZ += z;
    }
    const inv = 1 / points.length;
    const centerX = sumX * inv;
    const centerY = sumY * inv;
    const centerZ = sumZ * inv;
    this.autoFocusTarget = new THREE.Vector3(centerX, centerY, Math.max(8, centerZ * 0.5 + 6));
  }

  render(): void {
    if (this.autoFocusTarget) {
      this.controls.target.lerp(this.autoFocusTarget, 0.09);
    }
    if (this.camera.position.z < 5.5) {
      this.camera.position.z = 5.5;
    }
    if (this.controls.target.z < 0) {
      this.controls.target.z = 0;
    }
    this.controls.update();
    this.renderer.render(this.scene, this.camera);
  }

  dispose(): void {
    window.removeEventListener("resize", this.handleResize);
    this.renderer.domElement.removeEventListener("pointerdown", this.handlePointerDown);
    this.controls.dispose();
    this.renderer.dispose();
    if (this.renderer.domElement.parentElement === this.container) {
      this.container.removeChild(this.renderer.domElement);
    }
  }

  private setupLights(): void {
    const hemi = new THREE.HemisphereLight(0xeef6ff, 0xa5a5a5, 0.9);
    this.scene.add(hemi);

    const sun = new THREE.DirectionalLight(0xffffff, 0.95);
    sun.position.set(180, -120, 220);
    this.scene.add(sun);

    const fill = new THREE.DirectionalLight(0xe8f1ff, 0.38);
    fill.position.set(-120, 100, 80);
    this.scene.add(fill);
  }

  private handlePointerDown(event: PointerEvent): void {
    if (!this.groundClickHandler) {
      return;
    }
    const rect = this.renderer.domElement.getBoundingClientRect();
    this.ndc.x = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    this.ndc.y = -((event.clientY - rect.top) / rect.height) * 2 + 1;

    this.raycaster.setFromCamera(this.ndc, this.camera);
    const hit = new THREE.Vector3();
    const intersects = this.raycaster.ray.intersectPlane(this.groundPlane, hit);
    if (!intersects) {
      return;
    }
    this.groundClickHandler({
      x: Number(hit.x.toFixed(2)),
      y: Number(hit.y.toFixed(2)),
    });
  }

  private handleResize(): void {
    const width = this.container.clientWidth;
    const height = Math.max(1, this.container.clientHeight);
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height);
  }
}
