import { Component, lazy, Suspense, useEffect, useState } from 'react'
import { useSettings } from '../hooks/useSettings'
import { hasWebGL, usePrefersReducedMotion } from '../hooks/useMisc'

// three.js is loaded lazily so the UI is interactive before the 3D chunk arrives.
const Scene3D = lazy(() => import('./Scene3D'))


// Faint paper grain (static, tiny tile, no GPU work): gives the dark surface a printed-page feel instead of a flat digital one.
const GRAIN_SVG =
  "<svg xmlns='http://www.w3.org/2000/svg' width='180' height='180'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/>" +
  "<feColorMatrix values='0 0 0 0 0.93  0 0 0 0 0.9  0 0 0 0 0.84  0 0 0 0.6 0'/></filter><rect width='100%' height='100%' filter='url(#n)'/></svg>"
const GRAIN = `url("data:image/svg+xml,${encodeURIComponent(GRAIN_SVG)}")`

class SceneBoundary extends Component {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch(err) { console.warn('3D background disabled:', err?.message) }
  render() { return this.state.failed ? null : this.props.children }
}

/**
 * Fixed, non-interactive backdrop. Layers (bottom → top):
 *  1. CSS gradient (always present: it is also the fallback when WebGL is unavailable or disabled)
 *  2. optional 3D scene
 *  3. a dark vignette that guarantees text stays readable over the animation
 */
export default function Background() {
  const { settings } = useSettings()
  const reduced = usePrefersReducedMotion()
  const [webgl, setWebgl] = useState(null)
  useEffect(() => { setWebgl(hasWebGL()) }, [])

  const enabled = settings.background !== 'off' && webgl === true
  // 'auto' respects the OS reduced-motion setting by rendering a still frame; 'on' always animates.
  const animate = settings.background === 'on' ? true : !reduced

  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 z-0 overflow-hidden" data-testid="background">
      <div
        className="absolute inset-0"
        style={{
          background:
            'radial-gradient(64rem 42rem at 8% -12%, rgba(168,112,255,.30), transparent 60%),' +
            'radial-gradient(52rem 38rem at 100% -5%, rgba(255,120,200,.16), transparent 60%),' +
            'radial-gradient(70rem 44rem at 65% 115%, rgba(60,84,235,.24), transparent 60%),' +
            'linear-gradient(180deg, #0d0821 0%, #08051a 100%)',
        }}
      />
      <div className="absolute inset-0 opacity-[0.05]" style={{ backgroundImage: GRAIN }} />
      {enabled && (
        <SceneBoundary>
          <Suspense fallback={null}>
            <div className="absolute inset-0" data-scene={animate ? 'animated' : 'static'}>
              <Scene3D animate={animate} />
            </div>
          </Suspense>
        </SceneBoundary>
      )}
      <div className="absolute inset-0 bg-gradient-to-b from-page/20 via-transparent to-page/40" />
    </div>
  )
}
