with open('/Users/rgraham/beltinator-app/index.html', 'r') as f:
    content = f.read()

# ── 1. Add equirect stream button to UI ──────────────────────────────
old_ui = (
    '      <button class="btn" id="igloo-toggle-btn" onclick="toggleIglooMode()"'
    ' title="Toggle IGLOO 6-face cubemap mode (also: press I)">&#9645; IGLOO Cubemap</button>\n'
    '    </div>'
)
new_ui = (
    '      <button class="btn" id="igloo-toggle-btn" onclick="toggleIglooMode()"'
    ' title="Toggle IGLOO 6-face cubemap mode (also: press I)">&#9645; IGLOO Cubemap</button>\n'
    '      <button class="btn" id="equirect-stream-btn" onclick="openEquirectStream()"'
    ' title="Stream equirectangular 360 output for IGLOO Core Engine NDI input">&#9678; Equirect Stream (IGLOO)</button>\n'
    '    </div>'
)
if old_ui in content:
    content = content.replace(old_ui, new_ui, 1)
    print('UI button inserted OK')
else:
    print('ERROR: UI anchor not found')

# ── 2. Wire renderEquirect() into the animate loop after extractCubeFaces ──
old_anim = 'extractCubeFaces(); // copy faces to preview canvases (captureStream-able for NDI/Spout)'
new_anim = ('extractCubeFaces(); // copy faces to preview canvases (captureStream-able for NDI/Spout)\n'
            '    renderEquirect();  // update equirect canvas for IGLOO NDI stream')
if old_anim in content:
    content = content.replace(old_anim, new_anim, 1)
    print('Animate loop updated OK')
else:
    print('ERROR: animate anchor not found')

# ── 3. Insert equirect shader + openEquirectStream() before toggleIglooMode ──
equirect_js = r"""
// ── Equirectangular output for IGLOO NDI streaming ───────────────────
// Renders the cubemap to a 2:1 lat-long canvas that OBS can capture and
// output as NDI — IGLOO Core Engine then applies its projector mapping.
const EQUIRECT_W = 2048, EQUIRECT_H = 1024;
const _equiScene = new THREE.Scene();
const _equiCam   = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);
const _equiMat   = new THREE.ShaderMaterial({
  uniforms: { tCube: { value: null } },
  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=vec4(position,1.0); }`,
  fragmentShader: [
    "uniform samplerCube tCube; varying vec2 vUv;",
    "#define PI 3.14159265358979323846",
    "void main(){",
    "  float lon = (vUv.x) * 2.0 * PI - PI;",   // -PI .. PI
    "  float lat = (vUv.y - 0.5) * PI;",          // -PI/2 .. PI/2
    "  vec3 dir = vec3(cos(lat)*sin(lon), sin(lat), cos(lat)*cos(lon));",
    "  gl_FragColor = textureCube(tCube, normalize(dir));",
    "}"
  ].join("\n"),
});
_equiScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2, 2), _equiMat));
const _equiTarget = new THREE.WebGLRenderTarget(EQUIRECT_W, EQUIRECT_H);
const _equiPixels = new Uint8Array(EQUIRECT_W * EQUIRECT_H * 4);
let _equiCanvas = null;

function renderEquirect() {
  if (!cubeRenderTarget || !_equiCanvas) return;
  _equiMat.uniforms.tCube.value = cubeRenderTarget.texture;
  renderer.setRenderTarget(_equiTarget);
  renderer.render(_equiScene, _equiCam);
  renderer.readRenderTargetPixels(_equiTarget, 0, 0, EQUIRECT_W, EQUIRECT_H, _equiPixels);
  renderer.setRenderTarget(null);
  const ctx = _equiCanvas.getContext('2d');
  const img = new ImageData(EQUIRECT_W, EQUIRECT_H);
  for (let r = 0; r < EQUIRECT_H; r++) {
    const src = (EQUIRECT_H - 1 - r) * EQUIRECT_W * 4; // flip Y (WebGL origin bottom-left)
    img.data.set(_facePixels.subarray ? _equiPixels.subarray(src, src + EQUIRECT_W * 4)
                                      : _equiPixels.slice(src, src + EQUIRECT_W * 4), r * EQUIRECT_W * 4);
  }
  ctx.putImageData(img, 0, 0);
}

function openEquirectStream() {
  if (!iglooMode) {
    if (!confirm('IGLOO Cubemap mode is off. Enable it now?')) return;
    toggleIglooMode();
  }
  _equiCanvas = document.createElement('canvas');
  _equiCanvas.width  = EQUIRECT_W;
  _equiCanvas.height = EQUIRECT_H;
  const stream = _equiCanvas.captureStream(30);
  const win = window.open('', 'BeltinatEquirect',
    'width=1280,height=640,toolbar=0,menubar=0,location=0,scrollbars=0');
  if (!win) { alert('Popup blocked \u2014 allow popups for this site.'); return; }
  win.document.write('<!DOCTYPE html><html><head><title>Beltinator Equirect \u2014 IGLOO NDI<\/title>'
    + '<style>*{margin:0;padding:0;}body{background:#000;}'
    + 'video{width:100vw;height:100vh;object-fit:contain;}<\/style>'
    + '<\/head><body><video id="v" autoplay muted playsinline><\/video><\/body><\/html>');
  win.document.close();
  win.document.getElementById('v').srcObject = stream;
  const btn = document.getElementById('equirect-stream-btn');
  if (btn) btn.classList.add('active');
}

"""

old_toggle = 'function toggleIglooMode() {'
new_toggle = equirect_js + 'function toggleIglooMode() {'

if old_toggle in content:
    content = content.replace(old_toggle, new_toggle, 1)
    print('Equirect JS inserted OK')
else:
    print('ERROR: toggleIglooMode anchor not found')

with open('/Users/rgraham/beltinator-app/index.html', 'w') as f:
    f.write(content)

print('All done.')

