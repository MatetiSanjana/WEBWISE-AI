import { useEffect, useMemo, useRef } from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'

// Deterministic pseudo-random so the first frame is identical on every load.
function rng(seed) {
  let s = seed >>> 0
  return () => {
    s = (s * 1664525 + 1013904223) >>> 0
    return s / 4294967296
  }
}

const CAM_Z = 9
const FOV = 55
const Z_NEAR = 4 // stars wrap well before the camera (no giant blobs); they also fade out as they approach
const Z_FAR = -46

/** Soft round sprite so points render as gentle stars instead of hard squares. */
function useSoftDot() {
  return useMemo(() => {
    const c = document.createElement('canvas')
    c.width = c.height = 64
    const g = c.getContext('2d')
    const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32)
    grad.addColorStop(0, 'rgba(255,255,255,1)')
    grad.addColorStop(0.3, 'rgba(255,255,255,0.55)')
    grad.addColorStop(1, 'rgba(255,255,255,0)')
    g.fillStyle = grad
    g.fillRect(0, 0, 64, 64)
    const t = new THREE.CanvasTexture(c)
    t.colorSpace = THREE.SRGBColorSpace
    return t
  }, [])
}

/** Crisp star sprite: a small bright core with a short halo (a soft dot would read as a blurry bubble). */
function useStarSprite() {
  return useMemo(() => {
    const c = document.createElement('canvas')
    c.width = c.height = 64
    const g = c.getContext('2d')
    const grad = g.createRadialGradient(32, 32, 0, 32, 32, 32)
    grad.addColorStop(0, 'rgba(255,255,255,1)')
    grad.addColorStop(0.12, 'rgba(255,255,255,0.95)')
    grad.addColorStop(0.32, 'rgba(255,255,255,0.3)')
    grad.addColorStop(1, 'rgba(255,255,255,0)')
    g.fillStyle = grad
    g.fillRect(0, 0, 64, 64)
    const t = new THREE.CanvasTexture(c)
    t.colorSpace = THREE.SRGBColorSpace
    return t
  }, [])
}

/** A procedural wispy cloud (many overlapping soft blobs with a faded edge); tinted per sprite to make nebulae. */
function useCloud() {
  return useMemo(() => {
    const size = 256
    const c = document.createElement('canvas')
    c.width = c.height = size
    const g = c.getContext('2d')
    const r = rng(11)
    for (let i = 0; i < 48; i++) {
      const a = r() * Math.PI * 2
      const d = Math.pow(r(), 0.75) * 88
      const x = size / 2 + Math.cos(a) * d
      const y = size / 2 + Math.sin(a) * d
      const rad = 22 + r() * 54
      const grad = g.createRadialGradient(x, y, 0, x, y, rad)
      const al = 0.05 + r() * 0.1
      grad.addColorStop(0, `rgba(255,255,255,${al})`)
      grad.addColorStop(1, 'rgba(255,255,255,0)')
      g.fillStyle = grad
      g.beginPath()
      g.arc(x, y, rad, 0, Math.PI * 2)
      g.fill()
    }
    g.globalCompositeOperation = 'destination-in' // fade the whole cloud out toward its edge
    const m = g.createRadialGradient(size / 2, size / 2, 36, size / 2, size / 2, size / 2)
    m.addColorStop(0, 'rgba(0,0,0,1)')
    m.addColorStop(1, 'rgba(0,0,0,0)')
    g.fillStyle = m
    g.fillRect(0, 0, size, size)
    const t = new THREE.CanvasTexture(c)
    t.colorSpace = THREE.SRGBColorSpace
    return t
  }, [])
}

const NEBULAE = [
  { pos: [-9, 3.5, -14], scale: 26, color: '#6d34ff', opacity: 0.36, spin: 0.012 },
  { pos: [10, -2.5, -16], scale: 30, color: '#c13bb0', opacity: 0.24, spin: -0.009 },
  { pos: [1, -7, -12], scale: 22, color: '#2f55ff', opacity: 0.3, spin: 0.007 },
  { pos: [-13, -5, -18], scale: 24, color: '#9a6bff', opacity: 0.2, spin: -0.006 },
  { pos: [13, 7, -20], scale: 24, color: '#ff6fb5', opacity: 0.15, spin: 0.005 },
  { pos: [-2, 8, -22], scale: 30, color: '#35c7d8', opacity: 0.09, spin: -0.004 },
]

/** Slowly rotating, drifting clouds of coloured gas far behind the stars. */
function Nebula({ animate }) {
  const cloud = useCloud()
  const refs = useRef([])
  useFrame(({ clock }, dt) => {
    if (!animate) return
    const t = clock.getElapsedTime()
    refs.current.forEach((s, i) => {
      if (!s) return
      s.material.rotation += NEBULAE[i].spin * dt
      s.position.x = NEBULAE[i].pos[0] + Math.sin(t * 0.03 + i) * 1.2
      s.position.y = NEBULAE[i].pos[1] + Math.cos(t * 0.025 + i * 2) * 0.8
    })
  })
  return NEBULAE.map((n, i) => (
    <sprite key={i} ref={(el) => (refs.current[i] = el)} position={n.pos} scale={[n.scale, n.scale, 1]}>
      <spriteMaterial map={cloud} color={n.color} transparent opacity={n.opacity} depthWrite={false} blending={THREE.AdditiveBlending} />
    </sprite>
  ))
}

const STAR_COLORS = ['#ffffff', '#ffffff', '#dcd2ff', '#bfd0ff', '#ffd9f1']
const frustumAt = (z, aspect) => {
  const h = Math.tan((FOV * Math.PI) / 360) * (CAM_Z - z) * 1.12
  return [h * aspect, h]
}

/**
 * A starfield you slowly fly through. Stars drift toward the camera, so near ones sweep outward quickly and distant
 * ones barely move (parallax), which is what gives the sense of depth. Stars re-spawn far away once they pass.
 */
function Stars({ count, size, opacity, speed, seed, twinkle, animate }) {
  const ref = useRef()
  const dot = useStarSprite()
  const { positions, colors, base } = useMemo(() => {
    const r = rng(seed)
    const aspect = 1.8
    const pos = new Float32Array(count * 3)
    const col = new Float32Array(count * 3)
    const tmp = new THREE.Color()
    for (let i = 0; i < count; i++) {
      const z = Z_FAR + r() * (Z_NEAR - Z_FAR)
      const [hw, hh] = frustumAt(z, aspect)
      pos[i * 3] = (r() * 2 - 1) * hw
      pos[i * 3 + 1] = (r() * 2 - 1) * hh
      pos[i * 3 + 2] = z
      tmp.set(STAR_COLORS[Math.floor(r() * STAR_COLORS.length)])
      const k = 0.55 + r() * 0.45 // brightness variety
      col[i * 3] = tmp.r * k
      col[i * 3 + 1] = tmp.g * k
      col[i * 3 + 2] = tmp.b * k
    }
    return { positions: pos, colors: col, base: Float32Array.from(col) }
  }, [count, seed])

  useFrame(({ clock, size: vp }, dt) => {
    if (!animate || !ref.current) return
    const geo = ref.current.geometry
    const attr = geo.attributes.position
    const colAttr = geo.attributes.color
    const a = attr.array
    const col = colAttr.array
    const aspect = vp.width / vp.height
    for (let i = 0; i < count; i++) {
      a[i * 3 + 2] += speed * dt
      if (a[i * 3 + 2] > Z_NEAR) {
        const z = Z_FAR + Math.random() * 4
        const [hw, hh] = frustumAt(z, aspect)
        a[i * 3] = (Math.random() * 2 - 1) * hw
        a[i * 3 + 1] = (Math.random() * 2 - 1) * hh
        a[i * 3 + 2] = z
      }
      // fade in when spawned far away and out when approaching the camera, so nothing pops or becomes a giant blob
      const z = a[i * 3 + 2]
      const fade = Math.min(1, (z - Z_FAR) / 10) * Math.min(1, (Z_NEAR - z) / 9)
      col[i * 3] = base[i * 3] * fade
      col[i * 3 + 1] = base[i * 3 + 1] * fade
      col[i * 3 + 2] = base[i * 3 + 2] * fade
    }
    attr.needsUpdate = true
    colAttr.needsUpdate = true
    ref.current.material.opacity = opacity * (0.8 + 0.2 * Math.sin(clock.getElapsedTime() * twinkle + seed))
  })

  return (
    <points ref={ref} frustumCulled={false}>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
        <bufferAttribute attach="attributes-color" args={[colors, 3]} />
      </bufferGeometry>
      <pointsMaterial map={dot} size={size} vertexColors transparent opacity={opacity} sizeAttenuation depthWrite={false} blending={THREE.AdditiveBlending} />
    </points>
  )
}

/** A rare, brief streak across the sky. Pure decoration; one sprite, stretched and faded. */
function ShootingStar({ animate }) {
  const ref = useRef()
  const dot = useSoftDot()
  const st = useRef({ active: false, t: 0, wait: 5, start: new THREE.Vector3(), dir: new THREE.Vector2(-1, -0.4), angle: 0 })
  useFrame((_, dt) => {
    const s = st.current
    const sp = ref.current
    if (!animate || !sp) return
    if (!s.active) {
      s.wait -= dt
      sp.material.opacity = 0
      if (s.wait <= 0) {
        s.active = true
        s.t = 0
        s.start.set(-4 + Math.random() * 14, 2 + Math.random() * 4.5, -8)
        s.dir.set(-1, -(0.25 + Math.random() * 0.35)).normalize()
        s.angle = Math.atan2(s.dir.y, s.dir.x)
      }
      return
    }
    s.t += dt / 1.1
    if (s.t >= 1) {
      s.active = false
      s.wait = 9 + Math.random() * 9
      sp.material.opacity = 0
      return
    }
    sp.position.set(s.start.x + s.dir.x * s.t * 9, s.start.y + s.dir.y * s.t * 9, s.start.z)
    sp.material.rotation = s.angle
    sp.material.opacity = Math.sin(Math.PI * s.t) * 0.85
  })
  return (
    <sprite ref={ref} scale={[2.6, 0.07, 1]} position={[0, 0, -8]}>
      <spriteMaterial map={dot} color="#f1eaff" transparent opacity={0} depthWrite={false} blending={THREE.AdditiveBlending} />
    </sprite>
  )
}

/** Gentle camera parallax following the pointer (read from a window listener: the canvas itself ignores pointer events). */
function Rig({ animate }) {
  const pointer = useRef({ x: 0, y: 0 })
  useEffect(() => {
    if (!animate) return
    const onMove = (e) => {
      pointer.current.x = (e.clientX / window.innerWidth - 0.5) * 2
      pointer.current.y = (e.clientY / window.innerHeight - 0.5) * 2
    }
    window.addEventListener('pointermove', onMove, { passive: true })
    return () => window.removeEventListener('pointermove', onMove)
  }, [animate])
  useFrame(({ camera }, dt) => {
    if (!animate) return
    const k = Math.min(1, dt * 1.5)
    camera.position.x += (pointer.current.x * 0.55 - camera.position.x) * k
    camera.position.y += (-pointer.current.y * 0.35 - camera.position.y) * k
    camera.lookAt(0, 0, 0)
  })
  return null
}

/**
 * Drives rendering manually at ~24fps (slow ambient motion doesn't need 60) and pauses when the tab is hidden.
 * This keeps GPU/CPU use low on ordinary laptops.
 */
function Throttle({ fps }) {
  const invalidate = useThree((s) => s.invalidate)
  useEffect(() => {
    let last = 0
    let raf
    const loop = (now) => {
      raf = requestAnimationFrame(loop)
      if (document.hidden || now - last < 1000 / fps) return
      last = now
      invalidate()
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [fps, invalidate])
  return null
}

export default function Scene3D({ animate }) {
  const small = typeof window !== 'undefined' && window.innerWidth < 768
  return (
    <Canvas
      frameloop="demand"
      dpr={1}
      camera={{ position: [0, 0, CAM_Z], fov: FOV }}
      gl={{ antialias: false, alpha: true, powerPreference: 'low-power' }}
      style={{ pointerEvents: 'none', position: 'absolute', inset: 0 }}
      aria-hidden="true"
    >
      <Nebula animate={animate} />
      {/* distant, dense, faint stars */}
      <Stars count={small ? 520 : 1200} size={0.17} opacity={1} speed={0.8} seed={7} twinkle={0.9} animate={animate} />
      {/* fewer, brighter, bigger stars: these carry the parallax */}
      <Stars count={small ? 36 : 90} size={0.3} opacity={1} speed={1.0} seed={19} twinkle={0.6} animate={animate} />
      <ShootingStar animate={animate} />
      <Rig animate={animate} />
      {animate && <Throttle fps={24} />}
    </Canvas>
  )
}
