import re

with open('/Users/rgraham/beltinator-app/index.html', 'r') as f:
    content = f.read()

# ── 1. Add Stream Output + IGLOO panel section ──────────────────────────────
old_ui = (
    '    <div class="legend-item" onclick="focusSatByName(\'Lomonosov\')"><div class="legend-dot" style="background:#a855f7;"></div>Lomonosov</div>\n'
    '  </div>\n'
    '\n'
    '</div>\n'
    '\n'
    '<!-- Right Info Panel -->'
)
new_ui = (
    '    <div class="legend-item" onclick="focusSatByName(\'Lomonosov\')"><div class="legend-dot" style="background:#a855f7;"></div>Lomonosov</div>\n'
    '  </div>\n'
    '\n'
    '  <div class="panel-section">\n'
    '    <div class="section-header">Output / Streaming</div>\n'
    '    <div class="btn-group" style="flex-direction:column;gap:6px;">\n'
    '      <button class="btn" onclick="openStreamWindow()" title="Open canvas stream for OBS / NDI / Spout capture">&#128225; Stream Output</button>\n'
    '      <button class="btn" id="igloo-toggle-btn" onclick="toggleIglooMode()" title="Toggle IGLOO 6-face cubemap mode (also: press I)">&#9645; IGLOO Cubemap</button>\n'
    '    </div>\n'
    '    <div style="margin-top:8px;font-size:9px;color:var(--text-dim);line-height:1.5;">\n'
    '      Stream Output opens a clean popup.<br>\n'
    '      Capture in <strong style="color:var(--accent-cyan);">OBS</strong> &rarr; output via\n'
    '      <strong style="color:var(--accent-cyan);">NDI</strong> (OBS-NDI plugin) or\n'
    '      <strong style="color:var(--accent-cyan);">Spout</strong> (obs-spout2 plugin).\n'
    '    </div>\n'
    '  </div>\n'
    '\n'
    '</div>\n'
    '\n'
    '<!-- Right Info Panel -->'
)

if old_ui in content:
    content = content.replace(old_ui, new_ui, 1)
    print('UI panel section inserted OK')
else:
    print('ERROR: UI anchor not found')

# ── 2. Replace destroyIglooMode + keyboard handler block ────────────────────
old_js = (
    'function destroyIglooMode() {\n'
    '  const el = document.getElementById(\'igloo-faces\');\n'
    '  if (el) el.remove();\n'
    '  iglooFaceCanvases = [];\n'
    '}\n'
    '\n'
    'document.addEventListener(\'keydown\', (e) => {\n'
    '  if (e.key === \'i\' || e.key === \'I\') {\n'
    '    iglooMode = !iglooMode;\n'
    '    if (iglooMode && !cubeCamera) initIglooMode();\n'
    '    if (!iglooMode) destroyIglooMode();\n'
    '    const el = document.getElementById(\'fps-counter\');\n'
    '    if (el) el.textContent = iglooMode ? \'IGLOO Cubemap\' : \'Rendering\';\n'
    '    console.log(`IGLOO mode: ${iglooMode ? \'ON \u2014 press I again to exit\' : \'OFF\'}`);\n'
    '  }\n'
    '});'
)
new_js = (
    'function destroyIglooMode() {\n'
    '  const el = document.getElementById(\'igloo-faces\');\n'
    '  if (el) el.remove();\n'
    '  iglooFaceCanvases = [];\n'
    '}\n'
    '\n'
    '// ── Cube face extraction for IGLOO / NDI / Spout output ──────────────\n'
    'const _faceScene = new THREE.Scene();\n'
    'const _faceCam = new THREE.OrthographicCamera(-1, 1, 1, -1, 0, 1);\n'
    'const _faceMat = new THREE.ShaderMaterial({\n'
    '  uniforms: { tCube: { value: null }, face: { value: 0 } },\n'
    '  vertexShader: `varying vec2 vUv; void main(){ vUv=uv; gl_Position=vec4(position,1.0); }`,\n'
    '  fragmentShader: [\n'
    '    "uniform samplerCube tCube; uniform int face; varying vec2 vUv;",\n'
    '    "void main(){",\n'
    '    "  vec2 uv=vUv*2.0-1.0; vec3 dir;",\n'
    '    "  if(face==0)      dir=vec3( 1.0,-uv.y,-uv.x);",\n'
    '    "  else if(face==1) dir=vec3(-1.0,-uv.y, uv.x);",\n'
    '    "  else if(face==2) dir=vec3( uv.x, 1.0, uv.y);",\n'
    '    "  else if(face==3) dir=vec3( uv.x,-1.0,-uv.y);",\n'
    '    "  else if(face==4) dir=vec3( uv.x,-uv.y, 1.0);",\n'
    '    "  else             dir=vec3(-uv.x,-uv.y,-1.0);",\n'
    '    "  gl_FragColor=textureCube(tCube,normalize(dir));",\n'
    '    "}"\n'
    '  ].join("\\n"),\n'
    '});\n'
    '_faceScene.add(new THREE.Mesh(new THREE.PlaneGeometry(2,2), _faceMat));\n'
    'const _faceTarget = new THREE.WebGLRenderTarget(256, 256);\n'
    'const _facePixels = new Uint8Array(256*256*4);\n'
    '\n'
    'function extractCubeFaces() {\n'
    '  if (!cubeRenderTarget || !iglooFaceCanvases.length) return;\n'
    '  _faceMat.uniforms.tCube.value = cubeRenderTarget.texture;\n'
    '  for (let i = 0; i < 6; i++) {\n'
    '    _faceMat.uniforms.face.value = i;\n'
    '    renderer.setRenderTarget(_faceTarget);\n'
    '    renderer.render(_faceScene, _faceCam);\n'
    '    renderer.readRenderTargetPixels(_faceTarget, 0, 0, 256, 256, _facePixels);\n'
    '    renderer.setRenderTarget(null);\n'
    '    const ctx = iglooFaceCanvases[i].getContext(\'2d\');\n'
    '    const img = new ImageData(256, 256);\n'
    '    for (let r = 0; r < 256; r++) {\n'
    '      const src = (255-r)*256*4;\n'
    '      img.data.set(_facePixels.subarray(src, src+256*4), r*256*4);\n'
    '    }\n'
    '    ctx.putImageData(img, 0, 0);\n'
    '  }\n'
    '}\n'
    '\n'
    '// ── Stream Output (canvas.captureStream -> popup for OBS/NDI/Spout) ──\n'
    'function openStreamWindow() {\n'
    '  const stream = renderer.domElement.captureStream(60);\n'
    '  const win = window.open(\'\', \'BeltinatStream\',\n'
    '    "width="+window.screen.width+",height="+window.screen.height+",toolbar=0,menubar=0,location=0");\n'
    '  if (!win) { alert(\'Popup blocked \u2014 allow popups for this site.\'); return; }\n'
    '  win.document.write(\'<!DOCTYPE html><html><head><title>Beltinator Stream<\\/title>\'\n'
    '    +\'<style>*{margin:0;padding:0;}body{background:#000;}video{width:100vw;height:100vh;object-fit:contain;}<\\/style>\'\n'
    '    +\'<\\/head><body><video id="v" autoplay muted playsinline><\\/video><\\/body><\\/html>\');\n'
    '  win.document.close();\n'
    '  win.document.getElementById(\'v\').srcObject = stream;\n'
    '}\n'
    '\n'
    'function toggleIglooMode() {\n'
    '  iglooMode = !iglooMode;\n'
    '  if (iglooMode && !cubeCamera) initIglooMode();\n'
    '  if (!iglooMode) destroyIglooMode();\n'
    '  const fpsel = document.getElementById(\'fps-counter\');\n'
    '  if (fpsel) fpsel.textContent = iglooMode ? \'IGLOO Cubemap\' : \'Rendering\';\n'
    '  const btn = document.getElementById(\'igloo-toggle-btn\');\n'
    '  if (btn) btn.classList.toggle(\'active\', iglooMode);\n'
    '}\n'
    '\n'
    'document.addEventListener(\'keydown\', (e) => {\n'
    '  if (e.key === \'i\' || e.key === \'I\') toggleIglooMode();\n'
    '});'
)

if old_js in content:
    content = content.replace(old_js, new_js, 1)
    print('JS section replaced OK')
else:
    print('ERROR: JS anchor not found')

# ── 3. Wire extractCubeFaces() into the animate loop ────────────────────────
old_animate = (
    '    // For IGLOO: pipe each face to a projector via Spout/NDI\n'
    '    // Access individual faces: cubeRenderTarget.texture (CubeTexture with 6 images)\n'
    '    // To extract faces to canvases for projection mapping, see extractCubeFaces() below\n'
    '  }'
)
new_animate = (
    '    extractCubeFaces(); // copy faces to preview canvases (captureStream-able for NDI/Spout)\n'
    '  }'
)

if old_animate in content:
    content = content.replace(old_animate, new_animate, 1)
    print('Animate IGLOO block updated OK')
else:
    print('ERROR: animate IGLOO anchor not found')

with open('/Users/rgraham/beltinator-app/index.html', 'w') as f:
    f.write(content)

print('All done.')

