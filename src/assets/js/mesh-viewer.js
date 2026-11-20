// Interactive mesh viewer for the Examples page: shaded / wireframe / both, with live readouts.
// Each viewer is an element with [data-mesh-viewer] and data-src; three.js is only fetched
// once a viewer scrolls into view. three.js is self-hosted (see eleventy.config.js); the page's
// import map points the bare 'three' specifier at the same copy the loaders import.
const THREE_URL = '/assets/vendor/three-0.160.0';

const roots = document.querySelectorAll('[data-mesh-viewer]');

function cssColor(name, fallback) {
    const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return v || fallback;
}

async function start(root) {
    const [THREE, { GLTFLoader }, { DRACOLoader }, { OrbitControls }] = await Promise.all([
        import('three'),
        import(`${THREE_URL}/examples/jsm/loaders/GLTFLoader.js`),
        import(`${THREE_URL}/examples/jsm/loaders/DRACOLoader.js`),
        import(`${THREE_URL}/examples/jsm/controls/OrbitControls.js`),
    ]);

    const canvasHost = root.querySelector('[data-canvas]');
    const status = root.querySelector('[data-status]');
    const readout = root.querySelector('[data-readout]');
    const buttons = root.querySelectorAll('[data-mode]');
    const unitScale = parseFloat(root.dataset.unitScale || '1');

    let renderer;
    try {
        renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    } catch (e) {
        throw new Error('WebGL is not available in this browser');
    }
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    canvasHost.appendChild(renderer.domElement);

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(35, 1, 0.001, 100);
    scene.add(new THREE.HemisphereLight(0xffffff, 0x445066, 1.6));
    const key = new THREE.DirectionalLight(0xffffff, 2.2);
    key.position.set(2, 3, 2);
    scene.add(key);
    const rim = new THREE.DirectionalLight(0x9fe8ff, 1.0);
    rim.position.set(-3, 1, -2);
    scene.add(rim);

    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.autoRotate = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    controls.autoRotateSpeed = 1.2;
    controls.addEventListener('start', () => { controls.autoRotate = false; });

    function resize() {
        const w = canvasHost.clientWidth, h = canvasHost.clientHeight;
        renderer.setSize(w, h, false);
        camera.aspect = w / h;
        camera.updateProjectionMatrix();
    }
    new ResizeObserver(resize).observe(canvasHost);
    resize();

    const draco = new DRACOLoader();
    draco.setDecoderPath(`${THREE_URL}/examples/jsm/libs/draco/gltf/`);
    const loader = new GLTFLoader();
    loader.setDRACOLoader(draco);

    const wireMat = new THREE.MeshBasicMaterial({ wireframe: true, transparent: true, opacity: 0.4, depthWrite: false });
    const shaded = [];
    const wires = [];

    function applyWireColor() {
        wireMat.color.set(cssColor('--color-primary', '#22d3ee'));
    }
    applyWireColor();
    new MutationObserver(applyWireColor).observe(document.documentElement, { attributes: true, attributeFilter: ['data-theme'] });

    function setMode(mode) {
        buttons.forEach((b) => {
            const on = b.dataset.mode === mode;
            b.classList.toggle('btn-active', on);
            b.setAttribute('aria-pressed', String(on));
        });
        shaded.forEach((m) => { m.visible = mode !== 'wireframe'; });
        wires.forEach((m) => { m.visible = mode !== 'shaded'; });
        wireMat.opacity = mode === 'wireframe' ? 0.22 : 0.1;
    }
    buttons.forEach((b) => b.addEventListener('click', () => setMode(b.dataset.mode)));

    const gltf = await loader.loadAsync(root.dataset.src, (e) => {
        if (e.lengthComputable && status) status.textContent = `Loading ${Math.round((e.loaded / e.total) * 100)}%`;
    });
    const model = gltf.scene;
    scene.add(model);

    let tris = 0;
    const meshes = [];
    model.traverse((o) => { if (o.isMesh) meshes.push(o); });
    meshes.forEach((m) => {
        const g = m.geometry;
        tris += (g.index ? g.index.count : g.attributes.position.count) / 3;
        shaded.push(m);
        const w = new THREE.Mesh(g, wireMat);
        w.renderOrder = 1;
        // sibling, not child: hiding the shaded mesh must not hide its wireframe
        w.position.copy(m.position);
        w.quaternion.copy(m.quaternion);
        w.scale.copy(m.scale);
        m.parent.add(w);
        wires.push(w);
    });

    const box = new THREE.Box3().setFromObject(model);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    model.position.sub(center);
    const radius = size.length() / 2;
    const dist = radius / Math.sin((camera.fov * Math.PI) / 360) * 0.72;
    camera.position.set(dist * 0.6, dist * 0.45, dist * 0.8);
    camera.near = radius / 100;
    camera.far = radius * 100;
    camera.updateProjectionMatrix();
    controls.target.set(0, 0, 0);
    controls.minDistance = radius * 0.4;
    controls.maxDistance = dist * 3;
    controls.update();

    if (readout) {
        const dims = [size.x, size.y, size.z].map((v) => v * unitScale).sort((a, b) => b - a);
        readout.textContent = `${dims.map((v) => v.toFixed(1)).join(' × ')} mm · ${Math.round(tris).toLocaleString('en-US')} triangles`;
    }
    if (status) status.remove();
    setMode('shaded');

    let visible = true;
    new IntersectionObserver((entries) => { visible = entries[0].isIntersecting; }).observe(root);
    renderer.setAnimationLoop(() => {
        if (!visible) return;
        controls.update();
        renderer.render(scene, camera);
    });
}

const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
        if (!e.isIntersecting) return;
        io.unobserve(e.target);
        start(e.target).catch((err) => {
            console.error(err);
            const s = e.target.querySelector('[data-status]');
            if (s) s.textContent = `Could not load the 3D viewer (${(err && err.message) || 'unknown error'}).`;
        });
    });
}, { rootMargin: '200px' });
roots.forEach((r) => io.observe(r));
